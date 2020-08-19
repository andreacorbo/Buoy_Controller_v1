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

"""This module contains specific Aml ctd devices tools."""

import utime
from device import DEVICE
import tools.utils as utils
import constants

class METRECX(DEVICE):
    """Creates an aml metrecx multiparametric probe object."""

    def __init__(self, instance, tasks=[], data_tasks = ["log"]):
        self.prompt = ">"
        DEVICE.__init__(self, instance, tasks, data_tasks)

    def start_up(self):
        """Performs device specific initialization sequence."""
        self.on()
        if self._break():
            self._stop_logging()
            self._set_clock()
            self._set_sample_rate()
            self._start_logging()
        self.off()
        return

    def _get_reply(self, timeout=None):
        """Returns replies from instrument.

        Returns:
            bytes or None
        """
        start = utime.time()
        while not self._timeout(start, timeout):
            if self.uart.any():
                return self.uart.read().split(b"\r\n")[1].decode("utf-8")
        return

    def _break(self):
        """Sends the escape sequence to the instrument ``CTRL+C``.

        Returns:
            True or False
        """

        start = utime.time()
        while not self._timeout(start, self.config["Ctd"]["Break_Timeout"]):
            self.flush_uart()
            self.uart.write(self.config["Ctd"]["Break_Sequence"])
            if self._get_prompt(self.config["Ctd"]["Prompt_Timeout"]):
                return True
        utils.log("{} => did not answer in {} sec".format(self.name, self.config["Ctd"]["Prompt_Timeout"]), "e")  # DEBUG
        return False

    def _get_prompt(self, timeout=None):
        """Gets the instrument prompt."""
        self.flush_uart()
        self.uart.write(b"\r")
        rx = self._get_reply(timeout)
        if rx == self.prompt:
            return True
        else:
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
            utils.log("{} => instrument clock successfully synchronized (instrument: {} {} controller: {})".format(self.name, self._get_date(), self._get_time(), utils.time_string(utime.mktime(utime.localtime()))))  # DEBUG
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
        try:
            data = [
                self.config["String_Label"],
                str(utils.unix_epoch(epoch)),
                utils.datestamp(epoch),  # YYMMDD
                utils.timestamp(epoch)  # hhmmss
                ]
        except Exception as err:
            utils.log("{} => {} while formatting data".format(self.name, err), "e")  # DEBUG
            return
        return data + sample

    def main(self):
        """Captures instrument data."""
        utils.log("{} => acquiring data...".format(self.name))  # DEBUG
        self.led_on()
        self.data = []
        new_line = False
        while True:
            if not self.status() == 'ready':  # Exits if the device has been switched off by scheduler.
                utils.log("{} => timeout occourred".format(self.name), "e")  # DEBUG
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
        self.led_off()
        return

    def log(self):
        """Writes out acquired data to file."""
        utils.log_data(constants.DATA_SEPARATOR.join(self._format_data(self.data)))
        return


class UVXCHANGE(DEVICE):
    """Creates an aml uvxchange untifouling object."""

    def __init__(self, instance, tasks=[]):
        DEVICE.__init__(self, instance)
        if tasks:
            for task in tasks:
                eval("self." + task + "()", {"self":self})

    def start_up(self):
        """Performs device specific initialization sequence."""
        self.on()
