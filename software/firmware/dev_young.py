import pyb
import time
from math import sin, cos, radians, atan2, degrees, pow, sqrt
import tools.utils as utils
from configs import dfl, cfg
from device import DEVICE

class Y32500(DEVICE):

    def __init__(self, instance):
        DEVICE.__init__(self, instance)
        self.rx_buff = bytearray(1)

    def start_up(self):
        """Performs the instrument specific initialization sequence."""
        self.off()

    def wd_vect_avg(self, samples):
        """Calculates the average wind vector direction."""
        avg = 0
        def samples_():
            i=0
            while i < len(samples):
                yield [int(samples[0+i:4+i]) * float(self.config["Meteo"]["Windspeed_" + self.config["Meteo"]["Windspeed_Unit"]]), int(samples[5+i:9+i])/10]
                i += self.config["Data_Length"]
        try:
            x = 0
            y = 0
            for sample in samples_():
                direction = sample[1]
                speed = sample[0]
                x = x + (sin(radians(direction)) * speed)
                y = y + (cos(radians(direction)) * speed)
            avg = degrees(atan2(x, y))
            if avg < 0:
                avg += 360
        except Exception as err:
            utils.log("{} => wd_vect_avg ({}): {}".format(self.name, type(err).__name__, err), "e")  # DEBUG
        return avg

    def ws_vect_avg(self, samples):
        """Calculates the average wind veector speed."""
        avg = 0
        def samples_():
            i=0
            while i < len(samples):
                yield [int(samples[0+i:4+i]) * float(self.config["Meteo"]["Windspeed_" + self.config["Meteo"]["Windspeed_Unit"]]), int(samples[5+i:9+i])/10]
                i += self.config["Data_Length"]
        try:
            x = 0
            y = 0
            for sample in samples_():
                direction = sample[1]
                speed = sample[0]
                x = x + (sin(radians(direction)) * pow(speed,2))
                y = y + (cos(radians(direction)) * pow(speed,2))
            avg = sqrt(x+y) / len(samples)
        except Exception as err:
            utils.log("{} => ws_vect_avg ({}): {}".format(self.name, type(err).__name__, err), "e")  # DEBUG
        return avg

    def ws_avg(self, samples):
        """Calculates average wind speed."""
        avg = 0
        def samples_():
            i=0
            while i < len(samples):
                yield int(samples[0+i:4+i]) * float(self.config["Meteo"]["Windspeed_" + self.config["Meteo"]["Windspeed_Unit"]])
                i += self.config["Data_Length"]
        try:
            avg = sum(samples_()) / len(samples)
        except Exception as err:
            utils.log("{} => ws_avg ({}): {}".format(self.name, type(err).__name__, err), "e")  # DEBUG
        return avg

    def ws_max(self, samples):
        """Calculates the gust speed."""
        maxspeed = 0
        def samples_():
            i=0
            while i < len(samples):
                yield int(samples[0+i:4+i]) * float(self.config["Meteo"]["Windspeed_" + self.config["Meteo"]["Windspeed_Unit"]])
                i += self.config["Data_Length"]
        try:
            maxspeed = max(samples_())
        except Exception as err:
            utils.log("{} => ws_max ({}): {}".format(self.name, type(err).__name__, err), "e")  # DEBUG
        return maxspeed

    def wd_max(self, samples):
        """Calculates the gust direction."""
        maxdir = 0
        def samples_():
            i=0
            while i < len(samples):
                yield [int(samples[0+i:4+i]) * float(self.config["Meteo"]["Windspeed_" + self.config["Meteo"]["Windspeed_Unit"]]), int(samples[5+i:9+i])/10]
                i += self.config["Data_Length"]
        try:
            for sample in samples_():
                if sample[0] == self.ws_max(samples):
                    maxdir = sample[1] / 10
        except Exception as err:
            utils.log("{} => wd_max ({}): {}".format(self.name, type(err).__name__, err), "e")  # DEBUG
        return maxdir

    def temp_avg(self, samples):
        """Calculates the average air temperature."""
        avg = 0
        def samples_():
            i=0
            while i < len(samples):
                yield int(samples[10+i:14+i]) * float(self.config["Meteo"]["Temp_Conv_0"]) - float(self.config["Meteo"]["Temp_Conv_1"])
                i += self.config["Data_Length"]
        try:
            avg = sum(samples_()) / len(samples)
        except Exception as err:
            utils.log("{} => temp_avg ({}): {}".format(self.name, type(err).__name__, err), "e")  # DEBUG
        return avg

    def press_avg(self, samples):
        """Calculates the average barometric pressure."""
        avg = 0
        def samples_():
            i=0
            while i < len(samples):
                yield int(samples[15+i:19+i]) * float(self.config["Meteo"]["Press_Conv_0"]) + float(self.config["Meteo"]["Press_Conv_1"])
                i += self.config["Data_Length"]
        try:
            avg = sum(samples_()) / len(samples)
        except Exception as err:
            utils.log("{} => press_avg ({}): {}".format(self.name, type(err).__name__, err), "e")  # DEBUG
        return avg

    def hum_avg(self, samples):
        """Calculates the average relative humidity."""
        avg = 0
        def samples_():
            i=0
            while i < len(samples):
                yield int(samples[20+i:24+i]) * float(self.config["Meteo"]["Hum_Conv_0"])
                i += self.config["Data_Length"]
        try:
            avg = sum(samples_()) / len(samples)
        except Exception as err:
            utils.log("{} => hum_avg ({}): {}".format(self.name, type(err).__name__, err), "e")  # DEBUG
        return avg

    def compass_avg(self, samples):
        """Calculates the average heading."""
        avg = 0
        def samples_():
            i=0
            while i < len(samples):
                yield int(samples[30+i:34+i]) / 10
                i += self.config["Data_Length"]
        try:
            x = 0
            y = 0
            for sample in samples_():
                x = x + sin(radians(sample))
                y = y + cos(radians(sample))
            avg = degrees(atan2(x, y))
            if avg < 0:
                avg += 360
        except Exception as err:
            utils.log("{} => compass_avg ({}): {}".format(self.name, type(err).__name__, err), "e")  # DEBUG
        return avg

    def radiance_avg(self, samples):
        """Calculates the average solar radiance."""
        avg = 0
        def samples_():
            i=0
            while i < len(samples):
                yield int(samples[25+i:29+i]) * float(self.config["Meteo"]["Rad_Conv_0"])
                i += self.config["Data_Length"]
        try:
            avg = sum(samples_()) / len(samples)
        except Exception as err:
            utils.log("{} => radiance_avg ({}): {}".format(self.name, type(err).__name__, err), "e")  # DEBUG
        return avg

    def log(self):
        """Writes out acquired data to file."""
        epoch = time.time()
        samples = self.data.decode("utf-8")
        utils.log_data(
            "{},{},{},{},{:.1f},{:.1f},{:.1f},{:.1f},{:.1f},{:.1f},{:.1f},{:.1f},{:.1f},{:0d},{:.1f}".format(
                self.config["String_Label"],
                str(utils.unix_epoch(epoch)),
                utils.datestamp(epoch),  # MMDDYY
                utils.timestamp(epoch),  # hhmmss
                self.wd_vect_avg(samples),  # vectorial avg wind direction
                self.ws_avg(samples),  # avg wind speed
                self.temp_avg(samples),  # avg temp
                self.press_avg(samples),  # avg pressure
                self.hum_avg(samples),  # avg relative humidity
                self.compass_avg(samples),  # avg heading
                self.ws_vect_avg(samples),  # vectorial avg wind speed
                self.ws_max(samples),  # gust speed
                self.wd_max(samples),  # gust direction
                int(len(samples) / self.config["Data_Length"]),  # number of strings
                self.radiance_avg(samples)  # solar radiance (optional)
                )
            )

    def main(self, tasks=[]):
        """Gets data from the meteo station."""
        utils.log("{} => acquiring data...".format(self.name))  # DEBUG
        self.status(2)
        self.init_uart()
        pyb.LED(3).on()
        self.data = bytearray()
        nl = False
        t0 = time.time()
        while True:  # Reads out n-strings.
            if self._timeout(t0, self.timeout):
                utils.log("{} => no data received".format(self.name), "e")
                break
            if self.uart.any():
                self.uart.readinto(self.rx_buff)
                try:
                    self.rx_buff.decode("utf-8")
                except UnicodeError:
                    nl = False
                    sample = bytearray()
                    continue
                if self.rx_buff == '\n':
                    nl = True
                    sample = bytearray()
                elif nl and self.rx_buff == '\r':
                    sample.extend(b'\r\n')
                    self.data.extend(sample)
                    nl = False
                elif nl:
                    sample.extend(self.rx_buff)
                if len(self.data) == self.config["Samples"]*self.config["Data_Length"]:
                    break
        for t in tasks:
            exec("self."+t+"()",{"self":self})
        pyb.LED(3).off()
        self.uart.deinit()
