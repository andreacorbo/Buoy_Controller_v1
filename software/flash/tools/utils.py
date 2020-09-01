import pyb
import machine
import ujson
import uos as os
import utime as time
import config
import _thread

# Creates a lock to manage the processes list access.
process_lock = _thread.allocate_lock()

# List of active processes.
processes = []

# Creates a lock to handling data file secure.
file_lock = _thread.allocate_lock()

# Last gps fix.
gps_fix = []

# Calculated displacement from previous fix.
gps_displacement = 0

"""Creates a virtual timer."""
tim = machine.Timer(-1)  # Defines a generic timer.

timed = False  # Timer initialization flag.
prompted = False  # Prompt initialization flag.

def welcome_msg():
    return(
    "{:#^80}\n\r".format("")+
    "#{: ^78}#\n\r".format("WELCOME TO "+config.NAME+" "+config.SW_NAME+" "+config.SW_VERSION)+
    "#{: ^78}#\n\r".format("")+
    "# {: <20}{: <57}#\n\r".format(" current time:", timestring(time.time())+" UTC")+
    "# {: <20}{: <57}#\n\r".format(" machine:", os.uname()[4])+
    "# {: <20}{: <57}#\n\r".format(" mpy release:", os.uname()[2])+
    "# {: <20}{: <57}#\n\r".format(" mpy version:", os.uname()[3])+
    "{:#^80}".format("")
    )

def read_cfg(file):
    """Parses a json configuration file."""
    try:
        with open(config.CONFIG_DIR + file + config.CONFIG_TYPE) as cfg:
            return ujson.load(cfg)
    except:
        log("Unable to read file {}".format(file), "e")
        return None

def unix_epoch(epoch):
    """Converts embedded epoch 2000-01-01 00:00:00 to unix epoch 1970-01-01 00:00:00."""
    return 946684800 + epoch

def datestamp(epoch):
    """Returns a formatted date mmddyy."""
    return "{:02d}{:02d}{:02d}".format(time.localtime(epoch)[1], time.localtime(epoch)[2], int(str(time.localtime(epoch)[0])[-2:]))

def timestamp(epoch):
    """Returns a formatted time HHMMSS."""

    return "{:02d}{:02d}{:02d}".format(time.localtime(epoch)[3], time.localtime(epoch)[4], time.localtime(epoch)[5])

def timestring(timestamp):
    """Formats a time string as yyyy-mm-dd HH:MM:SS"""
    return "{}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}".format(time.localtime(timestamp)[0], time.localtime(timestamp)[1], time.localtime(timestamp)[2], time.localtime(timestamp)[3], time.localtime(timestamp)[4], time.localtime(timestamp)[5])

def time_display(timestamp):
    """Formats a timestamp."""
    timestring = []
    if timestamp < 0:
        timestamp = 0
    days = timestamp // 86400
    hours = timestamp % 86400 // 3600
    mins = timestamp % 86400 % 3600 // 60
    secs = timestamp % 86400 % 3600 % 60
    if days > 0:
        timestring.append(str(days) + "d")
    if hours > 0:
        timestring.append(str(hours) + "h")
    if mins > 0:
        timestring.append(str(mins) + "'")
    if secs >= 0:
        timestring.append(str(secs) + "\"")
    return " ".join(timestring)

def verbose(msg, enable=True):
    """Shows extensive messages."""
    if enable:
        print(msg)

def msg(msg=None):
    """Prints out a simple message."""
    if msg is None:
        print("")
    elif msg == "-":
        print("{:#^80}\n".format(""))
    else:
        print("\n{:#^80}".format(msg))

def log(msg, msg_type="m", new_line=True):
    """Creates a log and prints out a messagge on screen."""
    log_msg = "{: <23}{}".format(timestring(time.time()), msg)
    end_char = ""
    if new_line:
        end_char = "\n"
    print(log_msg, end=end_char)
    if config.LOG_TO_FILE:
        if msg_type in config.LOG_LEVEL:
            try:
                with open(config.LOG_DIR + "/" + config.LOG_FILE, "a") as log:  # TODO: start new file, zip old file, remove oldest
                    log.write(log_msg + end_char)
            except Exception as err:
                print(err)

