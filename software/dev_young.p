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

"""This module contains specific Young METEO devices tools."""

from dev_meteo import METEO
import constants
import tools.utils as utils
import utime

class Y32500(METEO):
    """Creates a Young Y32500 METEO device object.
    #define PRESS_CONV_FACT(X) (X*0.075+800.00) //per barometro young modello 61201 VECCHIA !!!!
    #define PRESS_CONV_FACT(X) (X*0.125+600.00)   //per barometro young modello 61202V NUOVA !!!!

    Extends the :class:`dev_meteo.METEO` class.

    Parameters:
        ``instance`` :obj:`str` The object instance number (if multiple devices
        are present) needs a correspondent section in the config_file.

        ``tasks`` :obj:`list` (optional) A list of methods to be executed at
        object creation.
    """

    def __init__(self, instance, tasks=[]):
        """Constructor method."""
        METEO.__init__(self, instance, tasks)
        data_tasks = ["log"]
        if tasks:
            if any(elem in data_tasks for elem in tasks):
                if self.main():
                    for task in tasks:
                        eval("self." + task + "()", {"self":self})
            else:
                for task in tasks:
                    eval("self." + task + "()", {"self":self})

    def main(self):
        """Gets data from meteo station

                                       $WIMWV,ddd,a,sss.s,N,A,*hh<CR/LF>
                                          |    |  |   |   | |  |
         NMEA HEADER______________________|    |  |   |   | |  |
         DIRECTION (0-360 DEGREES)_____________|  |   |   | |  |
         DIRECTION REFERENCE (T)RUE OR (R)ELATIVE_|   |   | |  |
         WIND SPEED (KNOTS)___________________________|   | |  |
         WIND SPEED UNITS N=KNOTS (NAUTICAL MPH)__________| |  |
         DESIGNATES GOOD DATA_______________________________|  |
         CHECKSUM FIELD________________________________________|

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
            True or False.
        """

        utils.log_file("{} => acquiring data...".format(self.name), constants.LOG_LEVEL)
        self.led_on()
        string_count = 0
        new_string = False
        string = ""
        strings = []
        self.data = []
        while string_count < self.config["Samples"]:
            if not self.status() == "READY":  # Exits if the device has been switched off by scheduler.
                utils.log_file("{} => timeout occourred".format(self.name), constants.LOG_LEVEL, True)  # DEBUG
                return False
            if self.uart.any():
                char = self.uart.readchar()
                if self.config["Data_Format"] == "STRING":
                    if chr(char) == "\n":
                        new_string = True
                    elif chr(char) == "\r":
                        if new_string:
                            strings.append(string.split(self.config["Data_Separator"]))
                            string = ""
                            new_string = False
                            string_count += 1
                    else:
                        if new_string:
                            string = string + chr(char)
                elif self.config["Data_Format"] == "NMEA":
                    self.get_sentence(char)
                    if self.checksum_verified:
                        if self.sentence[0] in self.config["String_To_Acquire"]:
                            if self.sentence[0] == "WIMWV":
                                valid_data = False
                                if self.sentence[5] == "A":
                                    return True
                                else:
                                    utils.log_file("{} => invalid data received".format(self.name), constants.LOG_LEVEL, True)  # DEBUG
        epoch = utime.time()
        self.data.append(self.config["String_Label"])
        self.data.append(utils.unix_epoch(epoch))
        self.data.append(utils.datestamp(epoch))  # YYMMDD
        self.data.append(utils.timestamp(epoch))  # hhmmss
        self.data.append("{:.1f}".format(self._wd_vect_avg(strings)))  # vectorial avg wind direction
        self.data.append("{:.1f}".format(self._ws_avg(strings)))  # avg wind speed
        self.data.append("{:.1f}".format(self._temp_avg(strings)))  # avg temp
        self.data.append("{:.1f}".format(self._press_avg(strings)))  # avg pressure
        self.data.append("{:.1f}".format(self._hum_avg(strings)))  # avg relative humidity
        self.data.append("{:.1f}".format(self._compass_avg(strings)))  # avg heading
        self.data.append("{:.1f}".format(self._ws_vect_avg(strings)))  # vectorial avg wind speed
        self.data.append("{:.1f}".format(self._ws_max(strings)))  # gust speed
        self.data.append("{:.1f}".format(self._wd_max(strings)))  # gust direction
        self.data.append("{:0d}".format(len(strings)))  # number of strings
        self.data.append("{:.1f}".format(self._radiance_avg(strings)))  # solar radiance (optional)
        return True
