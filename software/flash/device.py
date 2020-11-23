import pyb
import time
import tools.utils as utils
from configs import dfl, cfg

class DEVICE:

    def __init__(self, instance):
        self.instance = instance
        self.name = self.__module__ + "." + self.__qualname__ + "_" + str(self.instance)
        self.get_config()
        self.samples = 0
        if "Samples" in self.config:
            self.samples = self.config["Samples"]
        self.sample_rate = 0
        if "Sample_Rate" in self.config:
            self.sample_rate = self.config["Sample_Rate"]
        self.timeout = 0
        if self.sample_rate > 0:
            self.timeout = self.samples // self.sample_rate + (self.samples % self.sample_rate > 0) + cfg.TIMEOUT
        self.init_uart()
        self.init_gpio()

    def _timeout(self, start, expire=0):
        """Checks if timeout has expired."""
        if not expire:
            expire = cfg.TIMEOUT
        if expire > 0 and time.time() - start >= expire:
            return True
        return False

    def get_config(self):
        """Gets the device configuration."""
        try:
            self.config = utils.read_cfg(self.__module__)[self.__qualname__]
            return self.config
        except Exception as err:
            utils.log("{} => get_config ({}): {}".format(self.name, type(err).__name__, err), "e")  # DEBUG

    def init_uart(self):
        """Initializes the uart bus."""
        if "Uart" in self.config:
            #self.uart_bus = int(config.UARTS[config.DEVICES[self.name] % len(config.UARTS)])
            self.uart_bus = dfl.UARTS[dfl.DEVS.index(self.name)] if self.name in dfl.DEVS else dfl.UARTS[cfg.DEVS.index(self.name)]
            try:
                self.uart = pyb.UART(self.uart_bus, int(self.config["Uart"]["Baudrate"]))
                self.uart.init(int(self.config["Uart"]["Baudrate"]),
                    bits=int(self.config["Uart"]["Bits"]),
                    parity=eval(self.config["Uart"]["Parity"]),
                    stop=int(self.config["Uart"]["Stop"]),
                    timeout=int(self.config["Uart"]["Timeout"]),
                    flow=int(self.config["Uart"]["Flow_Control"]),
                    timeout_char=int(self.config["Uart"]["Timeout_Char"]),
                    read_buf_len=int(self.config["Uart"]["Read_Buf_Len"]))
            except Exception as err:
                utils.log("{} => init_uart ({}): {}".format(self.name, type(err).__name__, err), "e")  # DEBUG

    def init_gpio(self):
        """Creates the device pin object."""
        try:
            self.gpio = pyb.Pin(dfl.CTRL_PINS[dfl.DEVS.index(self.name) if self.name in dfl.DEVS else cfg.DEVS.index(self.name)], pyb.Pin.OUT, pyb.Pin.PULL_DOWN)
        except KeyError:
            pass
        except Exception as err:
            utils.log("{} => init_gpio ({}): {}".format(self.name, type(err).__name__, err), "e")  # DEBUG

    def on(self):
        """Turns on device."""
        if hasattr(self, "gpio"):
            self.gpio.on()  # set pin to off
        utils.log("{} => {}".format(self.name,self.status(1)))

    def off(self):
        """Turns off device."""
        if hasattr(self, "gpio"):
            self.gpio.off()  # set pin to off
        utils.log("{} => {}".format(self.name,self.status(0)))

    def status(self, status=None):
        """Returns or sets the current device status."""
        if status >= 0:
            dfl.DEVICE_STATUS[dfl.DEVS.index(self.name) if self.name in dfl.DEVS else cfg.DEVS.index(self.name)] = status
        return dfl.STATUS[dfl.DEVICE_STATUS[dfl.DEVS.index(self.name) if self.name in dfl.DEVS else cfg.DEVS.index(self.name)]]
