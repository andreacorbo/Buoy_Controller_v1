import time
import select
import tools.utils as utils
import tools.shutil as shutil
from configs import dfl, cfg
from device import DEVICE
from tools.ymodem import YMODEM

class MODEM(DEVICE, YMODEM):

    def __init__(self, instance):
        YMODEM.__init__(self, self.getc, self.putc, mode="Ymodem1k")
        DEVICE.__init__(self, instance)

    def start_up(self):
        """Performs the instrument specific initialization sequence."""
        self.on()
        if self.is_ready():
            self.init_terminal()

    def is_ready(self):
        t0 = time.time()
        while not self._timeout(t0, self.config["Modem"]["Init_Timeout"]):
            utils.verbose("AT\r",cfg.VERBOSE)
            self.uart.write("AT\r")
            if self.uart.any():
                try:
                    rxd = self.uart.read().decode("utf-8")
                except UnicodeError:
                    continue
                utils.verbose(rxd)
                if "OK" in rxd:
                    return True
                else:
                    time.sleep(1)
        utils.log("{} => did not respond in {} secs.".format(self.name,self.config["Modem"]["Init_Timeout"]), "e")  # DEBUG
        return False

    def init_terminal(self):
        self.uart.read()  # Flushes input buffer.
        for _ in range(self.config["Modem"]["Call_Attempt"]):
            retry = False
            for at in self.config["Modem"]["Init_Ats"]:
                utils.verbose(at)
                self.uart.write(at)
                t0 = time.time()
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
                        utils.verbose(rxd)
                        if "ERROR" in rxd:
                            retry = True
                        break
                time.sleep(self.config["Modem"]["Ats_Delay"])
                if retry:
                    break

    def getc(self, size, timeout=1):
        """Reads out n-bytes from serial."""
        r, w, e = select.select([self.uart], [], [], timeout)
        if r:
            return self.uart.read(size)

    def putc(self, data, timeout=1):
        """Writes out n-bytes to serial."""
        r, w, e = select.select([], [self.uart], [], timeout)
        if w:
            return self.uart.write(data)

    def call(self):
        """Starts a call."""
        self.uart.read()  # Flushes input buffer.
        utils.log("{} => dialing...".format(self.name))  # DEBUG
        for at in self.config["Modem"]["Pre_Ats"]:
            utils.verbose(at)
            self.uart.write(at)
            t0 = time.time()
            while True:
                if self._timeout(t0, self.config["Modem"]["Call_Timeout"]):
                    utils.log("{} => timeout occourred".format(self.name), "e")  # DEBUG
                    return False
                if self.uart.any():
                    try:
                        rxd = self.uart.read().decode("utf-8")
                    except UnicodeError:
                        continue
                    utils.verbose(rxd)
                    if "OK" in rxd:
                        break
                    if "CONNECT" in rxd:
                        self.uart.read(1)  # Clears last byte \n
                        return True
                    return False
            time.sleep(self.config["Modem"]["Ats_Delay"])

    def hangup(self):
        """Ends a call."""
        self.uart.read()  # Flushes input buffer.  # Flushes uart buffer
        for at in self.config["Modem"]["Post_Ats"]:
            utils.verbose(at)
            self.uart.write(at)
            t0 = time.time()
            while True:
                if self._timeout(t0, self.config["Modem"]["Call_Timeout"]):
                    utils.log("{} => timeout occourred".format(self.name), "e")  # DEBUG
                    return False
                if self.uart.any():
                    try:
                        rxd = self.uart.read().decode("utf-8")
                    except UnicodeError:
                        continue
                    utils.verbose(rxd)
                    if "OK" in rxd:
                        break
                    return False
            time.sleep(self.config["Modem"]["Ats_Delay"])
        return True

    def data_transfer(self):
        """Sends files over the gsm network."""
        self.status(3)
        connected = False
        if utils.files_to_send():
            self.led.on()
            ########################################################################
            if config.DEBUG:
                connected = True
                self.uart.write(b"CONNECT\r")
            ########################################################################
            if not connected:
                for _ in range(self.config["Modem"]["Call_Attempt"]):
                    if self.call():
                        connected = True
                        break
            if connected:
                self.send(utils.files_to_send(), config.TMP_FILE_PFX, config.SENT_FILE_PFX, config.BKP_FILE_PFX)
                self.recv(10)
                self.hangup()
            else:
                utils.log("{} => connection unavailable, aborting...".format(self.name), "e")
            self.led.off()
        self.off()

    def sms(self, text):
        """Sends sms."""
        utils.log("{} => sending alert sms...".format(self.name))  # DEBUG
        self.led.on()
        self.uart.read()  # Flushes input buffer.
        for at in self.config["Modem"]["Sms_Pre_Ats"]:
            utils.verbose(at)
            self.uart.write(at)
            t0 = time.time()
            while True:
                if self._timeout(t0, self.config["Modem"]["Call_Timeout"]):
                    utils.log("{} => timeout occourred".format(self.name), "e")  # DEBUG
                    return False
                if self.uart.any():
                    try:
                        rxd = self.uart.read().decode("utf-8")
                    except UnicodeError:
                        continue
                    utils.verbose(rxd)
                    if "OK" in rxd:
                        break
                    if ">" in rxd:
                        break
                    return False
            time.sleep(self.config["Modem"]["Ats_Delay"])
        self.uart.write(text)
        self.uart.write(b"\x1A")
        self.led.off()
