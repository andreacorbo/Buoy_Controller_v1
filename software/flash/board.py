# board.py
import pyb
import config
from tools.utils import msg, log, read_cfg, timestring, time_display
import _thread
import utime
import gc

irqs = []
lock = _thread.allocate_lock()
processes = []
interrupted = None
next = 0

rtc = pyb.RTC()

def init_led():
    for led in config.LEDS:
        led = pyb.LED(config.LEDS[led]).off()

def pwr_led():
    init_led()
    pyb.LED(config.LEDS["PWR"]).on()

def sleep_led():
    init_led()
    pyb.LED(config.LEDS["SLEEP"]).on()

def ext_callback(line):
    global interrupted
    interrupted = line

def init_interrupts():
    for pin in config.IRQS:
        irqs.append(pyb.ExtInt(pyb.Pin(pin[0], pyb.Pin.IN), eval("pyb.ExtInt." + pin[1]), eval("pyb.Pin." + pin[2]), ext_callback))

def run_async(dev, tasks=[]):
    while lock.locked():
        continue
    lock.acquire()
    processes.append(dev)
    lock.release()
    exec("from " + dev.split(".")[0] + " import " + dev.split(".")[1].split("_")[0])
    exec(dev.split(".")[1].lower() + " = " + dev.split(".")[1].split("_")[0] + "(" + dev.split(".")[1].split("_")[1]  + ", " + str(tasks) +  ")")
    exec("del " + dev.split(".")[1].lower())
    while lock.locked():
        continue
    lock.acquire()
    processes.remove(dev)
    lock.release()

def init_devices():
    msg(" init devices ".upper())
    for d,p in config.DEVICES.items():
        if p >= 0:  # Skips device with a negative port number.
            run_async(d, ["start_up"])
    msg("-")

def next_event(timestamp):
    global next
    def print_events(timestamp):
        msg(" next events ".upper())
        for _ in sorted(gen_events(timestamp)):
            print("{} -> {:<25}{}".format(timestring(_[0]), _[1], _[2]))
        msg("-")
    next = min(gen_events(timestamp))[0]
    print_events(timestamp)

def power(dev, status):
    if config.DEVICES[dev] in config.CTRL_PINS:
        pin = pyb.Pin(config.CTRL_PINS[config.DEVICES[dev]], pyb.Pin.OUT)
        if pin.value() != (1 if status == "on" else 0):
            pin.value(1 if status == "on" else 0)
    config.DEVICE_STATUS[dev] = 1 if status == "on" else 0
    log("{} => {}".format(dev, status))

def schedule(timestamp):
    def run_tasks(dev, tl):
        status0 = config.DEVICE_STATUS[dev]
        if any(_ in ["on","off"] for _ in tl):
            power(dev,tl[0])
        else:
            _thread.start_new_thread(run_async, (dev,tl))
        t0 = utime.time()
        while status0 == config.DEVICE_STATUS[dev]:
            if(utime.time() - t0 > 2):
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
                    run_tasks(dev,tl)
                    dev = _[1]
                    tl = [_[2]]
                else:
                    tl.append(_[2])
    if dev:
        run_tasks(dev,tl)
    while utime.time() - timestamp == 0:
        continue
    next_event(utime.time())

def gen_activation_interval(device, sampling_period):
    if sampling_period > 0:
        if not device in config.TASK_SCHEDULE or not "log" in config.TASK_SCHEDULE[device]:
            yield config.SCHEDULE, "log"
    if device in config.TASK_SCHEDULE:
        for task in config.TASK_SCHEDULE[device]:
            yield config.TASK_SCHEDULE[device][task], task

def gen_events(timestamp):
    for device, port in config.DEVICES.items():
        if port >= 0:
            cfg = read_cfg(device.split(".")[0])[device.split(".")[1].split("_")[0]]
            sampling_period = 0
            if "Samples" in cfg:
                sampling_period = cfg["Samples"] // cfg["Sample_Rate"] + (cfg["Samples"] % cfg["Sample_Rate"] > 0) + config.TIMEOUT
            activation_interval = min(gen_activation_interval(device, sampling_period))[0]
            warmup_period = cfg["Warmup_Interval"]
            if warmup_period < 0:
                warmup_period = activation_interval - sampling_period
            uart_slot = 0
            if config.DEVICES[device] in range(config.MUX * len(config.UARTS)):
                uart_slot = int(config.DEVICES[device] // len(config.UARTS))
            activation_delay = uart_slot * config.SLOT_DELAY
            virt = timestamp - activation_delay
            status = config.DEVICE_STATUS[device]
            if  status == 0:  # device is off
                event =  virt - virt % activation_interval + activation_interval - sampling_period - warmup_period + activation_delay
                task = "on"
                yield event, device, task
            elif status == 1:  # device is on / warming up
                for _ in gen_activation_interval(device, sampling_period):
                    activation_interval = _[0]
                    warmup_period = cfg["Warmup_Interval"]
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
    remain = config.WD_TIMEOUT - (utime.time() - lastfeed) * 1000
    interval = interval * 1000
    if interval - remain > -3000:
        interval = remain - 3000
    rtc.wakeup(interval)  # Set next rtc wakeup (ms).
    utime.sleep_ms(interval)  # DEBUG
    #pyb.stop()
    disable_interrupts()
    pwr_led()

def init():
    init_led()
    pwr_led()
    init_interrupts()
    init_devices()
    next_event(utime.time())
