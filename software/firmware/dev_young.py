import utime
import tools.utils as utils
import config
from math import sin, cos, radians, atan2, degrees, pow, sqrt
from device import DEVICE

class Y32500(DEVICE):

    def __init__(self, instance, tasks=[]):
        DEVICE.__init__(self, instance)
        ########################################################################
        self.tasks = tasks
        if self.tasks:
            if not any( elem in ["start_up","on","off"] for elem in self.tasks):
                self.status(2) # Sets device ready.
                try:
                    self.main()
                except AttributeError:
                    pass
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
        """Performs the device specific initialization sequence."""
        self.on()
        self.off()

    def _wd_vect_avg(self, samples):
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
            utils.log("{} => _wd_vect_avg ({}): {}".format(self.name, type(err).__name__, err), "e")  # DEBUG
        return avg

    def _ws_vect_avg(self, samples):
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
            utils.log("{} => _ws_vect_avg ({}): {}".format(self.name, type(err).__name__, err), "e")  # DEBUG
        return avg

    def _ws_avg(self, samples):
        """Calculates average wind speed."""
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
        """Calculates the gust speed."""
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
        """Calculates the gust direction."""
        maxdir = 0
        try:
            for sample in samples:
                if sample[0] == self._ws_max(samples):
                    maxdir = sample[1] / 10
        except Exception as err:
            utils.log("{} => _wd_max ({}): {}".format(self.name, type(err).__name__, err), "e")  # DEBUG
        return maxdir

    def _temp_avg(self, samples):
        """Calculates the average air temperature."""
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
        """Calculates the average barometric pressure."""
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
        """Calculates the average relative humidity."""
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
            utils.log("{} => _compass_avg ({}): {}".format(self.name, type(err).__name__, err), "e")  # DEBUG
        return avg

    def _radiance_avg(self, samples):
        """Calculates the average solar radiance."""
        avg = 0
        sample_list = []
        try:
            for sample in samples:
                sample_list.append(int(sample[5]) * float(self.config["Meteo"]["Rad_Conv_0"]))
            avg = sum(sample_list) / len(sample_list)
        except Exception as err:
            utils.log("{} => _radiance_avg ({}): {}".format(self.name, type(err).__name__, err), "e")  # DEBUG
        return avg

    def format_data(self, samples):
        """Formats data according to output format."""
        epoch = utime.time()
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
        return data

    def log(self):
        """Writes out acquired data to file."""
        utils.log_data(config.DATA_SEPARATOR.join(self.format_data(self.data)))

    def main(self):
        """Gets data from the meteo station."""
        utils.log("{} => acquiring data...".format(self.name))
        self.led.on()
        new_string = False
        sample = []
        self.data = []
        t0 = utime.time()
        while True:
            if self._timeout(t0, self.timeout):
                utils.log("{} => timeout occourred".format(self.name), "e")  # DEBUG
                if not self.data:
                    utils.log("{} => no data received".format(self.name), "e")  # DEBUG
                break
            if self.uart.any():
                try:
                    char = chr(self.uart.readchar())
                    if char == "\n":
                        new_string = True
                    elif char == "\r":
                        if new_string:
                            self.data.append("".join(sample).split(self.config["Data_Separator"]))
                            sample = []
                            new_string = False
                            if len(self.data) == self.samples:  # Returns if got n-samples
                                break
                    elif new_string:
                        sample.append(char)
                except UnicodeError:
                    continue
        self.led.off()
