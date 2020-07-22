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

"""This module contains specific Young METEO devices tools."""

import utime
from device import DEVICE
from tools.nmea import NMEA
import tools.utils as utils
import constants
from math import sin, cos, radians, atan2, degrees, pow, sqrt

class Y32500(DEVICE, NMEA):
    """Creates a Young Y32500 METEO device object.
    #define PRESS_CONV_FACT(X) (X*0.075+800.00) //per barometro young modello 61201 VECCHIA !!!!
    #define PRESS_CONV_FACT(X) (X*0.125+600.00)   //per barometro young modello 61202V NUOVA !!!!

    Extends the :class:`device` and the :class:`tools.nmea` classes.

    Parameters:
        ``instance`` :obj:`str` The object instance number (if multiple devices
        are present) needs a correspondent section in the config_file.

        ``tasks`` :obj:`list` (optional) A list of methods to be executed at
        object creation.
    """

    def __init__(self, instance, tasks=[], data_tasks=["log"]):
        """Constructor method."""
        NMEA.__init__(self, instance)
        DEVICE.__init__(self, instance, tasks, data_tasks)

    def start_up(self):
        """Performs the device specific initialization sequence."""
        self.off()
        return

    def _wd_vect_avg(self, samples):
        """Calculates the average wind vector direction.

        Parameters:
            ``samples`` :obj:`list` [[sample1], [sample1]...]
        Returns:
            ``avg`` :obj:`float` The average wind vector direction (degrees).
        """
        avg = 0
        sample_list = []
        try:
            for sample in samples:
                sample_list.append([int(sample[0]) * float(self.config["Meteo"]["Windspeed_" + self.config["Meteo"]["Windspeed_Unit"]]), int(sample[1])/10])
            x = 0
            y = 0
            for sample in sample_list:
                direction = sample[1]
                speed = sample[0]
                x = x + (sin(radians(direction)) * speed)
                y = y + (cos(radians(direction)) * speed)
            avg = degrees(atan2(x, y))
            if avg < 0:
                avg += 360
        except Exception as err:
            utils.log("{} => _wd_vect_avg ({}): {}".format(self.name, type(err).__name__, err), "e")  # DEBUG
        return avg

    def _ws_vect_avg(self, samples):
        """Calculates the average wind veector speed.

        Parameters:
            ``samples`` :obj:`list` [[sample1], [sample1]...]
        Returns:
            ``avg`` :obj:`float` The average wind vector speed (m/s).
        """
        avg = 0
        sample_list = []
        try:
            for sample in samples:
                sample_list.append([int(sample[0])* float(self.config["Meteo"]["Windspeed_" + self.config["Meteo"]["Windspeed_Unit"]]), int(sample[1])/10])
            x = 0
            y = 0
            for sample in sample_list:
                direction = sample[1]
                speed = sample[0]
                x = x + (sin(radians(direction)) * pow(speed,2))
                y = y + (cos(radians(direction)) * pow(speed,2))
            avg = sqrt(x+y) / len(sample_list)
        except Exception as err:
            utils.log("{} => _ws_vect_avg ({}): {}".format(self.name, type(err).__name__, err), "e")  # DEBUG
        return avg

    def _ws_avg(self, samples):
        """Calculates average wind speed.

        Parameters:
            ``samples`` :obj:`list` [[sample1], [sample1]...]
        Returns:
            ``avg`` :obj:`float` The average wind speed (m/s).
        """
        avg = 0
        sample_list = []
        try:
            for sample in samples:
                sample_list.append(int(sample[0]) * float(self.config["Meteo"]["Windspeed_" + self.config["Meteo"]["Windspeed_Unit"]]))
            avg = sum(sample_list) / len(sample_list)
        except Exception as err:
            utils.log("{} => _ws_avg ({}): {}".format(self.name, type(err).__name__, err), "e")  # DEBUG
        return avg

    def _ws_max(self, samples):
        """Calculates the gust speed.

        Parameters:
            ``samples`` :obj:`list` [[sample1], [sample1]...]
        Returns:
            ``maxspeed`` :obj:`float` The gust speed (m/s).
        """
        maxspeed = 0
        sample_list = []
        try:
            for sample in samples:
                sample_list.append(int(sample[0]) * float(self.config["Meteo"]["Windspeed_" + self.config["Meteo"]["Windspeed_Unit"]]))
            maxspeed = max(sample_list)
        except Exception as err:
            utils.log("{} => _ws_max ({}): {}".format(self.name, type(err).__name__, err), "e")  # DEBUG
        return maxspeed

    def _wd_max(self, samples):
        """Calculates the gust direction.

        Parameters:
            ``samples`` :obj:`list` [[sample1], [sample1]...]
        Returns:
            ``maxdir`` :obj:`float` The gust direction (degrees).
        """
        maxdir = 0
        try:
            for sample in samples:
                if sample[0] == self._ws_max(samples):
                    maxdir = sample[1] / 10
        except Exception as err:
            utils.log("{} => _wd_max ({}): {}".format(self.name, type(err).__name__, err), "e")  # DEBUG
        return maxdir

    def _temp_avg(self, samples):
        """Calculates the average air temperature.

        Parameters:
            ``samples`` :obj:`list` [[sample1], [sample1]...]
        Returns:
            ``avg`` :obj:`float` The average air temperature (°C).
        """
        avg = 0
        sample_list = []
        try:
            for sample in samples:
                sample_list.append(int(sample[2]) * float(self.config["Meteo"]["Temp_Conv_0"]) - float(self.config["Meteo"]["Temp_Conv_1"]))
            avg = sum(sample_list) / len(sample_list)
        except Exception as err:
            utils.log("{} => _temp_avg ({}): {}".format(self.name, type(err).__name__, err), "e")  # DEBUG
        return avg

    def _press_avg(self, samples):
        """Calculates the average barometric pressure.

        Parameters:
            ``samples`` :obj:`list` [[sample1], [sample1]...]
        Returns:
            ``avg`` :obj:`float` The average barometric pressure (mBar).
        """
        avg = 0
        sample_list = []
        try:
            for sample in samples:
                sample_list.append(int(sample[3]) * float(self.config["Meteo"]["Press_Conv_0"]) + float(self.config["Meteo"]["Press_Conv_1"]))
            avg = sum(sample_list) / len(sample_list)
        except Exception as err:
            utils.log("{} => _press_avg ({}): {}".format(self.name, type(err).__name__, err), "e")  # DEBUG
        return avg

    def _hum_avg(self, samples):
        """Calculates the average relative humidity.

        Parameters:
            ``samples`` :obj:`list` [[sample1], [sample1]...]
        Returns:
            ``avg`` :obj:`float` The average relative humidity (%).
        """
        avg = 0
        sample_list = []
        try:
            for sample in samples:
                sample_list.append(int(sample[4]) * float(self.config["Meteo"]["Hum_Conv_0"]))
            avg = sum(sample_list) / len(sample_list)
        except Exception as err:
            utils.log("{} => _hum_avg ({}): {}".format(self.name, type(err).__name__, err), "e")  # DEBUG
        return avg

    def _compass_avg(self, samples):
        """Calculates the average heading.

        Parameters:
            ``samples`` :obj:`list` [[sample1], [sample1]...]
        Returns:
            ``avg`` :obj:`float` The average heading (°).
        """
        avg = 0
        sample_list = []
        try:
            for sample in samples:
                sample_list.append(int(sample[6]) / 10)
            x = 0
            y = 0
            for sample in sample_list:
                x = x + sin(radians(sample))
                y = y + cos(radians(sample))
            avg = degrees(atan2(x, y))
            if avg < 0:
                avg += 360
        except Exception as err:
            utils.log("{} => _compass_avg ({}): {}".format(self.name, type(err).__name__, err), "e")  # DEBUG
        return avg

    def _radiance_avg(self, samples):
        """Calculates the average solar radiance.

        Parameters:
            ``samples`` :obj:`list` [[sample1], [sample1]...]
        Returns:
            ``avg`` :obj:`float` The average solar radiance (W/m^2).
        """
        avg = 0
        sample_list = []
        try:
            for sample in samples:
                sample_list.append(int(sample[5]) * float(self.config["Meteo"]["Rad_Conv_0"]))
            avg = sum(sample_list) / len(sample_list)
        except Exception as err:
            utils.log("{} => _radiance_avg ({}): {}".format(self.name, type(err).__name__, err), "e")  # DEBUG
        return avg

    def _format_data(self, samples):
        """Formats data according to output format.

            Parameters:
                ``samples`` :obj:`list` [[sample1], [sample1]...]
            Returns:
                ``data`` :obj:`list`
            """
        epoch = utime.time()
        try:
            data = [
                self.config["String_Label"],
                str(utils.unix_epoch(epoch)),
                utils.datestamp(epoch),  # MMDDYY
                utils.timestamp(epoch),  # hhmmss
                "{:.1f}".format(self._wd_vect_avg(samples)),  # vectorial avg wind direction
                "{:.1f}".format(self._ws_avg(samples)),  # avg wind speed
                "{:.1f}".format(self._temp_avg(samples)),  # avg temp
                "{:.1f}".format(self._press_avg(samples)),  # avg pressure
                "{:.1f}".format(self._hum_avg(samples)),  # avg relative humidity
                "{:.1f}".format(self._compass_avg(samples)),  # avg heading
                "{:.1f}".format(self._ws_vect_avg(samples)),  # vectorial avg wind speed
                "{:.1f}".format(self._ws_max(samples)),  # gust speed
                "{:.1f}".format(self._wd_max(samples)),  # gust direction
                "{:0d}".format(len(samples)),  # number of strings
                "{:.1f}".format(self._radiance_avg(samples))  # solar radiance (optional)
                ]
        except Exception as err:
            utils.log("{} => _format_data ({}): {}".format(self.name, type(err).__name__, err), "e")  # DEBUG
            return
        return data

    def log(self):
        """Writes out acquired data to file."""
        utils.log_data(constants.DATA_SEPARATOR.join(self._format_data(self.data)))
        return

    def main(self):
        """Gets data from the meteo station."""

        utils.log("{} => acquiring data...".format(self.name))
        self.led_on()
        new_string = False
        string = []
        self.data = []
        while True:
            if not self.status() == 'ready':
                utils.log("{} => timeout occourred".format(self.name), "e")  # DEBUG
                break
            if self.uart.any():
                char = chr(self.uart.readchar())
                if char == "\n":
                    new_string = True
                elif char == "\r":
                    if new_string:
                        self.data.append("".join(string).split(self.config["Data_Separator"]))
                        string = []
                        new_string = False
                        if len(self.data) == self.samples:
                            break
                else:
                    if new_string:
                        string.append(char)
        self.led_off()
        return
