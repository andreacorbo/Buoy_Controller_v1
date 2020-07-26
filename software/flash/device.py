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

"""This module contains standard device tools."""

import pyb
import utime
import tools.utils as utils
import constants

class DEVICE(object):
    """Creates a device object.

    Parameters:
        ``instance`` :obj:`str` The object instance number (if multiple devices
        are present) needs a correspondent section in the config_file.
    """

    def __init__(self, instance, tasks=[], data_tasks=[]):
        self.instance = instance
        self.name = self.__module__ + "." + self.__qualname__ + "_" + self.instance
        self.timeout = constants.TIMEOUT
        self.uart_bus = 0
        self.uart_slot = 0
        self.activation_delay = 0
        self.get_config()
        self.warmup_interval = self.config["Warmup_Interval"]
        self.samples = None
        if "Samples" in self.config:
            self.samples = self.config["Samples"]
        self.sample_rate = None
        if "Sample_Rate" in self.config:
            self.sample_rate = self.config["Sample_Rate"]
        self.init_uart()
        self.init_gpio()
        self.init_led()
        self.tasks = tasks
        self.data_tasks = data_tasks
        if self.tasks:
            if any(elem[0] if type(elem) == tuple else elem in self.data_tasks for elem in self.tasks):
                self.main()
            for task in self.tasks:
                func = task
                param_dict={"self":self}
                param_list=""
                if type(task) == tuple:
                    func = task[0]
                    for param in task[1:]:
                        param_dict[str(param)] = param
                    param_list = ",".join(map(str,task[1:]))
                exec("self."+ func +"(" + param_list + ")", param_dict)

    def _timeout(self, start, timeout=None):
        """Checks if a timeout occourred

        Params:
            start(int)
        Returns:
            True or False
        """
        if timeout is None:
            timeout = self.timeout
        if timeout > 0 and utime.time() - start >= timeout:
            return True
        return False

    def get_config(self):
        """Gets the device configuration."""
        #try:
            #self.config = utils.read_config(self.__module__ + "." + constants.CONFIG_TYPE)[self.__qualname__][self.instance]
        self.config = utils.read_config(self.__module__ + "." + constants.CONFIG_TYPE)[self.__qualname__]
        return self.config
        #except Exception as err:
        #    utils.log("{} => get_config ({}): {}".format(self.name, type(err).__name__, err), "e")  # DEBUG

    def init_uart(self):
        """Initializes the uart bus."""
        if "Uart" in self.config:
            if "Bus" in self.config["Uart"]:
                self.uart_bus = self.config["Uart"]["Bus"]
            else:
                self.uart_bus = int(constants.UARTS[dict(map(reversed, constants.DEVICES.items()))[self.name] % len(constants.UARTS)])
                self.uart_slot = int(dict(map(reversed, constants.DEVICES.items()))[self.name] // len(constants.UARTS))
            self.activation_delay = self.uart_slot * constants.SLOT_DELAY
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

    def deinit_uart(self):
        """Deinitializes the uart bus."""
        self.uart.deinit()

    def flush_uart(self, chars=None):
        """Flushes the whole uart read buffer or the specified number of chars.

        Parameters:
            ``chars`` :obj:`int` (optional) The number of chars to be flushed.
        """
        if chars:
            self.uart.read(chars)
        else:
            self.uart.read()

    def init_gpio(self):
        """Creates the device pin object."""
        if {value:key for key, value in constants.DEVICES.items()}[self.name] in constants.CTRL_PINS.keys():
            try:
                self.gpio = pyb.Pin(constants.CTRL_PINS[{value:key for key, value in constants.DEVICES.items()}[self.name]], pyb.Pin.OUT, pyb.Pin.PULL_DOWN)
            except Exception as err:
                utils.log("{} => init_gpio ({}): {}".format(self.name, type(err).__name__, err), "e")  # DEBUG

    def init_led(self):
        """Creates the device led object."""
        try:
            self.led = pyb.LED(constants.LEDS["RUN"])
            self.led.off()
        except Exception as err:
            utils.log("{} => init_led ({}): {}".format(self.name, type(err).__name__, err), "e")  # DEBUG

    def led_on(self):
        """Power on the device led."""
        self.led.on()

    def led_off(self):
        """Power off the device led."""
        self.led.off()

    def on(self):
        """Turns on device."""
        if hasattr(self, "gpio"):
            if self.gpio.value() == 0:
                self.gpio.on()  # set pin to off
        utils.log("{} => {}".format(self.name,self.status(1)))
        return

    def off(self):
        """Turns off device."""
        if hasattr(self, "gpio"):
            if self.gpio.value() == 1:
                self.gpio.off()  # set pin to off
        utils.log("{} => {}".format(self.name,self.status(0)))
        return

    def toggle(self):
        """Toggles the device status between on and off."""
        if hasattr(self, "gpio"):
            if self.gpio.value():
                self.gpio.off()
                self.status(0)
            else:
                self.gpio.on()
                self.status(1)
        return

    def status(self, status=None):
        """Returns or sets the current device status."""
        if not status is None and any(key == status for key, value in constants.DEVICE_STATUS.items()):
            utils.status_table[self.name] = status
        return constants.DEVICE_STATUS[utils.status_table[self.name]]

    def disable(self):
        """Temporary disables unreacheable devices."""
        try:
            tmp = {v:k for k, v in constants.DEVICES.items()}[self.name]
            del(constants.DEVICES[tmp])
            constants.DEVICES[-tmp]=self.name
            del(utils.status_table[self.name])
            utils.log("{} => disabled until next reboot".format(self.name), "m")  # DEBUG
        except Exception as err:
            utils.log("{} => disable ({}): {}".format(self.name, type(err).__name__, err), "e")  # DEBUG
