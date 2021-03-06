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
# FITNESS FOR A PARTICULAR PURPOSE AND NONINt1                                                                                                                                                                FRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

"""This module contains standard GPS devices tools."""

import pyb
import utime
import tools.utils as utils
import constants
from device import DEVICE
from tools.nmea import NMEA
from math import sin, cos, sqrt, atan2, radians

class GPS(NMEA, DEVICE):
    """Creates a GPS device object.

    Extends the :class:`device` and the :class:`tools.nmea` classes.

    Parameters:
        ``instance`` :obj:`str` The object instance number (if multiple devices
        are present) needs a correspondent section in the config_file.

        ``tasks`` :obj:`list` (optional) A list of methods to be executed at
        object creation.
    """

    def __init__(self, instance, tasks=[]):
        """Constructor method."""
        DEVICE.__init__(self, instance)
        NMEA.__init__(self, instance)
        data_tasks = ["log","last_fix","sync_rtc"]
        if tasks:
            if any(elem in data_tasks for elem in tasks):
                if self.main():
                    for task in tasks:
                        eval("self." + task + "()", {"self":self})
            else:
                for task in tasks:
                    eval("self." + task + "()", {"self":self})

    def start_up(self):
        """Performs the device specific initialization sequence.

        Return:
            ``True`` or ``False`` depends on startup sequence successfull
            completion.
        """
        if self.init_power():
          return True
        return False

    def main(self, sentence="RMC"):
        """Retreives data either from a UART or I2C gps device.

        Passes  data char by char to :func:`tools.nmea.NMEA.get_sentence` to get a valid
        :download:`NMEA <../../media/NV08C_RTK_NMEA_Protocol_Specification_V16_ENG_1.pdf>` string.

        Parameters:
            ``sentence`` :obj:`str` The desired NMEA sentence.

        Return:
            ``True`` or ``False`` depends on gps got a valid fix.
        """
        utils.log_file("{} => acquiring data...".format(self.name), constants.LOG_LEVEL)
        while True:
            if not self.status() == "READY":  # Exits if the device has been switched off by scheduler.
                utils.log_file("{} => timeout occourred".format(self.name), constants.LOG_LEVEL, True)  # DEBUG
                return False
            if self.config["I2C_Address"]:  # Retreives data from an I2C device.
                for char in self._i2c_read_reg():
                    if self.get_sentence(char, sentence):
                        continue
            else:  # Retreives data from a serial device.
                if self.uart.any():
                    if not self.get_sentence(self.uart.readchar(), sentence):
                        continue
                else:
                    continue
            if self.fixed():
                return True
            else:
                utils.log_file("{} => invalid data received".format(self.name), constants.LOG_LEVEL, True)  # DEBUG

    def _i2c_read_reg(self):
        """Reads the data form the i2c register."""
        pass

    def log(self):
        """Writes out acquired data to a file."""
        utils.log_data("$" + ",".join(map(str, self.sentence)))
        return

    def sync_rtc(self):
        """Synchronizes the board RTC with the gps utc timestamp."""
        if self.fixed():
            utils.log_file("{} => syncyng rtc...".format(self.name), constants.LOG_LEVEL)
            utc_time = self.sentence[1]
            utc_date = self.sentence[9]
            rtc = pyb.RTC()
            try:
                rtc.datetime((int("20"+utc_date[4:6]), int(utc_date[2:4]), int(utc_date[0:2]), 0, int(utc_time[0:2]), int(utc_time[2:4]), int(utc_time[4:6]), float(utc_time[6:])))  # rtc.datetime(yyyy, mm, dd, 0, hh, ii, ss, sss)
                utils.log_file("{} => rtc successfully synchronized (UTC: {})".format(self.name, utils.time_string(utime.time())), constants.LOG_LEVEL)
            except:
                utils.log_file("{} => unable to synchronize rtc".format(self.name, utils.time_string(utime.time())), constants.LOG_LEVEL)
        return

    def last_fix(self):
        """Stores last gps valid position and utc timestamp in
        :attr:`tools.utils.gps`.
        """
        if self.fixed():
            utils.log_file("{} => saving last gps fix...".format(self.name), constants.LOG_LEVEL)
            utc_time = self.sentence[1]
            utc_date = self.sentence[9]
            lat = "{}{}".format(self.sentence[3], self.sentence[4])
            lon = "{}{}".format(self.sentence[5], self.sentence[6])
            utc = "{}-{}-{} {}:{}:{}".format("20"+utc_date[4:6], utc_date[2:4], utc_date[0:2], utc_time[0:2], utc_time[2:4], utc_time[4:6])
            speed = "{}".format(self.sentence[7])
            heading = "{}".format(self.sentence[8])
            utils.gps = (utc, lat, lon, speed, heading)
            utils.log_file("{} => last fix (UTC: {} POSITION: {} {}, SPEED: {}, HEADING: {})".format(self.name, utc, lat, lon, speed, heading), constants.LOG_LEVEL)  # DEBUG
        return

    def displacement(self):
        # approximate radius of earth in km
        R = 6373.0
        lat1 = radians(utils.gps())
        lon1 = radians(21.0122287)
        lat2 = radians(52.406374)
        lon2 = radians(16.9251681)

        dlon = lon2 - lon1
        dlat = lat2 - lat1

        a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))

        distance = R * c

        print("Result:", distance)
        print("Should be:", 278.546, "km")
