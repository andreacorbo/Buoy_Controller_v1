import pyb
import time
import os
import tools.utils as utils
from configs import dfl, cfg
from device import DEVICE

class SYSMON(DEVICE):

    def __init__(self, instance):
        DEVICE.__init__(self, instance)

    def start_up(self):
        """Performs the instrument specific initialization sequence."""
        self.status(1)  # Virtual device is always on.

    def adcall_mask(self, channels):
        """Creates a mask for the adcall method with the adc's channels to acquire.

            Parameters:
                ``channels`` :obj:`dict` adc channels.
            Returns:
                ``mask`` :obj:`hex`
        """
        mask = []
        chs = [16,17,18]  # MCU_TEMP, VREF, VBAT
        chs.extend(channels)
        for i in reversed(range(19)):
            if i in chs:
                mask.append("1")
            else:
                mask.append("0")
        return eval(hex(int("".join(mask), 2)))

    def ad22103(self, vout, vsupply):
        try:
            return (vout * 3.3 / vsupply - 0.25) / 0.028
        except Exception as err:
            utils.log("{} => ad22103 ({}): {}".format(self.__qualname__, type(err).__name__, err), "e")  # DEBUG
        return 0

    def battery_level(self, vout):
        """Return calibrated main power source voltage level.

            Parameters:
                ``vout`` :obj:`float` direct adc read.
            Returns:
                ``vout`` :obj: `float` calibrated value.
        """
        try:
            return vout * self.config["Adc"]["Channels"]["Battery_Level"]["Calibration_Coeff"]
        except Exception as err:
            utils.log("{} => battery_level ({}): {}".format(self.__qualname__, type(err).__name__, err), "e")  # DEBUG
        return 0

    def current_level(self, vout):
        """Returns the calibrated total current consumption.

            Parameters:
                ``vout`` :obj:`float` direct adc read.
            Returns:
                ``aout`` :obj: `float` calibrated value.
        """
        try:
            return vout * self.config["Adc"]["Channels"]["Current_Level"]["Calibration_Coeff"]
        except Exception as err:
            utils.log("{} => current_level ({}): {}".format(self.__qualname__, type(err).__name__, err), "e")  # DEBUG
        return 0

    def fs_freespace(self):
        """Returns the filesystem free space (bytes)."""
        try:
            s=os.statvfs("/sd")
            return s[0]*s[3]
        except Exception as err:
            utils.log("{} => fs_freespace ({}): {}".format(self.__qualname__, type(err).__name__, err), "e")  # DEBUG
        return 0

    def log(self):
        """Writes out acquired data to file."""
        utils.log("{} => acquiring data...".format(self.name))  # DEBUG
        if self.main():
            epoch = time.time()
            if self.main():
                utils.log_data(
                    config.DATA_SEPARATOR.join(
                        [
                            self.config["String_Label"],
                            str(utils.unix_epoch(epoch)),
                            utils.datestamp(epoch),  # MMDDYY
                            utils.timestamp(epoch),  # hhmmss
                            "{:.4f}".format(self.battery_level(self.data[0])),  # Battery voltage [V].
                            "{:.4f}".format(self.current_level(self.data[1])),  # Current consumption [A].
                            "{:.4f}".format(self.ad22103(self.data[2], self.data[6])),  # Internal vessel temp [°C].
                            "{:.4f}".format(self.data[3]),  # Core temp [°C].
                            "{:.4f}".format(self.data[4]),  # Core vbat [V].
                            "{:.4f}".format(self.data[5]),  # Core vref [V].
                            "{:.4f}".format(self.data[6]),  # Vref [V].
                            "{}".format(self.data[7]//1024)  # SD free space [kB].
                        ]
                    )
                )

    def main(self):
        """Gets data from internal sensors."""
        self.status(2)
        self.led.on()
        core_temp = 0
        core_vbat = 0
        core_vref = 0
        vref = 0
        battery_level = 0
        current_level = 0
        ambient_temperature = 0
        self.data = []
        channels = []
        for key in self.config["Adc"]["Channels"].keys():
            channels.append(self.config["Adc"]["Channels"][key]["Ch"])
        adcall = pyb.ADCAll(int(self.config["Adc"]["Bit"]), self.adcall_mask(channels))
        for i in range(int(self.samples) * int(self.sample_rate)):
            core_temp += adcall.read_core_temp()
            core_vbat += adcall.read_core_vbat()
            core_vref += adcall.read_core_vref()
            vref += adcall.read_vref()
            battery_level += adcall.read_channel(self.config["Adc"]["Channels"]["Battery_Level"]["Ch"])
            current_level += adcall.read_channel(self.config["Adc"]["Channels"]["Current_Level"]["Ch"])
            ambient_temperature += adcall.read_channel(self.config["Adc"]["Channels"]["Ambient_Temperature"]["Ch"])
            i += 1
        core_temp = core_temp / i
        core_vbat = core_vbat / i
        core_vref = core_vref / i
        vref = vref / i
        battery_level = battery_level / i * vref / pow(2, int(self.config["Adc"]["Bit"]))
        current_level = current_level / i * vref / pow(2, int(self.config["Adc"]["Bit"]))
        ambient_temperature = ambient_temperature / i * vref / pow(2, int(self.config["Adc"]["Bit"]))
        self.data.append(battery_level)
        self.data.append(current_level)
        self.data.append(ambient_temperature)
        self.data.append(core_temp)
        self.data.append(core_vbat)
        self.data.append(core_vref)
        self.data.append(vref)
        self.data.append(self.fs_freespace())
        self.led.off()
        return True
