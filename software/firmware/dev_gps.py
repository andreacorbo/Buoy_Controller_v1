import pyb
import utime
import tools.utils as utils
import constants
from device import DEVICE
from tools.nmea import NMEA
from math import sin, cos, sqrt, atan2, radians

class GPS(NMEA, DEVICE):

    def __init__(self, instance, tasks=[]):
        """Constructor method."""
        NMEA.__init__(self, instance)
        DEVICE.__init__(self, instance, tasks)

    def start_up(self):
        """Performs the device specific initialization sequence."""
        self.on()
        self.off()

    def is_fixed(self):
        """Checks for a valid position."""
        if not self.sentence or not self.sentence[2] == "A":
            utils.log("{} => no fix".format(self.name))
            return False
        return True

    def last_fix(self):
        """Stores last gps fix in :attr:`tools.utils.gps_fix`."""
        if self.is_fixed():
            if utils.gps_fix:
                self.displacement()
            utils.log("{} => saving the last gps fix...".format(self.name))
            utils.gps_fix = self.sentence
            utc_time = self.sentence[1]
            utc_date = self.sentence[9]
            lat = "{}{}".format(self.sentence[3], self.sentence[4])
            lon = "{}{}".format(self.sentence[5], self.sentence[6])
            utc = "{}-{}-{} {}:{}:{}".format("20"+utc_date[4:6], utc_date[2:4], utc_date[0:2], utc_time[0:2], utc_time[2:4], utc_time[4:6])
            speed = "{}".format(self.sentence[7])
            heading = "{}".format(self.sentence[8])
            utils.log("{} => last fix (UTC: {} POSITION: {} {}, SPEED: {}, HEADING: {})".format(self.name, utc, lat, lon, speed, heading))  # DEBUG
        return

    def displacement(self):
        """Calculates the displacement from the previous position and store it in :attr:`tools.utils.gps_displacement`."""
        R = 6373.0 / 1.852  # Approximate radius of earth in nm.
        prev_lat = radians(int(utils.gps_fix[3][0:2]) + float(utils.gps_fix[3][2:]) / 60)
        prev_lon = radians(int(utils.gps_fix[5][0:2]) + float(utils.gps_fix[5][2:]) / 60)
        last_lat = radians(int(self.sentence[3][0:2]) + float(self.sentence[3][2:]) / 60)
        last_lon = radians(int(self.sentence[5][0:2]) + float(self.sentence[5][2:]) / 60)
        a = sin((last_lat - prev_lat) / 2)**2 + cos(prev_lat) * cos(last_lat) * sin((last_lon - prev_lon) / 2)**2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))
        utils.gps_displacement = R * c
        return

    def sync_rtc(self):
        """Synchronizes the board RTC with the gps utc timestamp."""
        if self.is_fixed():
            utils.log("{} => synchronizing the controller real time clock...".format(self.name))
            utc_time = self.sentence[1]
            utc_date = self.sentence[9]
            rtc = pyb.RTC()
            try:
                rtc.datetime((int("20"+utc_date[4:6]), int(utc_date[2:4]), int(utc_date[0:2]), 0, int(utc_time[0:2]), int(utc_time[2:4]), int(utc_time[4:6]), float(utc_time[6:])))  # rtc.datetime(yyyy, mm, dd, 0, hh, ii, ss, sss)
                utils.log("{} => controller clock successfully synchronized (UTC: {})".format(self.name, utils.timestring(utime.time())))
            except Exception as err:
                utils.log("{} => sync_rtc ({}): {}".format(self.name, type(err).__name__, err), "e")  # DEBUG
        return

    def log(self):
        """Writes out acquired data to file."""
        if self.sentence:
            utils.log_data(constants.DATA_SEPARATOR.join(map(str, self.sentence)))
        return

    def main(self, sentence="RMC"):
        """Retreives data from a serial gps device."""
        utils.log("{} => acquiring data...".format(self.name))
        self.led.on()
        t0 = utime.time()
        while True:
            if self._timeout(t0, self.timeout):
                utils.log("{} => timeout occourred".format(self.name), "e")  # DEBUG
                if not self.sentence:
                    utils.log("{} => no data received".format(self.name), "e")  # DEBUG
                else:
                    utils.log("{} => no {} string received".format(self.name, sentence), "e")  # DEBUG
                break
            if self.uart.any():
                if not self.get_sentence(self.uart.read(1), sentence):
                    continue
                break
        self.led.off()
        return
