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

import pyb
import utime
import tools.utils as utils
import constants

class DEVICE(object):

    def __init__(self):
        self._get_config()
        self._set_uart()
        self._set_gpio()
        self._set_led()

    def _get_config(self):
        """Gets the device configuration."""
        self.config = utils.read_config(self.config_file)[self.__qualname__]
        utils.log_file('{} => configuration loaded'.format(self.__qualname__), constants.LOG_LEVEL)  # DEBUG
        try:
          utils.log_file('{} => activation rate: {}, warmup time: {}, activation delay: {}'.format(self.__qualname__, utils.time_display(self.config['Activation_Rate']), utils.time_display(self.config['Warmup_Time']), utils.time_display(self.config['Activation_Delay'])), constants.LOG_LEVEL)
        except KeyError:
          pass
        return self.config

    def _set_uart(self):
        """Creates the device uart object."""
        try:
            self.uart = pyb.UART(int(self.config['Uart']['Bus']), int(self.config['Uart']['Baudrate']))
            return True
        except (KeyError, ValueError):
            return False
        utils.log_file("{} => unable to open uart {}".format(self.__qualname__, self.config['Uart']['Bus']), constants.LOG_LEVEL)
        return False

    def _init_uart(self):
        """Initializes the uart bus."""
        try:
            self.uart.init(int(self.config['Uart']['Baudrate']),
                bits=int(self.config['Uart']['Bits']),
                parity=eval(self.config['Uart']['Parity']),
                stop=int(self.config['Uart']['Stop']),
                timeout=int(self.config['Uart']['Timeout']),
                flow=int(self.config['Uart']['Flow_Control']),
                timeout_char=int(self.config['Uart']['Timeout_Char']),
                read_buf_len=int(self.config['Uart']['Read_Buf_Len']))
        except:
            utils.log_file("{} => unable to init uart".format(self.__qualname__), constants.LOG_LEVEL)
            return False
        return True

    def _deinit_uart(self):
        """Deinitializes the uart bus."""
        self.uart.deinit()

    def _flush_uart(self):
        """Flushes the uart read buffer."""
        self.uart.read()

    def _set_gpio(self):
        """Creates the device pin object."""
        try:
            self.gpio = pyb.Pin(self.config['Ctrl_Pin'], pyb.Pin.OUT)
            self.gpio.off()  # set pin to off
            return True
        except ValueError:
            self.gpio = None  # Needed for scheduling virtual devices
            return True
        except KeyError:
            utils.log_file("{} => gpio not defined".format(self.__qualname__), constants.LOG_LEVEL)
            return False
        utils.log_file("{} => unable to set gpio {}".format(self.__qualname__, self.config['Ctrl_Pin']), constants.LOG_LEVEL)
        return False

    def _set_led(self):
        """Creates the device led object."""
        try:
            self.led = pyb.LED(int(self.config['Led']))
            return True
        except (KeyError, ValueError):
            return False
        utils.log_file("{} => unable to led {}".format(self.__qualname__, self.config['Led']), constants.LOG_LEVEL)
        return False

    def _led_on(self):
        """Power on the device led."""
        if self.led:
            self.led.on()

    def _led_off(self):
        """Power off the device led."""
        if self.led:
            self.led.off()

    def init_power(self):
        """Initializes power status at startup."""
        try:
            if self.config['Status'] == 1:
                utime.sleep_ms(100)
                self.on()
        except:
            utils.log_file('{} => unable to get device status'.format(self.__qualname__), constants.LOG_LEVEL)  # DEBUG
            return False
        return True

    def off(self):
        """Turns off device."""
        try:
            self.gpio.off()  # set pin to off
            self.config['Status'] = 0
            utils.log_file('{} => OFF'.format(self.__qualname__), constants.LOG_LEVEL)  # DEBUG
        except:
            utils.log_file('{} => unable to power off device'.format(self.__qualname__), constants.LOG_LEVEL)  # DEBUG
            return False
        return True

    def on(self):
        """Turns on device."""
        try:
            self.gpio.on()  # set pin to off
            self.config['Status'] = 1
            utils.log_file('{} => ON'.format(self.__qualname__), constants.LOG_LEVEL)  # DEBUG
        except:
            utils.log_file('{} => unable to power on device'.format(self.__qualname__), constants.LOG_LEVEL)  # DEBUG
            return False
        return True

    def toggle(self):
        if self.gpio.value():
            self.gpio.off()
        else:
            self.gpio.on()

    def status(self):
        if self.gpio.value():
            return 'on'
        else:
            return 'off'
