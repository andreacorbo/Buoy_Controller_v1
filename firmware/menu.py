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
import _thread
import ubinascii
import uselect

class MENU(object):

    def __init__(self, board, scheduler):
        """Initializes menu object.

        Params:
            board(obj)
        """
        self.board = board
        self.scheduler = scheduler
        self.device = None
        self.exit = False

    def _board_menu(self):
        """Writes board menu."""
        print('\r\n' +
        'BOARD\r\n' +
        '[1] DEVICES\r\n' +
        '[2] DATA FILES\r\n' +
        '[3] NEXT EVENTS\r\n' +
        '[4] LAST LOG\r\n' +
        '[BACKSPACE] BACK TO SCHEDULED MODE')

    def _devices_menu(self):
        """Writes devices list."""
        self.device_list = {}
        i=1
        print('\r\n'+
        'DEVICES')
        for device in self.board.devices:
            if self.board.devices[device].config['Device']:
                print('[{}] {}'.format(i, self.board.devices[device].name.upper()))
                self.device_list[str(i)] = self.board.devices[device]
                i += 1
        print('[BACKSPACE] BACK')

    def _device_menu(self, device):
        """Writes device menu.

        Params:
            device(obj)
        """
        print('\r\n' +
        '{}\r\n'.format(device.name.upper()) +
        '[1] ON/OFF ({})\r\n'.format(device.status())+
        '[2] TRANSPARENT MODE\r\n' +
        '[3] SAMPLING\r\n' +
        '[4] CONFIGURATION\r\n' +
        '[BACKSPACE] BACK')

    def _pass_through(self, device):
        """Forwards device uart to board uart.
        Params:
            device(obj)
        """
        device._init_uart()
        tx = ''
        while True:
            if not self.board.interactive:
                device._deinit_uart()
                return False
            r, w, x = uselect.select([self.board.usb, self.board.uart, device.uart], [], [], 0)
            for _ in r:
                if _ == self.board.usb or _ == self.board.uart:
                    byte = ord(_.read(1))
                    if byte == 8:  # [BACKSPACE] Backs to previous menu.
                        device._deinit_uart()
                        return True
                    elif byte == 13:  # [CR] Forwards cmds to device.
                        tx += chr(byte)
                        device.uart.write(tx)
                        tx = ''
                    else:
                        tx += chr(byte)
                        print(chr(byte), end='')
                elif _ == device.uart:
                     print('{}'.format(chr(_.readchar())), end='')
            """r, w, x = uselect.select(self.board.input, [], [], 0)
            if r:
                byte = ord(r[0].read(1))
                if byte == 8:  # [BACKSPACE] Backs to previous menu.
                    device._deinit_uart()
                    return True
                elif byte == 13:  # [CR] Forwards cmds to device.
                    tx += chr(byte)
                    device.uart.write(tx)
                    tx = ''
                else:
                    tx += chr(byte)
                    print(chr(byte), end='')
            if device.uart.any():
                print(device.uart.read())
                #print('{}'.format(chr(device.uart.readchar())), end='')"""

    def _get_data_files(self):
        """Lists data directory."""
        import uos
        print('\r\n\r\nDATA FILES ' +
        '[{}]'.format(self.board.config['Data_File_Path']))
        data = uos.listdir(self.board.config['Data_File_Path'])
        data.sort(reverse=True)
        for file in data:
            print(file)

    def _get_event_table(self):
        """Shows scheduled events."""
        print('\r\n\r\nNEXT EVENTS (current time: {})'.format(utils.time_string(utime.time())))
        for event in sorted(self.scheduler.event_table.keys()):
            print('{} => '.format(utils.time_string(event)), end='')
            for device in self.scheduler.event_table[event]:
                print('{} ({}) '.format(self.board.devices[device].name.upper(), constants.DEVICE_STATUS[self.board.devices[device].config['Status']]), end='')
            print('\r')

    def _get_config(self, device):
        """Shows device configuration."""
        print('\r\n\r\nCONFIGURATION')

        with open(constants.CONFIG_PATH + '/' + self.device.name + constants.CONFIG_TYPE, 'r') as file:
            print(file.read())

    def main(self):
        key_buff = [27]  # Reads last char received
        board = False  # Board menu flag
        devices = False  # Device list flag
        device = False  # Device menu flag
        while True:
            if not self.board.interactive:  # if back received or timeout occurred backs to scheduled mode
                self.board._enable_interrupts()
                return
            r, w, x = uselect.select(self.board.input, [], [], 0)
            if r:
                try:
                    byte = ord(r[0].read(1))  # Reads from main UART
                    key_buff.append(byte)  # Appends char to the command buffer, needed for multiple char commands
                except:
                    pass
            else:  # Checks for command completion
                if key_buff:  # prints out menu on command received only
                    if not board:
                        if not devices:
                            if not device:
                                if 27 in key_buff:
                                    board = True
                                    self._board_menu()
                            else:
                                if 49 in key_buff:
                                    self.device.toggle()
                                    self._device_menu(self.device)
                                elif 50 in key_buff:
                                    if self._pass_through(self.device):
                                        self._device_menu(self.device)
                                elif 51 in key_buff:
                                    self.board.operational = True
                                    self.device.main()
                                    self.board.operational = False
                                elif 52 in key_buff:
                                    self._get_config(self.device)
                                elif 8 in key_buff:
                                    device = False
                                    devices = True
                                    self._devices_menu()
                                elif 27 in key_buff:
                                    self._device_menu(self.device)
                        else:
                            if chr(key_buff[0]) in self.device_list:
                                devices = False
                                device = True
                                self.device = self.device_list[chr(key_buff[0])]
                                self._device_menu(self.device)
                            elif 8 in key_buff:
                                devices = False
                                board = True
                                self._board_menu()
                            elif 27 in key_buff:
                                self._devices_menu()
                    else:
                        if 27 in key_buff:
                            board = True
                            self._board_menu()
                        elif 8 in key_buff:
                            print('')
                            self.board.interactive = False
                            #return  DEBUG
                        elif 49 in key_buff:
                            board  = False
                            devices = True
                            self._devices_menu()
                        elif 50 in key_buff:
                            self._get_data_files()
                        elif 51 in key_buff:
                            self._get_event_table()
                    key_buff = []
