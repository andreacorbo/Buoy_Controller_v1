import utime
import tools.utils as utils
import config
from math import sin, cos, radians, atan2, degrees, pow, sqrt
from device import DEVICE

class Y32500(DEVICE):

    def __init__(self, instance, tasks=[]):
        DEVICE.__init__(self, instance)
        self.data = []
        ########################################################################
        self.tasks = tasks
        if self.tasks:
            if not any( elem in ["start_up","on","off"] for elem in self.tasks):
                self.main()
            for task in self.tasks:
                method = task
                param_dict={"self":self}
                param_list=[]
                params=""
                if type(task) == tuple:
                    method = task[0]
                    i = 0
                    for param in task[1:]:
                        param_dict["param"+str(i)] = task[1:][i]
                        param_list.append("param"+str(i))
                        params = ",".join(param_list)
                exec("self."+ method +"(" + params + ")", param_dict)
        ########################################################################

    def start_up(self):
        """Performs the instrument specific initialization sequence."""
        self.off()

    def wd_vect_avg(self, samples):
        """Calculates the average wind vector direction."""
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
            utils.log("{} => wd_vect_avg ({}): {}".format(self.name, type(err).__name__, err), "e")  # DEBUG
        return avg

    def ws_vect_avg(self, samples):
        """Calculates the average wind veector speed."""
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
            utils.log("{} => ws_vect_avg ({}): {}".format(self.name, type(err).__name__, err), "e")  # DEBUG
        return avg

    def ws_avg(self, samples):
        """Calculates average wind speed."""
        avg = 0
        sample_list = []
        try:
            for sample in samples:
                sample_list.append(int(sample[0]) * float(self.config["Meteo"]["Windspeed_" + self.config["Meteo"]["Windspeed_Unit"]]))
            avg = sum(sample_list) / len(sample_list)
        except Exception as err:
            utils.log("{} => ws_avg ({}): {}".format(self.name, type(err).__name__, err), "e")  # DEBUG
        return avg

    def ws_max(self, samples):
        """Calculates the gust speed."""
        maxspeed = 0
        sample_list = []
        try:
            for sample in samples:
                sample_list.append(int(sample[0]) * float(self.config["Meteo"]["Windspeed_" + self.config["Meteo"]["Windspeed_Unit"]]))
            maxspeed = max(sample_list)
        except Exception as err:
            utils.log("{} => ws_max ({}): {}".format(self.name, type(err).__name__, err), "e")  # DEBUG
        return maxspeed

    def wd_max(self, samples):
        """Calculates the gust direction."""
        maxdir = 0
        try:
            for sample in samples:
                if sample[0] == self.ws_max(samples):
                    maxdir = sample[1] / 10
        except Exception as err:
            utils.log("{} => wd_max ({}): {}".format(self.name, type(err).__name__, err), "e")  # DEBUG
        return maxdir

    def temp_avg(self, samples):
        """Calculates the average air temperature."""
        avg = 0
        sample_list = []
        try:
            for sample in samples:
                sample_list.append(int(sample[2]) * float(self.config["Meteo"]["Temp_Conv_0"]) - float(self.config["Meteo"]["Temp_Conv_1"]))
            avg = sum(sample_list) / len(sample_list)
        except Exception as err:
            utils.log("{} => temp_avg ({}): {}".format(self.name, type(err).__name__, err), "e")  # DEBUG
        return avg

    def press_avg(self, samples):
        """Calculates the average barometric pressure."""
        avg = 0
        sample_list = []
        try:
            for sample in samples:
                sample_list.append(int(sample[3]) * float(self.config["Meteo"]["Press_Conv_0"]) + float(self.config["Meteo"]["Press_Conv_1"]))
            avg = sum(sample_list) / len(sample_list)
        except Exception as err:
            utils.log("{} => press_avg ({}): {}".format(self.name, type(err).__name__, err), "e")  # DEBUG
        return avg

    def hum_avg(self, samples):
        """Calculates the average relative humidity."""
        avg = 0
        sample_list = []
        try:
            for sample in samples:
                sample_list.append(int(sample[4]) * float(self.config["Meteo"]["Hum_Conv_0"]))
            avg = sum(sample_list) / len(sample_list)
        except Exception as err:
            utils.log("{} => hum_avg ({}): {}".format(self.name, type(err).__name__, err), "e")  # DEBUG
        return avg

    def compass_avg(self, samples):
        """Calculates the average heading."""
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
            utils.log("{} => compass_avg ({}): {}".format(self.name, type(err).__name__, err), "e")  # DEBUG
        return avg

    def radiance_avg(self, samples):
        """Calculates the average solar radiance."""
        avg = 0
        sample_list = []
        try:
            for sample in samples:
                sample_list.append(int(sample[5]) * float(self.config["Meteo"]["Rad_Conv_0"]))
            avg = sum(sample_list) / len(sample_list)
        except Exception as err:
            utils.log("{} => radiance_avg ({}): {}".format(self.name, type(err).__name__, err), "e")  # DEBUG
        return avg

    def format_data(self, samples):
        """Formats data according to output format."""
        epoch = utime.time()
        data = [
            self.config["String_Label"],
            str(utils.unix_epoch(epoch)),
            utils.datestamp(epoch),  # MMDDYY
            utils.timestamp(epoch),  # hhmmss
            "{:.1f}".format(self.wd_vect_avg(samples)),  # vectorial avg wind direction
            "{:.1f}".format(self.ws_avg(samples)),  # avg wind speed
            "{:.1f}".format(self.temp_avg(samples)),  # avg temp
            "{:.1f}".format(self.press_avg(samples)),  # avg pressure
            "{:.1f}".format(self.hum_avg(samples)),  # avg relative humidity
            "{:.1f}".format(self.compass_avg(samples)),  # avg heading
            "{:.1f}".format(self.ws_vect_avg(samples)),  # vectorial avg wind speed
            "{:.1f}".format(self.ws_max(samples)),  # gust speed
            "{:.1f}".format(self.wd_max(samples)),  # gust direction
            "{:0d}".format(len(samples)),  # number of strings
            "{:.1f}".format(self.radiance_avg(samples))  # solar radiance (optional)
            ]
        return data

    def log(self):
        """Writes out acquired data to file."""
        if self.data:
            utils.log_data(config.DATA_SEPARATOR.join(self.format_data(self.data)))

    def main(self):
        """Gets data from the meteo station."""
        utils.log("{} => acquiring data...".format(self.name))
        self.led.on()
        new_string = False
        r_buff = bytearray(1)
        sample = []
        t0 = utime.time()
        while len(self.data) <  self.samples:  # Reads out n-strings.
            if self._timeout(t0, self.timeout):
                utils.log("{} => timeout occourred".format(self.name), "e")
                if not self.data:
                    utils.log("{} => no data received".format(self.name), "e")
                break
            if self.uart.any():
                self.uart.readinto(r_buff)
                for byte in r_buff:
                    try:
                        ascii = chr(byte)
                        if ascii == "\n":
                            new_string = True
                        elif ascii == "\r":
                            if new_string:
                                self.data.append("".join(sample).split(self.config["Data_Separator"]))
                                sample = []
                                new_string = False
                        elif new_string:
                            sample.append(ascii)
                    except UnicodeError:
                        continue
        self.led.off()
