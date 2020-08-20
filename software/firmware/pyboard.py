import pyb
import uos
import utime
import uselect
import tools.utils as utils
import config
from device import DEVICE
import _thread

class PYBOARD:
    """Creates a board object."""
    rtc = pyb.RTC()

    devices = {}

    def __init__(self):
        self.config_path  = config.CONFIG_DIR
        self.lastfeed = utime.time()
        self.usb = None
        self.uart = None
        self.int_timer = False
        self.interrupted = None
        self.escaped = False
        self.prompted = False
        self.interactive = False
        self.connected = False
        self.operational = False
        self.irqs = []
        self.pwr_led()
        self.get_config()
        self.line2uart = {9:5, 11:3, 7:1}
        self.uart2stream = {5:self.usb, self.config["Uart"]["Bus"]:self.uart}
        self.init_devices()
        self.init_interrupts()
        self.disable_interrupts()
        self.init_usb()
        self.init_uart()
        self.input = [self.usb, self.uart]

    def init_led(self):
        for led in config.LEDS:
            self.led = pyb.LED(config.LEDS[led]).off()

    def pwr_led(self):
        self.init_led()
        pyb.LED(config.LEDS["PWR"]).on()

    def sleep_led(self):
        self.init_led()
        pyb.LED(config.LEDS["SLEEP"]).on()

    def get_config(self):
        """Gets the device configuration."""
        try:
            self.config = utils.read_cfg(self.__module__ + "." + config.CONFIG_TYPE)[self.__qualname__]
            return self.config
        except Exception as err:
            utils.log("{} => get_config ({}): {}".format(self.__qualname__, type(err).__name__, err), "e")  # DEBUG

    def init_usb(self):
        self.usb = pyb.USB_VCP()

    def init_uart(self):
        """Initializes the uart bus."""
        try:
            self.uart = pyb.UART(int(self.config["Uart"]["Bus"]), int(self.config["Uart"]["Baudrate"]))
            self.uart.init(int(self.config["Uart"]["Baudrate"]),
                bits=int(self.config["Uart"]["Bits"]),
                parity=eval(self.config["Uart"]["Parity"]),
                stop=int(self.config["Uart"]["Stop"]),
                timeout=int(self.config["Uart"]["Timeout"]),
                flow=int(self.config["Uart"]["Flow_Control"]),
                timeout_char=int(self.config["Uart"]["Timeout_Char"]),
                read_buf_len=int(self.config["Uart"]["Read_Buf_Len"]))
        except Exception as err:
            utils.log("{} => init_uart ({}): {}".format(self.__qualname__, type(err).__name__, err), "e")  # DEBUG

    def set_repl(self):
        pyb.repl_uart(self.uart2stream[self.line2uart[self.interrupted]])

    def ext_callback(self, line):
        """Sets board to interactive mode"""
        self.interrupted = line

    def init_interrupts(self):
        """Initializes all external interrupts to wakes up board from sleep mode."""
        for pin in self.config["Irq_Pins"]:
            self.irqs.append(pyb.ExtInt(pyb.Pin(pin[0], pyb.Pin.IN), eval("pyb.ExtInt." + pin[1]), eval("pyb.Pin." + pin[2]), self.ext_callback))

    def enable_interrupts(self):
        """Enables interrupts"""
        for irq in self.irqs:
            irq.enable()

    def disable_interrupts(self):
        """Disables interrupts."""
        for irq in self.irqs:
            irq.disable()

    def timeout_interrupt(self, timer):
        """Reset interrupted condition after 5 secs."""
        self.interrupted = None
        utils.timed = False

    def init_devices(self):
        """ Initializes all configured instruments. """
        utils.msg(" initializing instruments ".upper())
        for port,dev in sorted(config.DEVICES.items()):
            if port >= 0:  # Skips device with a negative port number.
                try:
                    _thread.start_new_thread(utils.execute, ((dev, ["start_up"]),))
                except Exception as err:
                    utils.log("{} => init_devices ({}): {}".format(self.__qualname__, type(err).__name__, err), "e")  # DEBUG
        utime.sleep_ms(500)  # Waits for threads starting.
        while utils.processes:  # Waits until all devices have been initialized.
            continue
        utils.msg("-")

    def set_mode(self, timeout):
        """ Prints out welcome message. """
        print("")
        print(utils.welcome_msg())
        print(
        "\n\r"+
        "[ESC] INTERACTIVE MODE\n\r"+
        "[DEL] FILE TRANSFER MODE\n\r")
        t0 = utime.time()
        while utime.time() - t0 < timeout:
            print("ENTER YOUR CHOICE WITHIN {:0>2} SEC".format(timeout - (utime.time() - t0)), end="\r")
            r, w, x = uselect.select(self.input, [], [], 0)
            if r:
                byte = r[0].read()
                if byte == b"\x1b":  # ESC
                    self.interactive = True
                    print("")
                    break
                elif byte == b"\x1b[3~":  # DEL
                    self.connected = True
                    print("")
                    break
            utime.sleep_ms(500)
        print("\n\r")

    def go_sleep(self, interval):
        """Puts board in sleep mode.

            Parameters:
                ``interval`` :obj:`int` current timestamp.
        """
        utils.log("Sleeping.... wake up in {}".format(utils.time_display(interval)))  # DEBUG
        self.sleep_led()
        self.enable_interrupts()
        remain = config.WD_TIMEOUT - (utime.time() - self.lastfeed) * 1000
        interval = interval * 1000
        if interval - remain > -3000:
            interval = remain - 3000
        self.rtc.wakeup(interval)  # Set next rtc wakeup (ms).
        pyb.stop()
        self.disable_interrupts()
        self.pwr_led()

class SYSMON(DEVICE):

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
        """Performs device specific initialization sequence."""
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
            s=uos.statvfs("/sd")
            return s[0]*s[3]
        except Exception as err:
            utils.log("{} => fs_freespace ({}): {}".format(self.__qualname__, type(err).__name__, err), "e")  # DEBUG
        return 0

    def main(self):
        """Gets data from internal sensors."""
        utils.log("{} => acquiring data...".format(self.name))  # DEBUG
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

    def format_data(self, sample):
        epoch = utime.time()
        data = [
            self.config["String_Label"],
            str(utils.unix_epoch(epoch)),
            utils.datestamp(epoch),  # MMDDYY
            utils.timestamp(epoch),  # hhmmss
            "{:.4f}".format(self.battery_level(sample[0])),  # Battery voltage [V].
            "{:.4f}".format(self.current_level(sample[1])),  # Current consumption [A].
            "{:.4f}".format(self.ad22103(sample[2], sample[6])),  # Internal vessel temp [°C].
            "{:.4f}".format(sample[3]),  # Core temp [°C].
            "{:.4f}".format(sample[4]),  # Core vbat [V].
            "{:.4f}".format(sample[5]),  # Core vref [V].
            "{:.4f}".format(sample[6]),  # Vref [V].
            "{}".format(sample[7]//1024)  # SD free space [kB].
            ]
        return data

    def log(self):
        """Writes out acquired data to file."""
        utils.log_data(config.DATA_SEPARATOR.join(self.format_data(self.data)))
