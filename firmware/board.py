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
import uos
import utime
import uselect
from device import DEVICE
import _thread
import tools.utils as utils
import constants
import tools.inspect as inspect

class BOARD(object):
    r_led = pyb.LED(1)  # pyb is communicating with slaves or modem
    g_led = pyb.LED(2)  # pyb is on
    y_led = pyb.LED(3)  # pyb is sampling
    b_led = pyb.LED(4)  # pyb is sleeping
    rtc = pyb.RTC()
    devices = {}

    line2uart = {
        1:4,
        3:2,
        7:1,     # attention!!! same as for uart6
        9:5,     # usb
        11:3
        }

    def __init__(self):
        self.config_path  = constants.CONFIG_PATH
        self.config_file = self.__qualname__ + constants.CONFIG_TYPE
        self.lastfeed = utime.time()
        self.usb = None
        self.interrupt = None
        self.interrupted = False
        self.escaped = False
        self.prompted = False
        self.interactive = False
        self.connected = False
        self.operational = False
        self.irqs = []
        self._active_led()
        self._get_config()
        self._init_devices()
        self._init_interrupts()
        self._disable_interrupts()
        self._usb()
        self._uart()
        self._init_uart()
        self.input = [self.usb, self.uart]

    def _init_led(self):
        self.r_led.off()
        self.g_led.off()
        self.b_led.off()
        self.y_led.off()

    def _active_led(self):
        self._init_led()
        self.g_led.on()

    def _sleep_led(self):
        self._init_led()
        self.b_led.on()

    def _get_config(self):
        """Gets board configuration."""
        self.config = utils.read_config(self.config_file)[self.__qualname__]
        if self.config:
            utils.log_file('{} => configuration loaded'.format(self.__qualname__), constants.LOG_LEVEL)  # DEBUG
            """utils.log_file('{} => activation rate: {}, warmup time: {}, working time: {}'.format(self.__qualname__, utils.time_display(self.config['Activation_Rate']), utils.time_display(self.config['Warmup_Time']), utils.time_display(self.config['Samples'])), constants.LOG_LEVEL)"""

    def _usb(self):
        self.usb = pyb.USB_VCP()

    def _uart(self):
        """Creates the uart object."""
        try:
            self.uart = pyb.UART(int(self.config['Uart']['Bus']), int(self.config['Uart']['Baudrate']))
        except:
            utils.log_file("{} => unable to open uart {}".format(self.__qualname__, self.config['Uart']['Bus']), constants.LOG_LEVEL)
            return False
        return True

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
            utils.log_file("{} => unable to initialize uart {}".format(self.__qualname__, self.config['Uart']['Bus']), constants.LOG_LEVEL)
            return False
        return True

    def _deinit_uart(self):
        """Deinitializes the uart bus."""
        try:
            self.uart.deinit()
        except:
            utils.log_file("{} => unable to deinitialize uart {}".format(self.__qualname__, self.config['Uart']['Bus']), constants.LOG_LEVEL)
            return False
        return True

    def set_repl(self):
        if self.line2uart[self.interrupt] == self.config['Uart']['Bus']:
            pyb.repl_uart(self.uart)

    def _ext_callback(self, line):
        """Sets board to interactive mode"""
        self._disable_interrupts()
        self.interrupt = line
        self.interrupted = True

    def _init_interrupts(self):
        """Initializes all external interrupts to wakes up board from sleep mode."""
        for pin in self.config['Irq_Pins']:
            self.irqs.append(pyb.ExtInt(pyb.Pin(pin[0], pyb.Pin.IN), eval('pyb.ExtInt.' + pin[1]), eval('pyb.Pin.' + pin[2]), self._ext_callback))

    def _enable_interrupts(self):
        """Enables interrupts"""
        self.interrupt = None
        self.interrupted = False
        for irq in self.irqs:
            irq.enable()

    def _disable_interrupts(self):
        """Disables interrupts."""
        for irq in self.irqs:
            irq.disable()

    def _import_module(self, name):
        """Imports a module.

        Param:
            name(str):
        """
        try:
            exec('import ' + name, globals())
            return True
        except:
            utils.log_file("{} => unable to import module {}.{}".format(self.__qualname__, name, str.upper(name)), constants.LOG_LEVEL)
            return False

    def _create_object(self, _module, _class):
        """Instantiates an object.

        Param:
            name(str):
        """
        try:
            exec(_class + ' = ' + _module + '.' + _class + '()', globals())  # creates a device object
        except:
            utils.log_file("{} => unable to instantiate object {}".format(self.__qualname__, _class), constants.LOG_LEVEL)
            return False
        return True

    def _init_devices(self):
        """Initializes all the board connected devices."""
        for _file in uos.listdir(constants.CONFIG_PATH):
            name = _file.split('.')[0]
            ext =  _file.split('.')[1]
            if ext == 'json':
                if name[0] != '_':  # DEBUG: excludes _file
                    if self._import_module(name):
                        for obj in inspect.getmembers(eval(name)):
                            if inspect.isclass(eval(name + '.' + obj[0])) and not eval(name + '.' + obj[0] + '.__name__') == self.__qualname__.upper():
                                if hasattr(eval(name + '.' + obj[0]), '__module__'):
                                    if eval(name + '.' + obj[0] + '.__module__') == name:
                                        if self._create_object(eval(name+'.'+obj[0]+'.__module__'), eval(name+'.'+obj[0]+'.__name__')):
                                            try:
                                                exec('self.devices[\'' + obj[0] + '\'] = ' + obj[0], globals(), {'self': self})  # appends device to device list
                                            except:
                                                utils.log_file("{} => unable to initialize device {}".format(self.__qualname__, name), constants.LOG_LEVEL)

        #self.devices[self.__qualname__.upper()] = self  # Appends board to device list.

    def set_mode(self, timeout):
        """ Prints welcome message. """
        print(
        '##################################################\r\n'+
        '#                                                #\r\n'+
        '#        WELCOME TO PYBUOYCONTROLLER V1.1        #\r\n'+
        '#                                                #\r\n'+
        '##################################################\r\n'+
        '[ESC] INTERACTIVE MODE\r\n'+
        '[DEL] FILE TRANSFER MODE')
        t0 = utime.time()
        while True:
            t1 = utime.time() - t0
            if t1 > timeout:
                break
            print("ENTER YOUR CHOICE WITHIN {} SECS".format(timeout - t1), end="\r")
            r, w, x = uselect.select(self.input, [], [], 0)
            if r:
                byte = r[0].read(1)
                if byte == b'\x1b':  # ESC
                    self.interactive = True
                    print("")
                    return True
                elif byte == b'\x1b[3~':  # DEL
                    self.connected = True
                    print("")
                    return True
        print("")
        return False

    def go_sleep(self, interval):
        """Puts board in sleep mode.

        Params:
            now(int): current timestamp
            wakeup(int): wakeup timestamp
        """
        self._sleep_led()
        self._enable_interrupts()
        remain = constants.WD_TIMEOUT - (utime.time() - self.lastfeed) * 1000
        interval = interval * 1000
        if interval - remain > -3000:
            interval = remain - 3000
        self.rtc.wakeup(interval)  # Set next rtc wakeup (ms).
        pyb.stop()
        self._active_led()


