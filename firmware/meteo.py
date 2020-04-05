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

import utime
from device import DEVICE
from tools.nmea import NMEA
import tools.utils as utils
import constants
from math import sin, cos, radians, atan2, degrees, pow, sqrt

#define PRESS_CONV_FACT(X) (X*0.075+800.00) //per barometro young modello 61201 VECCHIA !!!!
#define PRESS_CONV_FACT(X) (X*0.125+600.00)   //per barometro young modello 61202V NUOVA !!!!

class METEO(DEVICE, NMEA):


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

    def _wd_vect_avg(self, samples):
        """Calculates wind vector average direction.

        Params:
            samples(list)
        Returns:
            avg(float)
        """
        avg = 0
        sample_list = []
        try:
            for sample in samples:
                sample_list.append([int(sample[0])* float(self.config['Meteo']['Windspeed_'+self.config['Meteo']['Windspeed_Unit']]), int(sample[1])/10])
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

    def _ws_vect_avg(self, samples):
        """Calculates wind vector average speed.

        Params:
            samples(list)
        Returns:
            avg(float)
        """
        avg = 0
        sample_list = []
        try:
            for sample in samples:
                sample_list.append([int(sample[0])* float(self.config['Meteo']['Windspeed_'+self.config['Meteo']['Windspeed_Unit']]), int(sample[1])/10])
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

    def _ws_avg(self, samples):
        """Calculates average wind speed.

        Params:
            samples(list)
        Returns:
            avg(float)
        """
        avg = 0
        sample_list = []
        try:
            for sample in samples:
                sample_list.append(int(sample[0]) * float(self.config['Meteo']['Windspeed_'+self.config['Meteo']['Windspeed_Unit']]))
            avg = sum(sample_list) / len(sample_list)
        except:
            pass
        return avg

    def _ws_max(self, samples):
        """Calculates max wind speed (gust).

        Params:
            samples(list)
        Returns:
            max(float)
        """
        max = 0
        sample_list = []
        try:
            for sample in samples:
                sample_list.append(int(sample[0]) * float(self.config['Meteo']['Windspeed_'+self.config['Meteo']['Windspeed_Unit']]))
            max = max(sample_list)
        except:
            pass
        return max

    def _wd_max(self, samples):
        """Calculates gust direction.

        Params:
            samples(list)
        Returns:
            max(float)
        """
        max = 0
        try:
            for sample in samples:
                if sample[0] == self._ws_max(samples):
                    max = sample[1] / 10
        except:
            pass
        return max

    def _temp_avg(self, samples):
        """Calculates average air temperature.

        Params:
            samples(list)
        Returns:
            avg(float)
        """
        avg = 0
        sample_list = []
        try:
            for sample in samples:
                sample_list.append(int(sample[2]) * float(self.config['Meteo']['Temp_Conv_0']) - float(self.config['Meteo']['Temp_Conv_1']))
            avg = sum(sample_list) / len(sample_list)
        except:
            pass
        return avg

    def _press_avg(self, samples):
        """Calculates average barometric pressure.

        Params:
            samples(list)
        Returns:
            avg(float)
        """
        avg = 0
        sample_list = []
        try:
            for sample in samples:
                sample_list.append(int(sample[3]) * float(self.config['Meteo']['Press_Conv_0']) + float(self.config['Meteo']['Press_Conv_1']))
            avg = sum(sample_list) / len(sample_list)
        except:
            pass
        return avg

    def _hum_avg(self, samples):
        """Calculates average relative humidity.

        Params:
            samples(list)
        Returns:
            avg(float)
        """
        avg = 0
        sample_list = []
        try:
            for sample in samples:
                sample_list.append(int(sample[4]) * float(self.config['Meteo']['Hum_Conv_0']))
            avg = sum(sample_list) / len(sample_list)
        except:
            pass
        return avg

    def _compass_avg(self, samples):
        """Calculates average heading.

        Params:
            samples(list)
        Returns:
            avg(float)
        """
        avg = 0
        sample_list = []
        try:
            for sample in samples:
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

    def _radiance_avg(self, samples):
        """Calculates average solar radiance.

        Params:
            samples(list)
        Returns:
            avg(float)
        """
        avg = 0
        sample_list = []
        try:
            for sample in samples:
                sample_list.append(int(sample[5]) * float(self.config['Meteo']['Rad_Conv_0']))
            avg = sum(sample_list) / len(sample_list)
        except:
            pass
        return avg

    def main(self):
        """Gets data from weather station

                                       $WIMWV,ddd,a,sss.s,N,A,*hh<CR/LF>
                                          |    |  |   |   | |  |
         NMEA HEADER----------------------|    |  |   |   | |  |
         DIRECTION (0-360 DEGREES)-------------|  |   |   | |  |
         DIRECTION REFERENCE (T)RUE OR (R)ELATIVE-|   |   | |  |
         WIND SPEED (KNOTS)---------------------------|   | |  |
         WIND SPEED UNITS N=KNOTS (NAUTICAL MPH)----------| |  |
         DESIGNATES GOOD DATA-------------------------------|  |
         CHECKSUM FIELD----------------------------------------|

                                       $WIXDR,C,000.0,C,TEMP,H,000,P,%RH,P,0.000,B,BARO,*hh<CR/LF>
         NMEA HEADER----------------------|   |   |   |  |   |  |  |  |  |   |   |  |    |
         TRANSDUCER TYPE = TEMPERATURE--------|   |   |  |   |  |  |  |  |   |   |  |    |
         TEMPERATURE------------------------------|   |  |   |  |  |  |  |   |   |  |    |
         UNITS = CELSIUS------------------------------|  |   |  |  |  |  |   |   |  |    |
         TRANSDUCER ID-----------------------------------|   |  |  |  |  |   |   |  |    |
         TRANSDUCER TYPE = HUMIDITY--------------------------|  |  |  |  |   |   |  |    |
         RELATIVE HUMIDITY--------------------------------------|  |  |  |   |   |  |    |
         UNITS = PERCENT-------------------------------------------|  |  |   |   |  |    |
         TRANSDUCER ID------------------------------------------------|  |   |   |  |    |
         TRANSDUCER TYPE = PRESSURE--------------------------------------|   |   |  |    |
         BAROMETRIC PRESSURE-------------------------------------------------|   |  |    |
         UNITS = BARS------------------------------------------------------------|  |    |
         TRANSDUCER ID--------------------------------------------------------------|    |
         CHECKSUM FIELD------------------------------------------------------------------|

        Returns:
            None
        """
        if not self._init_uart():
            return
        self._led_on()
        if self.config['Data_Format'] == 'NMEA':
            NMEA.__init__(self)
        string_count = 0
        new_string = False
        serial_string = ''
        serial_list = []
        data_string = []
        start = utime.time()
        while string_count < int(self.config['Samples']) // 2:  # Read a pre defined number of strings
            if self.status() == 'off':
                utils.log_file("{} => timeout occourred".format(self.__qualname__), constants.LOG_LEVEL, True)  # DEBUG
                break
            if self.uart.any():
                char = self.uart.readchar()
                if self.config['Data_Format'] == 'NMEA':
                    self.get_sentence(char)
                    if not self.checksum_verified:
                        continue
                    if not self.sentence[0] in self.config['String_To_Acquire']:
                        continue
                    if self.sentence[0] == "WIMWV":
                        valid_data = False
                        if self.sentence[5] != "A":
                            utils.log_file("{} => invalid data".format(self.__qualname__), constants.LOG_LEVEL, True)  # DEBUG
                            continue
                        valid_data = True
                    if valid_data:
                        utils.log_data(self.config['Data_File_Path'], self.config['Data_File_Name'], self.serial_string)
                elif self.config['Data_Format'] == 'STRING':
                    if chr(char) == '\n':
                        new_string = True
                    elif chr(char) == '\r':
                        if new_string:
                            serial_list.append(serial_string.split(self.config['Data_Separator']))
                            serial_string = ''
                            new_string = False
                            string_count += 1
                    else:
                        if new_string:
                            serial_string = serial_string + chr(char)
        epoch = utime.time()
        data_string.append(self.config['String_Label'])
        data_string.append(utils.unix_epoch(epoch))
        data_string.append(utils.datestamp(epoch))  # YYMMDD
        data_string.append(utils.timestamp(epoch))  # hhmmss
        data_string.append("{:.1f}".format(self._wd_vect_avg(serial_list)))  # vectorial avg wind direction
        data_string.append("{:.1f}".format(self._ws_avg(serial_list)))  # avg wind speed
        data_string.append("{:.1f}".format(self._temp_avg(serial_list)))  # avg temp
        data_string.append("{:.1f}".format(self._press_avg(serial_list)))  # avg pressure
        data_string.append("{:.1f}".format(self._hum_avg(serial_list)))  # avg relative humidity
        data_string.append("{:.1f}".format(self._compass_avg(serial_list)))  # avg heading
        data_string.append("{:.1f}".format(self._ws_vect_avg(serial_list)))  # vectorial avg wind speed
        data_string.append("{:.1f}".format(self._ws_max(serial_list)))  # gust speed
        data_string.append("{:.1f}".format(self._wd_max(serial_list)))  # gust direction
        data_string.append("{:0d}".format(len(serial_list)))  # number of samples
        data_string.append("{:.1f}".format(self._radiance_avg(serial_list)))  # solar radiance (optional)
        utils.log_data(','.join(data_string))  # write data to file
        self._deinit_uart()
        self._led_off()
        return
