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
    """Creates a scheduler object."""

    def __init__(self):
        utils.log_file("Initializing the event table...", constants.LOG_LEVEL)
        self.calc_event_table()

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
            self.calc_event_table()
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
                utils.status_table[device] = 2  # Sets the device status as READY.
                utils.log_file("{} => {}".format(device, constants.DEVICE_STATUS[utils.status_table[device]]), constants.LOG_LEVEL)
                _thread.stack_size(8 * 1024)  # Icreases thread stack size to avoid RuntimeError: maximum recursion depth exceeded
                _thread.start_new_thread(utils.execute, (device, event[device],))

    def calc_activation_interval(self, device):
        """Calculates the minimum activation interval for the specified device.

        Parameters:
            ``device`` :obj:`str` The device FQN `module.device_#instancenumber`
        """
        tmp = [constants.DATA_ACQUISITION_INTERVAL]
        if device in constants.TASK_SCHEDULER:
            for event in constants.TASK_SCHEDULER[device]:
                tmp.append(constants.TASK_SCHEDULER[device][event])
        return min(tmp)

    def calc_activation_delay(self, device):
        """Calculates the activation delay for the specified serial device.

        Multiplexed uarts form `n-`virtual time slots.
        The activation of a serial device is delayed based on the slot the
        device belong to.
        Tasks for devices connected on the same slot are executed asyncronously
        while slots are activated sequentially with a delay defined by the
        SLOT_DELAY parameter.

        Parameters:
            ``device`` :obj:`str` The device FQN `module.device_#instancenumber`
        """
        if hasattr(device, "uart"):
            slot = self.inv_devices[device.name] // len(constants.UARTS)
            return slot * constants.SLOT_DELAY
        return 0

    def calc_event_table(self):
        """Calculates the subsequent events for all the connected devices.

        ``event_table`` :obj:`dict` {timestamp1:{device1:[task1, task2,...],...},...}
        """
        self.event_table = {}
        start = utime.time()
        for device in utils.status_table:
            status = utils.status_table[device]
            # Creates a reversed mapping DEVICES dict.
            self.inv_devices = dict(map(reversed, constants.DEVICES.items()))
            obj = utils.create_device(device)
            activation_delay = self.calc_activation_delay(obj)
            # Substracts the activation_delay from the actual timestamp
            # before calculates the next activation otherwise it misses a cycle.
            now = start - activation_delay
            warmup_duration = obj.config["Warmup_Duration"]
            samples = obj.config["Samples"]
            sample_rate = obj.config["Sample_Rate"]
            # Calculates the sampling_duration and rounds up the value. 
            sampling_duration = 0
            if sample_rate > 0:
                sampling_duration = samples // sample_rate + (samples % sample_rate > 0)
            activation_interval = self.calc_activation_interval(device)
            next_activation = now - now  % activation_interval + activation_interval + activation_delay
            if status == 0:  # device is off
                timestamp =  next_activation - sampling_duration - warmup_duration
                task = "on"
                self.add_event(timestamp, device, task)
            elif status == 1:  # device is on / warming up
                if samples > 0:
                    if not device in constants.TASK_SCHEDULER:
                        activation_interval = constants.DATA_ACQUISITION_INTERVAL
                        next_activation = now - now % activation_interval + activation_interval + activation_delay
                        timestamp = next_activation - sampling_duration
                        task = "log"
                        self.add_event(timestamp, device, task)
                    else:
                        if not "log" in constants.TASK_SCHEDULER[device]:
                            activation_interval = constants.DATA_ACQUISITION_INTERVAL
                            next_activation = now - now % activation_interval + activation_interval + activation_delay
                            timestamp = next_activation - sampling_duration
                            task = "log"
                            self.add_event(timestamp, device, task)
                        for event in constants.TASK_SCHEDULER[device]:
                            activation_interval = int(constants.TASK_SCHEDULER[device][event])
                            next_activation = now - now % activation_interval + activation_interval + activation_delay
                            timestamp = next_activation - sampling_duration
                            task = event
                            self.add_event(timestamp, device, task)
            elif status == 2:  # device is ready / acquiring data
                timestamp =  next_activation
                timestamp += 1 // sample_rate + (1 % sample_rate > 0)  # Adds a delay to capturing complete samples strings.
                if activation_interval - sampling_duration - warmup_duration > 0:
                    task = "off"
                else:
                    task = "on"
                self.add_event(timestamp, device, task)
        self.print_event_table()

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
        tmp1 = ["\r\n############################################################"]
        for event in sorted(self.event_table):
            tmp2 = []
            tmp2.append("# " + utils.timestamp(event))
            for device in self.event_table[event]:
                for task in self.event_table[event][device]:
                    tmp2.append(device)
                    tmp2.append("[" + task + "]")
                tmp1.append(" ".join(tmp2))
        tmp1.append("############################################################\r\n")
        print("\r\n".join(tmp1))
