import utime
import _thread
import tools.utils as utils
import constants

class SCHEDULER(object):

    def __init__(self):
        self.event_table = {}
        self.next_event = utime.time()
        self.calc_event_table()
        self.get_event_table()

    def scheduled(self, timestamp):
        """Runs all the tasks defined at the current timestamp."""
        self.next_event = min(self.event_table)
        if timestamp >= self.next_event:  # Executes the earlier event.
            self.manage_event()
            self.check_executed()
            self.calc_event_table()
            self.get_event_table()
            self.next_event = min(self.event_table)

    def manage_event(self):
        """Manages all the tasks defined for a device at the given timestamp."""
        # devices => {dev1:[task1,...],...}
        # dev_task => (dev1, [task1,...])
        for dev_task in self.event_table[self.next_event].items():
            try:
                _thread.start_new_thread(utils.execute, (dev_task,))
            except Exception as err:
                utils.log("{} {}".format(dev_task,err), "e")  # DEBUG

    def calc_activation_interval(self, device):
        """Calculates the minimum activation interval for the specified device."""
        tmp = [constants.SCHEDULE]
        if device in constants.TASK_SCHEDULE:
            for task in constants.TASK_SCHEDULE[device]:
                tmp.append(constants.TASK_SCHEDULE[device][task])
        return min(tmp)

    def check_executed(self):
        """Checks if all tasks defined for a given event have been launched."""
        status_table = {}
        for k,v in utils.status_table.items():
            status_table[k] = v
        i = 0
        while i < len(self.event_table[self.next_event]):
            i = 0
            for dev in self.event_table[self.next_event]:
                if utils.status_table[dev] != status_table[dev]:
                    i += 1

    def calc_event_table(self):
        """Calculates the subsequent events for all the connected devices."""
        # event_table => {event1:{dev1:[task1,...],...},...}
        self.event_table = {}
        now = utime.time()
        for device, status in utils.status_table.items():
            obj = utils.create_device(device)
            virt = now - obj.activation_delay
            sampling_interval = obj.timeout
            activation_interval = self.calc_activation_interval(device)
            next_activation = virt - virt  % activation_interval + activation_interval + obj.activation_delay
            if status == 0:  # device is off
                evt =  next_activation - sampling_interval - obj.warmup_interval
                if evt < now:
                    evt += activation_interval
                task = "on"
                self.add_event(evt, device, task)
            elif status == 1:  # device is on / warming up
                if obj.sample_rate > 0:
                    if not device in constants.TASK_SCHEDULE:
                        constants.TASK_SCHEDULE[device] = {}
                    if not "log" in constants.TASK_SCHEDULE[device]:
                        constants.TASK_SCHEDULE[device]["log"] = constants.SCHEDULE
                if device in constants.TASK_SCHEDULE:
                    for task in constants.TASK_SCHEDULE[device]:
                        activation_interval = constants.TASK_SCHEDULE[device][task]
                        next_activation = virt - virt % activation_interval + activation_interval + obj.activation_delay
                        evt = next_activation - sampling_interval
                        if evt < now:
                            evt += activation_interval
                        self.add_event(evt, device, task)
            elif status == 2:  # device is ready / acquiring data
                if obj.warmup_interval < 0:
                    obj.status(1)
                else:
                    evt =  next_activation
                    if evt < now:
                        evt += activation_interval
                    task = "off"
                    self.add_event(evt, device, task)

    def add_event(self, timestamp, device, task):
        """Adds an event {timestamp:{dev1:[task1,...],...} to the event table."""
        if timestamp in self.event_table:
            if device in self.event_table[timestamp]:
                self.event_table[timestamp][device].append(task)
            else:
                self.event_table[timestamp][device]=[task]
        else:
            self.event_table[timestamp] = {device:[task]}

    def get_event_table(self):
        """Prints out the event_table."""
        utils.msg(" next events ".upper())
        for event in sorted(self.event_table):
            for device, tasks in self.event_table[event].items():
                for task in tasks:
                    name = task if (type(task) == str) else task[0]
                    print("{} -> {:<25}{}".format(utils.timestring(event), device, name.upper()))
        utils.msg("-")