class SYSTEM(DEVICE):

    def __init__(self):
        self.config_file = __name__ + constants.CONFIG_TYPE
        DEVICE.__init__(self)

    def _adcall_mask(self, channels):
        """Creates a mask for the adcall method with the adc's channels to acquire.

        Params:
            channels(dictionary)
        Return:
            mask(hex)
        """
        mask = []
        chs = [16,17,18]  # MCU_TEMP, VREF, VBAT
        chs.extend(channels)
        for i in reversed(range(19)):
            if i in chs:
                mask.append('1')
            else:
                mask.append('0')
        return eval(hex(int(''.join(mask), 2)))

    def _ad22103(self, vout, vsupply):
        return (vout * 3.3 / vsupply - 0.25) / 0.028

    def _battery_level(self, vout):
        return vout * self.config['Adc']['Channels']['Battery_Level']['Calibration_Coeff']

    def _current_level(self, vout):
        return vout * self.config['Adc']['Channels']['Current_Level']['Calibration_Coeff']

    def main(self):
        """Gets data from internal sensors."""
        utils.log_file("{} => CHECKING SYSTEM STATUS...".format(self.__qualname__), constants.LOG_LEVEL)
        core_temp = 0
        core_vbat = 0
        core_vref = 0
        vref = 0
        battery_level = 0
        current_level = 0
        ambient_temperature = 0
        data_string = []
        channels = []
        for key in self.config['Adc']['Channels'].keys():
            channels.append(self.config['Adc']['Channels'][key]['Ch'])
        adcall = pyb.ADCAll(int(self.config['Adc']['Bit']), self._adcall_mask(channels))
        for i in range(int(self.config['Samples']) * int(self.config['Sampling_Rate'])):
            core_temp += adcall.read_core_temp()
            core_vbat += adcall.read_core_vbat()
            core_vref += adcall.read_core_vref()
            vref += adcall.read_vref()
            battery_level += adcall.read_channel(self.config['Adc']['Channels']['Battery_Level']['Ch'])
            current_level += adcall.read_channel(self.config['Adc']['Channels']['Current_Level']['Ch'])
            ambient_temperature += adcall.read_channel(self.config['Adc']['Channels']['Ambient_Temperature']['Ch'])
            i += 1
        core_temp = core_temp / i
        core_vbat = core_vbat / i
        core_vref = core_vref / i
        vref = vref / i
        battery_level = battery_level / i * vref / pow(2, int(self.config['Adc']['Bit']))
        current_level = current_level / i * vref / pow(2, int(self.config['Adc']['Bit']))
        ambient_temperature = ambient_temperature / i * vref / pow(2, int(self.config['Adc']['Bit']))
        battery_level = self._battery_level(battery_level)
        current_level = self._current_level(current_level)
        ambient_temperature = self._ad22103(ambient_temperature, vref)
        epoch = utime.time()
        data_string.append(self.config['String_Label'])
        data_string.append(str(utils.unix_epoch(epoch)))  # unix timestamp
        data_string.append(utils.datestamp(epoch))  # YYMMDD
        data_string.append(utils.timestamp(epoch))  # hhmmss
        data_string.append('{:.4f}'.format(battery_level))
        data_string.append('{:.4f}'.format(current_level))
        data_string.append('{:.4f}'.format(ambient_temperature))
        data_string.append('{:.4f}'.format(core_temp))
        data_string.append('{:.4f}'.format(core_vbat))
        data_string.append('{:.4f}'.format(core_vref))
        data_string.append('{:.4f}'.format(vref))
        utils.log_data(','.join(data_string))
