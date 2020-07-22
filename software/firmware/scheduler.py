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
import gc

class SCHEDULER(object):
    """Creates a scheduler object."""

    def __init__(self):
        self.next_event = 0
        self.calc_event_table(utime.time())
        self.print_event_table()

    def scheduled(self, timestamp):
        """Runs all tasks defined at the current timestamp.

        Parameters:
            ``timestamp`` :obj:`int` unix epoch timestamp
        """
        self.get_next_event()
        if timestamp > self.next_event:  # Executes missed event.
            timestamp = self.next_event
        if timestamp in self.event_table:
            self.manage_event(self.event_table[timestamp])
            self.calc_event_table(utime.time())
            self.print_event_table()
            self.get_next_event()

    def get_next_event(self):
        """Gets the timestamp of the next event from the event table."""
        self.next_event = min(self.event_table)

    def manage_event(self, event):
        """Manages all the tasks defined for a device at the current timestamp.

        Parameters:
            ``event`` :obj:`dict` {device1:[task1,...],...}
        """
        for device in event:
            if "on" in event[device]:
                utils.create_device(device, tasks=["on"])
            elif "off" in event[device]:
                utils.create_device(device, tasks=["off"])
            else:
                utils.create_device(device).status(2)  # Sets the device status as READY.
                
                _thread.start_new_thread(utils.execute, (device, event[device],))
            gc.collect()

    def calc_activation_interval(self, device):
        """Calculates the minimum activation interval for the specified device.

        Parameters:
            ``device`` :obj:`str` The device FQN `module.device_#instancenumber`
        """
        tmp = [constants.SCHEDULE]
        if device in constants.TASK_SCHEDULE:
            for event in constants.TASK_SCHEDULE[device]:
                tmp.append(constants.TASK_SCHEDULE[device][event])
        return min(tmp)

    def calc_event_table(self, timestamp):
        """Calculates the subsequent events for all the connected devices.

        Parameters:
            ``now`` :obj:`int` The timestamp to calculate the event table from.

        ``event_table`` :obj:`dict` {timestamp1:{device1:[task1, task2,...],...},...}
        """
        self.event_table = {}
        for device in utils.status_table:
            status = utils.status_table[device]
            obj = utils.create_device(device)
            virt = timestamp - obj.activation_delay
            sampling_interval = 0
            sampling_buffer = 0
            if obj.sample_rate:
                sampling_interval = obj.samples // obj.sample_rate + (obj.samples % obj.sample_rate > 0)
                sampling_buffer = (1 // obj.sample_rate + (1 % obj.sample_rate > 0)) * 2
            activation_interval = self.calc_activation_interval(device)
            next_activation = virt - virt  % activation_interval + activation_interval + obj.activation_delay
            if status == 0:  # device is off
                schedule =  next_activation - sampling_interval - obj.warmup_interval
                task = "on"
                self.add_event(schedule, device, task)
            elif status == 1:  # device is on / warming up
                if obj.sample_rate:
                    if not device in constants.TASK_SCHEDULE:
                        constants.TASK_SCHEDULE[device] = {}
                    if not "log" in constants.TASK_SCHEDULE[device]:
                        constants.TASK_SCHEDULE[device]["log"] = constants.SCHEDULE
                if device in constants.TASK_SCHEDULE:
                    for event in constants.TASK_SCHEDULE[device]:
                        activation_interval = constants.TASK_SCHEDULE[device][event]
                        next_activation = virt - virt % activation_interval + activation_interval + obj.activation_delay
                        schedule = next_activation - sampling_interval - sampling_buffer
                        task = event
                        self.add_event(schedule, device, task)
            elif status == 2:  # device is ready / acquiring data
                schedule =  next_activation
                if obj.warmup_interval < 0 or activation_interval - sampling_interval < obj.warmup_interval:
                    task = "on"
                else:
                    task = "off"
                self.add_event(schedule, device, task)

    def add_event(self, timestamp, device, task):
        """Adds an event {timestamp:{device1:[task1, task2,...],...} to the event table.

        Params:
            timestamp(int)
            device(str)
            task(str)
        """
        if timestamp in self.event_table:
            if device in self.event_table[timestamp]:
                self.event_table[timestamp][device].append(task)
            else:
                self.event_table[timestamp][device]=[task]
        else:
            self.event_table[timestamp] = {device:[task]}

    def print_event_table(self):
        """Prints out the event_table."""
        utils.msg(" next events ".upper())
        for event in sorted(self.event_table):
            for device, tasks in self.event_table[event].items():
                for task in tasks:
                    name = task if (type(task) == str) else task[0]
                    print("{} -> {:<25}{}".format(utils.time_string(event), device, name.upper()))
        utils.msg("-")
