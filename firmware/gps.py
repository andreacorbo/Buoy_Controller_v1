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

import pyb
import utime
from device import DEVICE
import tools.utils as utils
import constants
from tools.nmea import NMEA

class GPS(DEVICE, NMEA):

    def __init__(self):
        self.config_file = __name__ + constants.CONFIG_TYPE
        DEVICE.__init__(self)
        NMEA.__init__(self)
        self.start_up()

    def start_up(self):
        """Performs power on sequence."""
        if self.init_power():
          return True
        return False

    def main(self):
        """Read nmea messages and search for RMC valid strings.

        Returns:
            None
        """
        if not self._init_uart():
            return
        self._led_on()
        NMEA.__init__(self)
        start = utime.time()
        data = self.config['String_Label']
        while True:
            if self.status() == "off":
                utils.log_file("{} => timeout occourred".format(self.__qualname__), constants.LOG_LEVEL, True)  # DEBUG
                break
            if self.uart.any():
                char = self.uart.readchar()
                self.get_sentence(char)
                if not self.checksum_verified:
                    continue
                if not self.sentence[0] in self.config['Gps']['String_To_Acquire']:
                    continue
                if self.sentence[0] == "GPRMC":
                    data = self.serial_string
                    if self.sentence[2] == "V":
                        utils.log_file("{} => invalid data".format(self.__qualname__), constants.LOG_LEVEL, True)  # DEBUG
                        continue
                    self._synchronize_rtc(self.sentence)
                    self._set_last_fix(self.sentence)
                    break
        utils.log_data(data)
        self._deinit_uart()
        self._led_off()

    def _synchronize_rtc(self, gprmc_string):
        """Synchronizes rtc with gps data.

        Params:
            gprmc_string(str)
        """
        utc_time = gprmc_string[1]
        utc_date = gprmc_string[9]
        rtc = pyb.RTC()
        try:
            rtc.datetime((int('20'+utc_date[4:6]), int(utc_date[2:4]), int(utc_date[0:2]), 0, int(utc_time[0:2]), int(utc_time[2:4]), int(utc_time[4:6]), float(utc_time[6:])))  # rtc.datetime(yyyy, mm, dd, 0, hh, ii, ss, sss)
            utils.log_file("{} => rtc successfully synchronized (UTC: {})".format(self.__qualname__, utils.time_string(utime.time())), constants.LOG_LEVEL)
        except:
            utils.log_file("{} => unable to synchronize rtc".format(self.__qualname__, utils.time_string(utime.time())), constants.LOG_LEVEL)

    def _set_last_fix(self, gprmc_string):
        """Saves last gps fix.

        Params:
            gprmc_string(str)
        """
        utc_time = gprmc_string[1]
        utc_date = gprmc_string[9]
        lat = gprmc_string[3]
        lon = gprmc_string[5]
        try:
            self.config['Gps']['Last_Fix'] = "{}-{}-{} {}:{}:{}".format('20'+utc_date[4:6], utc_date[2:4], utc_date[0:2], utc_time[0:2], utc_time[2:4], utc_time[4:6])
            self.config['Gps']['Last_Position'] = "{}°{}\'{}, {}°{}\'{}".format(lat[0:2], lat[2:], gprmc_string[4], lon[0:3], lon[3:], gprmc_string[6])
            utils.log_file("{} => last fix successfully updated (UTC: {} POSITION: {})".format(self.__qualname__, self.config['Gps']['Last_Fix'], self.config['Gps']['Last_Position'], constants.LOG_LEVEL))  # DEBUG
        except:
            utils.log_file("{} => unable to update last fix".format(self.__qualname__), constants.LOG_LEVEL)  # DEBUG
