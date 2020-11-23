import pyb
import time
from math import sin, cos, sqrt, atan2, radians
import tools.utils as utils
from configs import dfl, cfg
from device import DEVICE
from tools.nmea import NMEA

class GPS(NMEA, DEVICE):

    def __init__(self, instance):
        DEVICE.__init__(self, instance)
        self.rx_buff = bytearray(1)

    def start_up(self):
        """Performs the instrument specific initialization sequence."""
        self.off()

    def is_fixed(self):
        """Checks for a valid position."""
        if not self.sentence[2] == "A":
            utils.log("{} => no fix".format(self.name))
            return False
        return True

    def last_fix(self):
        """Stores last gps fix in :attr:`tools.utils.gps_fix`."""
        if self.is_fixed():
            if utils.gps_fix:
                self.displacement()
            utils.gps_fix = self.sentence
            utils.log("{} => fix acquired".format(self.name))  # DEBUG

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

    def sync_rtc(self):
        """Synchronizes the board RTC with the gps utc timestamp."""
        if self.is_fixed():
            utc_time = self.sentence[1]
            utc_date = self.sentence[9]
            rtc = pyb.RTC()
            try:
                rtc.datetime((int("20"+utc_date[4:6]), int(utc_date[2:4]), int(utc_date[0:2]), 0, int(utc_time[0:2]), int(utc_time[2:4]), int(utc_time[4:6]), float(utc_time[6:])))  # rtc.datetime(yyyy, mm, dd, 0, hh, ii, ss, sss)
                utils.log("{} => rtc synchronized".format(self.name))
            except Exception as err:
                utils.log("{} => sync_rtc ({}): {}".format(self.name, type(err).__name__, err), "e")  # DEBUG

    def log(self):
        """Writes out acquired data to file."""
        utils.log_data(dfl.DATA_SEPARATOR.join(self.sentence))

    def main(self, tasks=[], sentence="RMC"):
        """Retreives data from a serial gps device."""
        utils.log("{} => acquiring data...".format(self.name))  # DEBUG
        self.status(2)
        self.init_uart()
        pyb.LED(3).on()
        NMEA.__init__(self)
        t0 = time.time()
        while True:
            if self._timeout(t0, self.timeout):
                if self.sentence:
                    utils.log("{} => no {} string received".format(self.name, sentence), "e")  # DEBUG
                else:
                    utils.log("{} => no data received".format(self.name), "e")  # DEBUG
                break
            if self.uart.any():
                self.uart.readinto(self.rx_buff)
                try:
                    self.rx_buff.decode("utf-8")
                except UnicodeError:
                    continue
                if not self.get_sentence(self.rx_buff.decode("utf-8"), sentence):
                    continue
                break
        for t in tasks:
            exec("self."+t+"()",{"self":self})
        pyb.LED(3).off()
        self.uart.deinit()