def log_data(data):
    """Appends device data to data file."""
    while file_lock.locked():
        continue
    file_lock.acquire()
    try:
        with open(config.DATA_DIR + "/" + eval(config.DATA_FILE), "a") as data_file:  # append row to existing file
            log("{}".format(data))
            data_file.write(data + "\r\n")
    except Exception as err:
        log("log_data ({}): {}".format(type(err).__name__, err), "e")  # DEBUG
    file_lock.release()
    return

def too_old(file):
    """Renames unsent files older than buffer days."""
    filename = file.split("/")[-1]
    path = file.replace("/" + file.split("/")[-1], "")
    if time.mktime(time.localtime()) - time.mktime([int(filename[0:4]),int(filename[4:6]),int(filename[6:8]),0,0,0,0,0]) > config.BUF_DAYS * 86400:
        os.rename(file, path + "/" + config.SENT_FILE_PFX + filename)
        if path + "/" + config.TMP_FILE_PFX + filename in os.listdir(path):
            os.remove(path + "/" + config.TMP_FILE_PFX + filename)
        return True
    return False

def files_to_send():
    """Checks for files to send."""
    #unsent_files = []
    for file in os.listdir(config.DATA_DIR):
        if file[0] not in (config.TMP_FILE_PFX, config.SENT_FILE_PFX):  # check for unsent files
            try:
                int(file)
            except:
                os.remove(config.DATA_DIR + "/" + file)  # Deletes all except data files.
                continue
            if not too_old(config.DATA_DIR + "/" + file):
                # Checks if new data has been added to the file since the last transmission.
                pointer = 0
                try:
                    with open(config.DATA_DIR + "/" + config.TMP_FILE_PFX + file, "r") as tmp:
                        pointer = int(tmp.read())
                except:
                    pass  # Tmp file does not exist.
                if os.stat(config.DATA_DIR + "/" + file)[6] > pointer:
                    #unsent_files.append(config.DATA_DIR + "/" + file)  # Makes a list of files to send.
                    yield config.DATA_DIR + "/" + file
    if any(file[0] not in (config.TMP_FILE_PFX, config.SENT_FILE_PFX) for file in os.listdir(config.DATA_DIR)):
            yield "\x00"

def create_device(device, tasks=[]):
    """Creates and return an istance of the passed device."""
    try:
        exec("from " + device.split(".")[0] + " import " + device.split(".")[1].split("_")[0])  # Imports the class.
        exec(device.split(".")[1].lower() + " = " + device.split(".")[1].split("_")[0] + "(" + device.split(".")[1].split("_")[1]  + ", " + str(tasks) +  ")")  # Creates the object.
        return eval(device.split(".")[1].lower())
    except Exception as err:
        log("create_device ({}): {}".format(type(err).__name__, err), "e")  # DEBUG


def execute(device, tasks=[]):
    """Manages processes list at thread starting/ending."""
    # schedule = (device, [task1,(task2, param1,...),...]) dev_module.CLASS_instance
    global process_lock, processes
    while process_lock.locked():
        continue
    process_lock.acquire()
    processes.append(device)
    process_lock.release()
    exec("from " + device.split(".")[0] + " import " + device.split(".")[1].split("_")[0])  # Imports the class.
    exec(device.split(".")[1].lower() + " = " + device.split(".")[1].split("_")[0] + "(" + device.split(".")[1].split("_")[1] + ", " + str(tasks) + ")")  # Creates the object.
    exec("del " + device.split(".")[1].lower())
    while process_lock.locked():
        continue
    process_lock.acquire()
    processes.remove(device)
    process_lock.release()

def power(dev, mode="off"):
    gpio = pyb.Pin(config.CTRL_PINS[config.DEVICES[dev]], pyb.Pin.OUT, pyb.Pin.PULL_DOWN)
    if mode == "on":
        mode = 1
    else:
        mode = 0
    gpio.value(mode)
    log("{} => {}".format(dev, status(dev, mode)))

def status(dev, status=None):
    """Returns or sets the current device status."""
    global status_table
    if not status is None and any(key == status for key in config.STATUS_DICT):
        status_table[dev] = status
    return config.STATUS_DICT[status_table[dev]]
