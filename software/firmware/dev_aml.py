import time
import tools.utils as utils
import config
from device import DEVICE

class METRECX(DEVICE):
    """Creates an aml metrecx multiparametric probe object."""

    def __init__(self, instance, tasks=[]):
        DEVICE.__init__(self, instance)
        self.data = []
        self.prompt = ">"
        ########################################################################
        self.tasks = tasks
        if self.tasks:
            if not any( elem in ["start_up","on","off"] for elem in self.tasks):
                self.status(2)
                self.main()
            for task in self.tasks:
                method = task
                param_dict={"self":self}
                param_list=[]
                params=""
                if type(task) == tuple:
                    method = task[0]
                    i = 0
                    for param in task[1:]:
                        param_dict["param"+str(i)] = task[1:][i]
                        param_list.append("param"+str(i))
                        params = ",".join(param_list)
                exec("self."+ method +"(" + params + ")", param_dict)
        ########################################################################

    def start_up(self):
        """Performs the instrument specific initialization sequence."""
        self.on()
        if self.break_():
            self.stop_logging()
            self.set_clock()
            self.set_sample_rate()
            self.start_logging()
        self.off()

    def get_reply(self, timeout=None):
        """Gets the instrument replies."""
        t0 = time.time()
        while not self._timeout(t0, timeout):
            if self.uart.any():
                return self.uart.read().split(b"\r\n")[1].decode("utf-8")

    def break_(self):
        """Sends the escape sequence to the instrument ``CTRL+C``."""
        t0 = time.time()
        while not self._timeout(t0, self.config["Ctd"]["Break_Timeout"]):
            self.uart.read()  # Flushes input buffer.
            self.uart.write(self.config["Ctd"]["Break_Sequence"])
            if self.get_prompt(self.config["Ctd"]["Prompt_Timeout"]):
                return True
        utils.log("{} => did not respond in {} secs.".format(self.name, self.config["Ctd"]["Prompt_Timeout"]), "e")  # DEBUG
        return False

    def get_prompt(self, timeout=None):
        """Gets the instrument prompt."""
        self.uart.read()  # Flushes input buffer.
        self.uart.write(b"\r")
        rx = self.get_reply(timeout)
        if rx == self.prompt:
            return True
        return False

    def set_date(self):
        """Sets up the instrument date, mm/dd/yy."""
        if self.get_prompt():
            now = time.localtime()
            self.uart.write("SET DATE {:02d}/{:02d}/{:02d}\r".format(now[1], now[2], int(str(now[0])[:-2])))
            if self.get_reply() == self.prompt:
                return True
        return False

    def set_time(self):
        """Sets up the instrument time, hh:mm:ss."""
        if self.get_prompt():
            now = time.localtime()
            self.uart.write("SET TIME {:02d}:{:02d}:{:02d}\r".format(now[3], now[4], now[5]))
            if self.get_reply() ==  self.prompt:
                return True
        return False

    def get_date(self):
        """Gets the instrument real time clock date."""
        if self.get_prompt():
            self.uart.write("DISPLAY DATE\r")
            return self._get_reply()[-13:]
        utils.log("{} => unable to retreive instrument date".format(self.name), "e")  # DEBUG

    def get_time(self):
        """Gets the instrument real time clock time."""
        if self.get_prompt():
            self.uart.write("DISPLAY TIME\r")
            return self._get_reply()[-14:-3]
        utils.log("{} => unable to retreive instrument time".format(self.name), "e")  # DEBUG

    def set_clock(self):
        """Synchronizes the intrument real time clock."""
        if self.set_date() and self.set_time():
            utils.log("{} => instrument clock synchronized ({} {})".format(self.name, self._get_date(), self._get_time()))  # DEBUG
            return True
        utils.log("{} => unable to synchronize the instrument clock".format(self.name), "e")  # DEBUG
        return False

    def set_sample_rate(self):
        """Sets the instrument sample rate."""
        if self.get_prompt():
            self.uart.write("SET S {:0d} S\r".format(self.sample_rate))
            if self.get_reply() ==  self.prompt:
                self.get_sample_rate()
                return True
        utils.log("{} => unable to set the sample rate".format(self.name), "e")  # DEBUG
        return False

    def get_sample_rate(self):
        """Gets the instrument sample rate."""
        if self.get_prompt():
            self.uart.write("DIS S\r")
            utils.log("{} => {}".format(self.name, self.get_reply()))  # DEBUG

    def stop_logging(self):
        """Stops instrument logging."""
        if self.get_prompt():
            self.uart.write("SET SCAN NOLOGGING\r")
            if self.get_prompt():
                return True
        utils.log("{} => unable to stop logging".format(self.name), "e")  # DEBUG
        return False

    def start_logging(self):
        """Starts instrument logging."""
        if self.get_prompt():
            self.uart.write("SET SCAN LOGGING\r")
            if self.get_prompt():
                return True
        utils.log("{} => unable to start logging".format(self.name), "e")  # DEBUG
        return False

    def format_data(self, sample):
        """Formats data according to output format."""
        epoch = time.time()
        data = [
            self.config["String_Label"],
            str(utils.unix_epoch(epoch)),
            utils.datestamp(epoch),  # YYMMDD
            utils.timestamp(epoch)  # hhmmssno
            ]
        return data + sample


    def log(self):
        """Writes out acquired data to file."""
        if self.data:
            utils.log_data(config.DATA_SEPARATOR.join(self.format_data(self.data)))

    def main(self):
        """Captures instrument data."""
        utils.log("{} => acquiring data...".format(self.name))  # DEBUG
        self.led.on()
        new_line = False
        r_buff = bytearray(1)
        t0 = time.time()
        while True:
            if self._timeout(t0, self.timeout):
                utils.log("{} => timeout occourred".format(self.name), "e")  # DEBUG
                if not self.data:
                    utils.log("{} => no data received".format(self.name), "e")  # DEBUG
                break
            if self.uart.any():
                self.uart.readinto(r_buff)
                for byte in r_buff:
                    try:
                        ascii = chr(byte)
                        if ascii == "\n":
                            new_line = True
                        elif ascii == "\r" and new_line:
                            self.data = "".join(self.data).split(config.DATA_SEPARATOR)
                            return
                        elif new_line:
                            self.data.append(ascii)
                        #print(ascii, end="")
                    except UnicodeError:
                        continue
        self.led.off()

class UVXCHANGE(DEVICE):
    """Creates an aml uvxchange untifouling object."""

    def __init__(self, instance, tasks=[]):
        DEVICE.__init__(self, instance)
        ########################################################################
        self.tasks = tasks
        if self.tasks:
            for task in self.tasks:
                method = task
                param_dict={"self":self}
                param_list=[]
                params=""
                if type(task) == tuple:
                    method = task[0]
                    i = 0
                    for param in task[1:]:
                        param_dict["param"+str(i)] = task[1:][i]
                        param_list.append("param"+str(i))
                        params = ",".join(param_list)
                exec("self."+ method +"(" + params + ")", param_dict)
        ########################################################################

    def start_up(self):
        """Performs the instrument specific initialization sequence."""
        self.off()
