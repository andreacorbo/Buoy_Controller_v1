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

"""This module contains standard METEO devices tools."""

from device import DEVICE
from tools.nmea import NMEA
import tools.utils as utils
import constants
from math import sin, cos, radians, atan2, degrees, pow, sqrt

class METEO(DEVICE, NMEA):
    """Creates a meteo device object.

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

    def start_up(self):
        """Performs device specific initialization sequence."""
        self.init_power()

    def _wd_vect_avg(self, strings):
        """Calculates wind vector average direction.

        Params:
            strings(list)
        Returns:
            avg(float)
        """
        avg = 0
        sample_list = []
        try:
            for sample in strings:
                sample_list.append([int(sample[0])* float(self.config["Meteo"]["Windspeed_"+self.config["Meteo"]["Windspeed_Unit"]]), int(sample[1])/10])
            x = 0
            y = 0
            for sample in sample_list:
                direction = sample[1]
                speed = sample[0]
                x = x + (math.sin(math.radians(direction)) * speed)
                y = y + (math.cos(math.radians(direction)) * speed)
            avg = math.degrees(math.atan2(x, y))
            if avg < 0:
                avg += 360
        except:
            pass
        return avg

    def _ws_vect_avg(self, strings):
        """Calculates wind vector average speed.

        Params:
            strings(list)
        Returns:
            avg(float)
        """
        avg = 0
        sample_list = []
        try:
            for sample in strings:
                sample_list.append([int(sample[0])* float(self.config["Meteo"]["Windspeed_"+self.config["Meteo"]["Windspeed_Unit"]]), int(sample[1])/10])
            x = 0
            y = 0
            for sample in sample_list:
                direction = sample[1]
                speed = sample[0]
                x = x + (math.sin(math.radians(direction)) * math.pow(speed,2))
                y = y + (math.cos(math.radians(direction)) * math.pow(speed,2))
            avg = math.sqrt(x+y) / len(sample_list)
        except:
            pass
        return avg

    def _ws_avg(self, strings):
        """Calculates average wind speed.

        Params:
            strings(list)
        Returns:
            avg(float)
        """
        avg = 0
        sample_list = []
        try:
            for sample in strings:
                sample_list.append(int(sample[0]) * float(self.config["Meteo"]["Windspeed_"+self.config["Meteo"]["Windspeed_Unit"]]))
            avg = sum(sample_list) / len(sample_list)
        except:
            pass
        return avg

    def _ws_max(self, strings):
        """Calculates max wind speed (gust).

        Params:
            strings(list)
        Returns:
            max(float)
        """
        max = 0
        sample_list = []
        try:
            for sample in strings:
                sample_list.append(int(sample[0]) * float(self.config["Meteo"]["Windspeed_"+self.config["Meteo"]["Windspeed_Unit"]]))
            max = max(sample_list)
        except:
            pass
        return max

    def _wd_max(self, strings):
        """Calculates gust direction.

        Params:
            strings(list)
        Returns:
            max(float)
        """
        max = 0
        try:
            for sample in strings:
                if sample[0] == self._ws_max(strings):
                    max = sample[1] / 10
        except:
            pass
        return max

    def _temp_avg(self, strings):
        """Calculates average air temperature.

        Params:
            strings(list)
        Returns:
            avg(float)
        """
        avg = 0
        sample_list = []
        try:
            for sample in strings:
                sample_list.append(int(sample[2]) * float(self.config["Meteo"]["Temp_Conv_0"]) - float(self.config["Meteo"]["Temp_Conv_1"]))
            avg = sum(sample_list) / len(sample_list)
        except:
            pass
        return avg

    def _press_avg(self, strings):
        """Calculates average barometric pressure.

        Params:
            strings(list)
        Returns:
            avg(float)
        """
        avg = 0
        sample_list = []
        try:
            for sample in strings:
                sample_list.append(int(sample[3]) * float(self.config["Meteo"]["Press_Conv_0"]) + float(self.config["Meteo"]["Press_Conv_1"]))
            avg = sum(sample_list) / len(sample_list)
        except:
            pass
        return avg

    def _hum_avg(self, strings):
        """Calculates average relative humidity.

        Params:
            strings(list)
        Returns:
            avg(float)
        """
        avg = 0
        sample_list = []
        try:
            for sample in strings:
                sample_list.append(int(sample[4]) * float(self.config["Meteo"]["Hum_Conv_0"]))
            avg = sum(sample_list) / len(sample_list)
        except:
            pass
        return avg

    def _compass_avg(self, strings):
        """Calculates average heading.

        Params:
            strings(list)
        Returns:
            avg(float)
        """
        avg = 0
        sample_list = []
        try:
            for sample in strings:
                sample_list.append(int(sample[6]) / 10)
            x = 0
            y = 0
            for sample in sample_list:
                x = x + math.sin(math.radians(sample))
                y = y + math.cos(math.radians(sample))
            avg = math.degrees(math.atan2(x, y))
            if avg < 0:
                avg += 360
        except:
            pass
        return avg

    def _radiance_avg(self, strings):
        """Calculates average solar radiance.

        Params:
            strings(list)
        Returns:
            avg(float)
        """
        avg = 0
        sample_list = []
        try:
            for sample in strings:
                sample_list.append(int(sample[5]) * float(self.config["Meteo"]["Rad_Conv_0"]))
            avg = sum(sample_list) / len(sample_list)
        except:
            pass
        return avg

    def log(self):
        """Writes out acquired data to file."""
        utils.log_data(",".join(map(str, self.data)))
        return
