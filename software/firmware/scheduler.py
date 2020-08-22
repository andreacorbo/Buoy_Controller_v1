import utime
import _thread
import tools.utils as utils
import config
import gc

class SCHEDULER:

    def __init__(self):
        self.event_table = {}
        self.next_event = utime.time()
        self.calc_event_table()
        self.get_event_table()

    def scheduled(self, now):
        """Runs all the tasks defined at the current timestamp."""
        self.next_event = min(self.event_table)
        if now >= self.next_event:  # Executes the earlier event.
            self.get_status_table()
            self.manage_event()
            #self.check_executed()
            self.calc_event_table()
            self.get_event_table()
            self.next_event = min(self.event_table)

    def get_status_table(self):
        self.status_table = {}
        for k,v in utils.status_table.items():
            self.status_table[k] = v

    def manage_event(self):
        """Manages all the tasks defined for a device at the given timestamp."""
        # devices => {dev1:[task1,...],...}
        # dev_task => (dev1, [task1,...])
        for dev, tasks in self.event_table[self.next_event].items():
            gc.collect()
            try:
                while dev in utils.processes:
                    continue
                if any(task in ["on","off"] for task in tasks):
                    utils.power(dev, tasks[0])
                else:
                    utils.status(dev,2)
                    _thread.start_new_thread(utils.execute, (dev,tasks))
            except Exception as err:
                utils.log("{} {} {}".format(dev,tasks,err), "e")  # DEBUG

    def check_executed(self):
        """Checks if all tasks defined for a given event have been started before
        calculates the next event.
        """
        i = 0
        while i < len(self.event_table[self.next_event]):
            i = 0
            for dev in self.event_table[self.next_event]:
                if utils.status_table[dev] != self.status_table[dev]:
                    i += 1

    def calc_activation_interval(self, device):
        """Calculates the minimum activation interval for the specified device."""
        tmp = [config.SCHEDULE]
        if device in config.TASK_SCHEDULE:
            for task in config.TASK_SCHEDULE[device]:
                tmp.append(config.TASK_SCHEDULE[device][task])
        return min(tmp)

    def calc_event_table(self):
        """Calculates the subsequent events for all the connected devices."""
        # event_table => {event1:{dev1:[task1,...],...},...}
        self.event_table = {}
        now = self.next_event
        for dev, status in utils.status_table.items():
            obj = utils.create_device(dev)
            virt = now - obj.activation_delay
            sampling_interval = obj.timeout
            activation_interval = self.calc_activation_interval(dev)
            next_activation = virt - virt  % activation_interval + activation_interval + obj.activation_delay
            if status == 0:  # device is off
                evt =  next_activation - sampling_interval - obj.warmup_interval
                if evt < now:
                    evt += activation_interval
                self.add_event(evt, dev, "on")
            elif status == 1:  # device is on / warming up
                if obj.sample_rate > 0:
                    if not dev in config.TASK_SCHEDULE:
                        config.TASK_SCHEDULE[dev] = {}
                    if not "log" in config.TASK_SCHEDULE[dev]:
                        config.TASK_SCHEDULE[dev]["log"] = config.SCHEDULE
                if dev in config.TASK_SCHEDULE:
                    for task in config.TASK_SCHEDULE[dev]:
                        activation_interval = config.TASK_SCHEDULE[dev][task]
                        next_activation = virt - virt % activation_interval + activation_interval + obj.activation_delay
                        evt = next_activation - sampling_interval
                        if evt < now:
                            evt += activation_interval
                        self.add_event(evt, dev, task)
            elif status == 2:  # device is ready / acquiring data
                if obj.warmup_interval < 0:
                    obj.status(1)
                else:
                    evt =  next_activation
                    if evt < now:
                        evt += activation_interval
                    self.add_event(evt, dev, "off")
            del obj

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
