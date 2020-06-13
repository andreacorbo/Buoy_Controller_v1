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
    """Creates a gps device object.

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
        """Performs the device specific initialization sequence."""
        self.init_power()

    def main(self, sentence="RMC"):
        """Retreives data from a serial gps device.

        Passes  data char by char to :func:`tools.nmea.NMEA.get_sentence` to get a valid
        :download:`NMEA <../../media/NV08C_RTK_NMEA_Protocol_Specification_V16_ENG_1.pdf>` string.

        Parameters:
            ``sentence`` :obj:`str` The desired NMEA sentence.

        Return:
            ``True`` or ``False`` depends on the desired sentence has been acquired.
        """
        utils.log_file("{} => acquiring data...".format(self.name), constants.LOG_LEVEL)
        while True:
            if not self.status() == "READY":  # Exits if the device has been switched off by scheduler.
                utils.log_file("{} => timeout occourred".format(self.name), constants.LOG_LEVEL, True)  # DEBUG
                if not self.sentence:
                    utils.log_file("{} => no data received".format(self.name), constants.LOG_LEVEL, True)  # DEBUG
                else:
                    utils.log_file("{} => no {} string received".format(self.name, sentence), constants.LOG_LEVEL, True)  # DEBUG
                return False
            if self.uart.any():
                if not self.get_sentence(self.uart.readchar(), sentence):
                    continue
                return True

    def fixed(self):
        """Checks for a valid position.

        Returns:
          True or False
        """
        if not self.sentence[2] == "A":
            utils.log_file("{} => no fix".format(self.name), constants.LOG_LEVEL)
            return False
        return True

    def log(self):
        """Writes out acquired data to file."""
        self.fixed()
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
        """Stores last gps fix in :attr:`tools.utils.gps_fix`."""
        if self.fixed():
            utils.log_file("{} => saving last gps fix...".format(self.name), constants.LOG_LEVEL)
            self.displacement()
            utils.gps_fix = self.sentence
            utc_time = self.sentence[1]
            utc_date = self.sentence[9]
            lat = "{}{}".format(self.sentence[3], self.sentence[4])
            lon = "{}{}".format(self.sentence[5], self.sentence[6])
            utc = "{}-{}-{} {}:{}:{}".format("20"+utc_date[4:6], utc_date[2:4], utc_date[0:2], utc_time[0:2], utc_time[2:4], utc_time[4:6])
            speed = "{}".format(self.sentence[7])
            heading = "{}".format(self.sentence[8])
            utils.log_file("{} => last fix (UTC: {} POSITION: {} {}, SPEED: {}, HEADING: {})".format(self.name, utc, lat, lon, speed, heading), constants.LOG_LEVEL)  # DEBUG
        return

    def displacement(self):
        """Calculates THE displacement from last fix and store it in :attr:`tools.utils.gps_displacement`."""
        if self.fixed() and utils.gps_fix:
            R = 6373.0  # Approximate radius of earth in km.
            prev_lat = radians(int(utils.gps_fix[3][0:2]) + float(utils.gps_fix[3][2:]) / 60)
            prev_lon = radians(int(utils.gps_fix[5][0:2]) + float(utils.gps_fix[5][2:]) / 60)
            last_lat = radians(int(self.sentence[3][0:2]) + float(self.sentence[3][2:]) / 60)
            last_lon = radians(int(self.sentence[5][0:2]) + float(self.sentence[5][2:]) / 60)
            a = sin((last_lat - prev_lat) / 2)**2 + cos(prev_lat) * cos(last_lat) * sin((last_lon - prev_lon) / 2)**2
            c = 2 * atan2(sqrt(a), sqrt(1 - a))
            utils.gps_displacement = R * c
        return
