from device import DEVICE
from tools.ymodem import YMODEM
import utime
import uselect
import tools.utils as utils
import tools.shutil as shutil
import constants

class MODEM(DEVICE, YMODEM):

    def __init__(self, instance, tasks=[]):
        self.sending = False
        self.connected = False
        self.sent = False
        self.received = False
        self.file_paths = []
        YMODEM.__init__(self, self._getc, self._putc, mode="Ymodem1k")
        DEVICE.__init__(self, instance, tasks)

    def start_up(self):
        """Performs the device specific initialization sequence."""
        self.on()
        self.init_terminal()

    def init_terminal(self):
        utils.log("{} => initializing".format(self.name))  # DEBUG
        self.uart.read()  # Flushes input buffer.
        t0 = utime.time()
        while True:
            if self._timeout(t0, self.config["Modem"]["Init_Timeout"]):
                utils.log("{} => did not respond in {} secs.".format(self.name,self.config["Modem"]["Init_Timeout"]), "e")  # DEBUG
                utils.log("{} => initialization failed".format(self.name), "e")  # DEBUG
                return
            utils.verbose("AT\r",constants.VERBOSE)
            self.uart.write("AT\r")
            if self.uart.any():
                try:
                    rxd = self.uart.read().decode("utf-8")
                except UnicodeError:
                    continue
                utils.verbose(rxd, constants.VERBOSE)
                if "OK" in rxd:
                    break
                else:
                    utime.sleep(1)
        for _ in range(self.config["Modem"]["Call_Attempt"]):
            retry = False
            for at in self.config["Modem"]["Init_Ats"]:
                utils.verbose(at,constants.VERBOSE)
                self.uart.write(at)
                t0 = utime.time()
                while True:
                    if self._timeout(t0 ,self.config["Modem"]["Init_Timeout"]):
                        utils.log("{} => timeout occourred".format(self.name), "e")  # DEBUG
                        retry = True
                        break
                    if self.uart.any():
                        try:
                            rxd = self.uart.read().decode("utf-8")
                        except UnicodeError:
                            continue
                        utils.verbose(rxd, constants.VERBOSE)
                        if "ERROR" in rxd:
                            retry = True
                        break
                utime.sleep(self.config["Modem"]["Ats_Delay"])
                if retry:
                    break
            if not retry:
                utils.log("{} => initialization succeeded".format(self.name))  # DEBUG

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

    def _send(self, unsent_files):
        """Sends files."""
        utils.log("{} => sending...".format(self.name))  # DEBUG
        self.send(unsent_files, constants.TMP_FILE_PFX, constants.SENT_FILE_PFX)
        return

    def _recv(self, timeout=10):
        """Receives files.

        Params:
            attempts(int): number of attempts
        Returns:
            True or False
        """
        utils.log("{} => receiving...".format(self.name))  # DEBUG
        if timeout > 0:
            self.recv(timeout)
        return

    def call(self):
        """Starts a call.

        Returns:
            True or False
        """
        self.uart.read()  # Flushes input buffer.
        utils.log("{} => dialing...".format(self.name))  # DEBUG
        for at in self.config["Modem"]["Pre_Ats"]:
            utils.verbose(at,constants.VERBOSE)
            self.uart.write(at)
            t0 = utime.time()
            while True:
                if self._timeout(t0, self.config["Modem"]["Call_Timeout"]):
                    utils.log("{} => timeout occourred".format(self.name), "e")  # DEBUG
                    return False
                if self.uart.any():
                    try:
                        rxd = self.uart.read().decode("utf-8")
                    except UnicodeError:
                        continue
                    utils.verbose(rxd,constants.VERBOSE)
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
                        return True
            utime.sleep(self.config["Modem"]["Ats_Delay"])


    def hangup(self):
        """Ends a call.

        Returns:
            True or False
        """
        self.uart.read()  # Flushes input buffer.  # Flushes uart buffer
        for at in self.config["Modem"]["Post_Ats"]:
            utils.verbose(at,constants.VERBOSE)
            self.uart.write(at)
            t0 = utime.time()
            while True:
                if self._timeout(t0, self.config["Modem"]["Call_Timeout"]):
                    utils.log("{} => timeout occourred".format(self.name), "e")  # DEBUG
                    return False
                if self.uart.any():
                    try:
                        rxd = self.uart.read().decode("utf-8")
                    except UnicodeError:
                        continue
                    utils.verbose(rxd,constants.VERBOSE)
                    if "ERROR" in rxd:
                        return False
                    if "OK" in rxd:
                        break
            utime.sleep(self.config["Modem"]["Ats_Delay"])
        return True

    def data_transfer(self):
        """Sends files over the gsm network."""
        unsent_files = utils.files_to_send()
        if not unsent_files:
            return
        self.led.on()
        self.connected = False
        for _ in range(self.config["Modem"]["Call_Attempt"]):
            if self.call():
                self.connected = True
                break
        if self.connected:
            self._send(unsent_files)
            self._recv()
            if not self.hangup():
                self.off()
        else:
            utils.log("{} => connection unavailable, aborting...".format(self.name), "e", True)
        self.led.off()

    def sms(self, text):
        """Starts a call.

        Returns:
            True or False
        """
        utils.log("{} => sending alert sms...".format(self.name))  # DEBUG
        self.led.on()
        self.uart.read()  # Flushes input buffer.
        for at in self.config["Modem"]["Sms_Pre_Ats"]:
            utils.verbose(at,constants.VERBOSE)
            self.uart.write(at)
            t0 = utime.time()
            while True:
                if self._timeout(t0, self.config["Modem"]["Call_Timeout"]):
                    utils.log("{} => timeout occourred".format(self.name), "e")  # DEBUG
                    return False
                if self.uart.any():
                    try:
                        rxd = self.uart.read().decode("utf-8")
                    except UnicodeError:
                        continue
                    utils.verbose(rxd, constants.VERBOSE)
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
        self.uart.write(text)
        self.uart.write(b"\x1A")
        self.led.off()
        return

    def main(self):
        """Do nothing, just for service pourpose."""
        return
