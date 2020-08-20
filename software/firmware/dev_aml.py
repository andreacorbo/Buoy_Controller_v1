import utime
from device import DEVICE
import tools.utils as utils
import config

class METRECX(DEVICE):
    """Creates an aml metrecx multiparametric probe object."""

    def __init__(self, instance, tasks=[]):
        DEVICE.__init__(self, instance)
        self.prompt = ">"
        ########################################################################
        self.tasks = tasks
        if self.tasks:
            if not any( elem in ["start_up","on","off"] for elem in self.tasks):
                self.status(2) # Sets device ready.
                try:
                    self.main()
                except AttributeError:
                    pass
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
        """Performs device specific initialization sequence."""
        self.on()
        if self._break():
            self._stop_logging()
            self._set_clock()
            self._set_sample_rate()
            self._start_logging()

    def _get_reply(self, timeout=None):
        """Returns replies from instrument.

        Returns:
            bytes or None
        """
        start = utime.time()
        while not self._timeout(start, timeout):
            if self.uart.any():
                return self.uart.read().split(b"\r\n")[1].decode("utf-8")

    def _break(self):
        """Sends the escape sequence to the instrument ``CTRL+C``.

        Returns:
            True or False
        """

        start = utime.time()
        while not self._timeout(start, self.config["Ctd"]["Break_Timeout"]):
            self.uart.read()  # Flushes input buffer.
            self.uart.write(self.config["Ctd"]["Break_Sequence"])
            if self._get_prompt(self.config["Ctd"]["Prompt_Timeout"]):
                return True
        utils.log("{} => did not answer in {} secs".format(self.name, self.config["Ctd"]["Prompt_Timeout"]), "e")  # DEBUG
        return False

    def _get_prompt(self, timeout=None):
        """Gets the instrument prompt."""
        self.uart.read()  # Flushes input buffer.
        self.uart.write(b"\r")
        rx = self._get_reply(timeout)
        if rx == self.prompt:
            return True
        return False

    def _set_date(self):
        """Sets up the instrument date, mm/dd/yy."""
        if self._get_prompt():
            now = utime.localtime()
            self.uart.write("SET DATE {:02d}/{:02d}/{:02d}\r".format(now[1], now[2], int(str(now[0])[:-2])))
            if self._get_reply() == self.prompt:
                return True
        return False

    def _set_time(self):
        """Sets up the instrument time, hh:mm:ss."""
        if self._get_prompt():
            now = utime.localtime()
            self.uart.write("SET TIME {:02d}:{:02d}:{:02d}\r".format(now[3], now[4], now[5]))
            if self._get_reply() ==  self.prompt:
                return True
        return False

    def _get_date(self):
        """Gets the instrument real time clock date."""
        if self._get_prompt():
            self.uart.write("DISPLAY DATE\r")
            return self._get_reply()[-13:]
        utils.log("{} => unable to retreive instrument date".format(self.name), "e")  # DEBUG

    def _get_time(self):
        """Gets the instrument real time clock time."""
        if self._get_prompt():
            self.uart.write("DISPLAY TIME\r")
            return self._get_reply()[-14:-3]
        utils.log("{} => unable to retreive instrument time".format(self.name), "e")  # DEBUG

    def _set_clock(self):
        """Synchronizes the intrument real time clock."""
        if self._set_date() and self._set_time():
            utils.log("{} => instrument clock successfully synchronized (instrument: {} {} controller: {})".format(self.name, self._get_date(), self._get_time(), utils.timestring(utime.mktime(utime.localtime()))))  # DEBUG
            return True
        utils.log("{} => unable to synchronize the real time clock".format(self.name), "e")  # DEBUG
        return False

    def _set_sample_rate(self):
        """Sets intrument sample rate."""
        if self._get_prompt():
            self.uart.write("SET S {:0d} S\r".format(self.sample_rate))
            if self._get_reply() ==  self.prompt:
                self._get_sample_rate()
                return True
        utils.log("{} => unable to set sample rate".format(self.name), "e")  # DEBUG
        return False

    def _get_sample_rate(self):
        if self._get_prompt():
            self.uart.write("DIS S\r")
            utils.log("{} => {}".format(self.name, self._get_reply()))  # DEBUG

    def _stop_logging(self):
        """Stops logging."""
        if self._get_prompt():
            self.uart.write("SET SCAN NOLOGGING\r")
            if self._get_prompt():
                utils.log("{} => logging successfully stopped".format(self.name))  # DEBUG
                return True
        utils.log("{} => unable to stop logging".format(self.name), "e")  # DEBUG
        return False

    def _start_logging(self):
        """Starts logging."""
        if self._get_prompt():
            self.uart.write("SET SCAN LOGGING\r")
            if self._get_prompt():
                utils.log("{} => logging successfully started".format(self.name))  # DEBUG
                return True
        utils.log("{} => unable to start logging".format(self.name), "e")  # DEBUG
        return False

    def _format_data(self, sample):
        """Formats data according to output format."""
        epoch = utime.time()
        data = [
            self.config["String_Label"],
            str(utils.unix_epoch(epoch)),
            utils.datestamp(epoch),  # YYMMDD
            utils.timestamp(epoch)  # hhmmssno
            ]
        return data + sample


    def log(self):
        """Writes out acquired data to file."""
        utils.log_data(config.DATA_SEPARATOR.join(self._format_data(self.data)))

    def main(self):
        """Captures instrument data."""
        utils.log("{} => acquiring data...".format(self.name))  # DEBUG
        self.led.on()
        self.data = []
        new_line = False
        t0 = utime.time()
        while True:
            if self._timeout(t0, self.timeout):
                utils.log("{} => timeout occourred".format(self.name), "e")  # DEBUG
                if not self.data:
                    utils.log("{} => no data received".format(self.name), "e")  # DEBUG
                break
            if self.uart.any():
                byte = self.uart.read(1)
                if byte == b"\n":
                    new_line = True
                elif byte == b"\r" and new_line:
                    self.data = "".join(self.data).split()
                    break
                elif new_line:
                    self.data.append(byte.decode("utf-8"))
        self.led.off()

class UVXCHANGE(DEVICE):
    """Creates an aml uvxchange untifouling object."""

    def __init__(self, instance, tasks=[]):
        DEVICE.__init__(self, instance)
        ########################################################################
        self.tasks = tasks
        if self.tasks:
            if not any( elem in ["start_up","on","off"] for elem in self.tasks):
                self.status(2) # Sets device ready.
                try:
                    self.main()
                except AttributeError:
                    pass
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
        """Performs device specific initialization sequence."""
        self.on()
        self.off()

    def disable(self):
        utils.log("{} => disabling antifouling...".format(self.name))  # DEBUG
        self.off()
