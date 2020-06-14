# The MIT License (MIT)
#
# Copyright (c) 2018 OGS
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

from device import DEVICE
from tools.ymodem import YMODEM
import utime
import uselect
import tools.utils as utils
import constants

class MODEM(DEVICE, YMODEM):
    """Creates a gprs MODEM object."""

    def __init__(self, instance, tasks=[]):
        """Constructor method."""
        DEVICE.__init__(self, instance)
        YMODEM.__init__(self, self._getc, self._putc, mode="Ymodem1k")
        self.sending = False
        self.connected = False
        self.sent = False
        self.received = False
        self.timeout = 1
        self.file_paths = []
        if tasks:
            for task in tasks:
                eval("self." + task + "()", {"self":self})

    def start_up(self):
        """Performs the device specific initialization sequence."""
        self.init_power()
        #self.init_terminal()

    def init_terminal(self):
        utils.log_file("{} => initializing".format(self.name), constants.LOG_LEVEL, True)  # DEBUG
        for _ in range(self.config["Modem"]["Call_Attempt"]):
            retry = False
            for at in self.config["Modem"]["Init_Ats"]:
                self.uart.write(at)
                t0 = utime.time()
                while True:
                    utime.sleep(self.config["Modem"]["Ats_Delay"])
                    if utime.time() - t0 >= self.config["Modem"]["Call_Timeout"]:
                        retry = True
                        break
                    if self.uart.any():
                        rxd = self.uart.read()
                        print("\r\n{}".format(rxd.decode("utf-8")), end="")
                        if "ERROR" in rxd:
                            retry = True
                        break
                    else:
                        print(".", end="")
                if retry:
                    break
            if not retry:
                utils.log_file("{} => initialization succeeded".format(self.name), constants.LOG_LEVEL, True)  # DEBUG
                return
        utils.log_file("{} => initialization failed".format(self.name), constants.LOG_LEVEL, True)  # DEBUG

    def _getc(self, size, timeout=1):
        """Reads bytes from serial.

        Params:
            size(int): num of bytes
            timeout(int)
        Returns:
            given data or None
        """
        r, w, e = uselect.select([self.uart], [], [], timeout)
        if r:
            return self.uart.read(size)
        else:
            return

    def _putc(self, data, timeout=1):
        """Writes bytes to serial.

        Params:
            data(bytes)
            timeout(int)
        Returns:
            written data or None
        """
        r, w, e = uselect.select([], [self.uart], [], timeout)
        if w:
            return self.uart.write(data)
        else:
            return

    def _send(self):
        """Sends files."""
        self.send(utils.unsent_files, constants.TMP_FILE_PFX, constants.SENT_FILE_PFX):
        self.sent = True
        return

    def receive(self, attempts):
        """Receives files.

        Params:
            attempts(int): number of attempts
        Returns:
            True or False
        """
        self.uart.write(
        "\r\n"+
        "##################################################\r\n"+
        "#                                                #\r\n"+
        "#              YMODEM RECEIVER V1.1              #\r\n"+
        "#                                                #\r\n"+
        "##################################################\r\n"+
        "WAITING FOR FILES...")
        for counter in range(attempts):
            if self.recv():
                break
        self.uart.write("...RECEIVED\r\n\r\n")
        self.received = True
        return

    def call(self):
        """Starts a call.

        Returns:
            True or False
        """
        self.flush_uart()
        for at in self.config["Modem"]["Pre_Ats"]:
            self.uart.write(at)
            t0 = utime.time()
            while True:
                utime.sleep(self.config["Modem"]["Ats_Delay"])
                if utime.time() - t0 >= self.config["Modem"]["Call_Timeout"]:
                    return False
                if self.uart.any():
                    rxd = self.uart.read()
                    print("\r\n{}".format(rxd.decode("utf-8")))
                    if "ERROR" in rxd:
                        return False
                    if "NO CARRIER" in rxd:
                        return False
                    if "NO ANSWER" in rxd:
                        return False
                    if "OK" in rxd:
                        break
                    if "CONNECT" in rxd:
                        self.flush_uart(1)  # Clears last byte \n
                        self.connected = True
                        return True
                else:
                    print(".", end="")


    def hangup(self):
        """Ends a call.

        Returns:
            True or False
        """
        self.flush_uart()  # Flushes uart buffer
        for at in self.config["Modem"]["Post_Ats"]:
            self.uart.write(at)
            t0 = utime.time()
            while True:
                utime.sleep(self.config["Modem"]["Ats_Delay"])
                if utime.time() - t0 == self.config["Modem"]["Call_Timeout"]:
                    return False
                if self.uart.any():
                    rxd = self.uart.read()
                    print("\r\n{}".format(rxd.decode("utf-8")), end="")
                    if "ERROR" in rxd:
                        return False
                    if "OK" in rxd:
                        break
                else:
                    print(".", end="")
        return True

    def data_transfer(self):
        """Sends files over the gsm network."""
        self.sending = True
        utils.log_file("{} => sending data...".format(self.name), constants.LOG_LEVEL, True)  # DEBUG
        self.led_on()
        self.connected = False
        self.sending = False
        self.sent = False
        for _ in range(self.config["Modem"]["Call_Attempt"]):
            if not self.connected:
                if not self.call():
                    utime.sleep(self.config["Modem"]["Call_Delay"])
                    continue
            elif not self.sent:
                self._send()
            elif not self.hangup():
                continue
            else:
                self.led_off()
                return
        self.led_off()
        utils.log_file("{} => connection unavailable, aborting...".format(self.name), constants.LOG_LEVEL, True)
        return

    def sms(self):
        """Starts a call.

        Returns:
            True or False
        """
        self.flush_uart()
        for at in self.config["Modem"]["Sms_Pre_Ats"]:
            self.uart.write(at)
            t0 = utime.time()
            while True:
                """if utime.time() - t0 >= self.config["Modem"]["Call_Timeout"]:
                    return False"""
                if self.uart.any():
                    rxd = self.uart.read()
                    print("\r\n{}".format(rxd.decode("utf-8")), end="")
                    if "ERROR" in rxd:
                        return False
                    if "NO CARRIER" in rxd:
                        return False
                    if "NO ANSWER" in rxd:
                        return False
                    if "OK" in rxd:
                        break
                    if ">" in rxd:
                        break
            utime.sleep(self.config["Modem"]["Ats_Delay"])
        self.uart.write("hello!")
        self.uart.write(b"\x1A")
