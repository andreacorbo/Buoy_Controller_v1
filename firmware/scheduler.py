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

import utime
import tools.utils as utils
import constants
import _thread

class SCHEDULER(object):

    def __init__(self, board):
        self.board = board
        self.devices = board.devices
        self.event_table = {}  # Initializes a event table (dictionary) {event:[device id,...],...}
        self.next_event = 0
        self._init_event_table()
        self._calc_thread_timeout()
        self.lock = _thread.allocate_lock()  # Defines a lock to manage the thread list access
        self.threads = {}  # Dict of active threads {id:timestamp}

    def _calc_thread_timeout(self):
        """Calculates the max thread timeout."""
        timeout = []
        for device in self.devices:
            try:
                timeout.append(self.devices[device].config['Samples'] // self.devices[device].config['Sampling_Rate'])
            except:
                pass
        self.thread_timeout = max(timeout)

    def _del_dead_threads(self):
        """Cleans up dead threads."""
        for thread in self.threads:
            if utime.time() - self.threads[thread] > self.thread_timeout:
                del self.threads[thread]

    def _encapsulate(self, method):
        """Manages threads list at thread starting/ending.

        Params:
            method(func)
        """
        while self.lock.locked():
            continue
        self.lock.acquire()
        self.threads[_thread.get_ident()] = utime.time()
        self.lock.release()
        method()
        while self.lock.locked():
            continue
        self.lock.acquire()
        del self.threads[_thread.get_ident()]
        self.lock.release()

    def _execute(self, device):
        """Executes the device main method.

        If device Async flag is true, launches it as thread.
        Param:
            device(obj):
        Returns:
            False if unable to execute process or True
        """
        self._del_dead_threads()
        if device.config['Async']:
            _thread.start_new_thread(self._encapsulate, (device.main,))
        else:
            device.main()
        return True

    def _init_event_table(self):
        """Initializes the event table."""
        for device in self.devices:
            if self.devices[device].config['Activation_Rate'] > 0:
                self._add_event(self.devices[device])

    def _next_event(self):
        """Gets earlier event from event table."""
        self.next_event = min(self.event_table)

    def _add_event(self, device):
        """Adds schedule to event table.

        Params:
            device(object)
        """
        event = self._calc_event(device)
        try:
            if event in self.event_table:
                #self.event_table[event].append(device.config['Id'])
                self.event_table[event].append(device.__qualname__)
            else:
                #self.event_table[event] = [device.config['Id']]
                self.event_table[event] = [device.__qualname__]
        except:
            utils.log_file("{} => unable to add event to scheduler".format(self.devices[device].__qualname__), constants.LOG_LEVEL)

    def _remove_event(self, timestamp):
        """Removes schedule from event table.

        Params:
            timestamp(int)
        """
        try:
            self.event_table.pop(timestamp)
        except:
            utils.log_file("{} => unable to remove event from scheduler".format(self.devices[device].__qualname__), constants.LOG_LEVEL)

    def scheduled(self, timestamp):
        """Executes any task defined at occurred timestamp.

        Params:
            timestamp(int)
        """
        self._next_event()
        if timestamp > self.next_event:  # execute missed event
            timestamp = self.next_event
        if timestamp in self.event_table:
            for device in self.event_table[timestamp]:
                self._manage_event(self.devices[device])
                self._add_event(self.devices[device])
            self._remove_event(timestamp)
            self._next_event()

    def _calc_event(self, device):
        """Calculates the next event for a device based on the device mode, current status and activation rate.

        Params:
            device(obj)
        Returns:
            event(int)
        """
        activation_rate = int(device.config['Activation_Rate'])
        delay = int(device.config['Activation_Delay'])
        warmup_time = int(device.config['Warmup_Time'])
        samples = int(device.config['Samples'])
        sampling_rate = int(device.config['Sampling_Rate'])
        status = device.config['Status']
        try:
            sampling_time = samples // sampling_rate
        except:
            sampling_time = 0
        now = utime.time() - delay
        next_activation = now - now % activation_rate + activation_rate
        """if now % activation_rate > activation_rate - sampling_time:
          next_activation += activation_rate"""
        if status in [0,3]:  # device is off / standing by
            event = next_activation - sampling_time - warmup_time
        elif status == 1:  # device is warming up
            event = next_activation - sampling_time
        elif status == 2:  # device is active
            event = next_activation
        else:  # Device_Status is not recognized
            utils.log_file('{} => unexpected device status: {}'.format(device.__qualname__, status))
            utils.log_file('{} => unable to calculate event time, use default'.format(device.__qualname__))
            event = next_activation
        return event + delay

    def _manage_event(self, device):
        """Manages the device status after a event event.

        |--OFF--|--WARMING UP--|--ACTIVE--|--STANDING BY--|->

        Params:
            device(obj)
        """
        ready = False  # True if device is ready to work
        if device.config['Status'] in [0, 3]:  # Device is off / standing by
            if not device.gpio:
                ready = True
                device.config['Status'] = 2   # Sets device active
            else:
                device.on()  # Sets device warming up
        elif device.config['Status'] == 1:  # Device is warming up
            if device.config['Samples'] > 0:
                ready = True
                device.config['Status'] = 2  # Sets device active
            elif device.off():
                device.config['Status'] = 3  # Sets device standing by
        elif device.config['Status'] == 2:  # Device is active
            if not device.gpio:
                device.config['Status'] = 0
            elif device.config['Samples'] != 0 and device.config['Warmup_Time'] + device.config['Samples'] // device.config['Sampling_Rate'] == device.config['Activation_Rate']:
                device.config['Status'] = 1  # Sets device warming up
            elif device.off():
                device.config['Status'] = 3  # Sets device standing by
        else:
            utils.log_file('{} => unexpected device status: {}'.format(device.__qualname__,str(device.config['Status'])), constants.LOG_LEVEL)
        utils.log_file('{} => {}'.format(device.__qualname__, constants.DEVICE_STATUS[device.config['Status']]), constants.LOG_LEVEL)
        if ready:
            self._execute(device)
