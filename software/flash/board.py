# board.py
import pyb
import time
import _thread
import gc
from tools.utils import msg, log, read_cfg, timestring, time_display
from configs import dfl, cfg

irqs = []
lock = _thread.allocate_lock()
processes = []
interrupted = None
next = 0
rtc = pyb.RTC()

def init_led():
    #R G Y B
    for _ in range(1,5):
        pyb.LED(_).off()

def pwr_led():
    init_led()
    pyb.LED(2).on()

def sleep_led():
    init_led()
    pyb.LED(4).on()

def ext_callback(line):
    global interrupted
    interrupted = line

def init_interrupts():
    for pin in dfl.IRQS:
        irqs.append(pyb.ExtInt(pyb.Pin(pin[0], pyb.Pin.IN), eval("pyb.ExtInt." + pin[1]), eval("pyb.Pin." + pin[2]), ext_callback))

def run_async(dev, tasks=[]):
    while lock.locked():
        continue
    lock.acquire()
    processes.append(dev)
    lock.release()
    for task in tasks:
        eval(dev + "." + task+"()")
    while lock.locked():
        continue
    lock.acquire()
    processes.remove(dev)
    lock.release()

def devices():
    for id, val in enumerate(dfl.DEVS):
        if not val:
            if cfg.DEVS[id]:
                yield cfg.DEVS[id], id
        else:
            yield val, id

def init_devices():
    msg(" init devices ".upper())
    for dev, id in devices():
        exec("from " + dev.split(".")[0] + " import " + dev.split(".")[1].split("_")[0])
        exec(dev.split(".")[1].lower() + " = " + dev.split(".")[1].split("_")[0] + "(" + dev.split(".")[1].split("_")[1] + ")")
    for dev, id in devices():
        exec("{}.start_up()".format(dev.split(".")[1].lower()))
    msg("-")

def next_event(timestamp):
    global next
    def print_events(timestamp):
        msg(" next events ".upper())
        for _ in sorted(gen_events(timestamp)):
            print("{} {} -> {:<25}{}".format(_[0],timestring(_[0]), _[1], _[2]))
        msg("-")
    try:
        next = min(gen_events(timestamp))[0]
        print_events(timestamp)
    except:
        pass

def schedule(timestamp):

    def get_id(dev):
        for _ in devices():
            if _[0] == dev:
                return _[1]

    def run_tasks(dev, tl):
        print(dev,tl)
        status0 = dfl.DEVICE_STATUS[get_id(dev)]
        if any(_ in ["on","off"] for _ in tl):
            exec("{}.{}()".format(dev.split(".")[1].lower(),tl[0]))
        else:
            gc.collect()  # IMPORTANT.
            _thread.start_new_thread(run_async, (dev.split(".")[1].lower(),tl))
        t0 = time.time()
        while status0 == dfl.DEVICE_STATUS[get_id(dev)]:
            if(time.time() - t0 > 1):
                break
            continue

    dev = None
    tl = []
    for _ in sorted(gen_events(timestamp)):
        if _[0] == timestamp:
            if not dev:
                dev = _[1]
                tl = [_[2]]

            else:
                if _[1] != dev:
                    #run_tasks(dev,tl)
                    dev = _[1]
                    tl = [_[2]]
                else:
                    tl.append(_[2])
    if dev:
        print(dev,tl)
        run_tasks(dev,tl)
    while time.time() - timestamp == 0:
        continue
    next_event(time.time())

def gen_activation_interval(device, sampling_period):
    if sampling_period > 0:
        if not device in cfg.TASK_SCHEDULE or not "log" in cfg.TASK_SCHEDULE[device]:
            yield cfg.SCHEDULE, "log"
    if device in cfg.TASK_SCHEDULE:
        for task in cfg.TASK_SCHEDULE[device]:
            yield cfg.TASK_SCHEDULE[device][task], task

def gen_events(timestamp):
    for device, id in devices():
        dev_cfg = read_cfg(device.split(".")[0])[device.split(".")[1].split("_")[0]]
        sampling_period = 0
        if "Samples" in dev_cfg:
            sampling_period = dev_cfg["Samples"] // dev_cfg["Sample_Rate"] + (dev_cfg["Samples"] % dev_cfg["Sample_Rate"] > 0) + cfg.TIMEOUT
        activation_interval = min(gen_activation_interval(device, sampling_period))[0]
        warmup_period = dev_cfg["Warmup_Interval"]
        if warmup_period < 0:
            warmup_period = activation_interval - sampling_period
        activation_delay = 0
        if id == max([index for index, element in enumerate(dfl.UARTS) if element == dfl.UARTS[id]]):
            activation_delay = cfg.ACTIVATION_DELAY
        virt = timestamp - activation_delay
        status = dfl.DEVICE_STATUS[id]
        if  status == 0:  # device is off
            event =  virt - virt % activation_interval + activation_interval - sampling_period - warmup_period + activation_delay
            task = "on"
            yield event, device, task
        elif status == 1:  # device is on / warming up
            for _ in gen_activation_interval(device, sampling_period):
                activation_interval = _[0]
                warmup_period = dev_cfg["Warmup_Interval"]
                if warmup_period < 0:
                    warmup_period = activation_interval - sampling_period
                event = virt - virt % activation_interval - sampling_period + activation_delay
                if virt % activation_interval > 0:
                    event +=  activation_interval
                task = _[1]
                yield event, device, task
        elif status == 2:
            event = virt - virt % activation_interval + activation_delay
            if virt % activation_interval > 0:
                event +=  activation_interval
            if activation_interval == warmup_period + sampling_period:
                task = "on"
            else:
                task = "off"
            yield event, device, task

def sleep(interval, lastfeed):

    def enable_interrupts():
        for irq in irqs:
            irq.enable()

    def disable_interrupts():
        for irq in irqs:
            irq.disable()

    log("sleeping.... wake up in {}".format(time_display(interval)))  # DEBUG
    sleep_led()
    enable_interrupts()
    remain = dfl.WD_TIMEOUT - (time.time() - lastfeed) * 1000
    interval = interval * 1000
    if interval - remain > -3000:
        interval = remain - 3000
    rtc.wakeup(interval)  # Set next rtc wakeup (ms).
    time.sleep_ms(interval)  # DEBUG
    #pyb.stop()
    disable_interrupts()
    pwr_led()

def init():
    init_led()
    pwr_led()
    init_interrupts()
    init_devices()
    #next_event(time.time())
