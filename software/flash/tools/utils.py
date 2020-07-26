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

import machine
import pyb
import ujson
import uos
import utime
import constants
import _thread
import uselect

"""Creates a lock to handling data file secure."""
file_lock = _thread.allocate_lock()

"""Creates a lock to manage the processes list access."""
processes_access_lock = _thread.allocate_lock()

"""List of active processes."""
processes = []

"""Contains pairs device:status."""
status_table = {}

unsent_files = []
bytes_to_send = 0

gps_fix = []

gps_displacement = 0

"""Creates a virtual timer."""
tim = machine.Timer(-1)  # Defines a generic timer.

timed = False  # Timer initialization flag.

"""Creates a poll object to capture cmds on uarts."""
_poll = uselect.poll()

def welcome_msg():
    return(
    "{:#^80}\n\r".format("")+
    "#{: ^78}#\n\r".format("WELCOME TO "+constants.NAME+" "+constants.SW_NAME+" "+constants.SW_VERSION)+
    "#{: ^78}#\n\r".format("")+
    "# {: <20}{: <57}#\n\r".format(" current time:", time_string(utime.time())+" UTC")+
    "# {: <20}{: <57}#\n\r".format(" machine:", uos.uname()[4])+
    "# {: <20}{: <57}#\n\r".format(" mpy release:", uos.uname()[2])+
    "# {: <20}{: <57}#\n\r".format(" mpy version:", uos.uname()[3])+
    "{:#^80}".format("")
    )

def read_config(file, path=constants.CONFIG_DIR):
    """Parses a json configuration file.

    Params:
        file(str)
        path(str): default CONFIG_DIR
    """
    try:
        with open(path + "/" + file) as file_:
            return ujson.load(file_)
    except:
        log("Unable to read file {}".format(file), "e")
        return None

def unix_epoch(epoch):
    """Converts embedded epoch since 2000-01-01 00:00:00
    to unix epoch since 1970-01-01 00:00:00
    """
    return 946684800 + epoch

def datestamp(epoch):
    """Returns a formatted date YYMMDD

    Params:
        epoch(embedded_epoch)
    """
    return "{:02d}{:02d}{:02d}".format(utime.localtime(epoch)[1], utime.localtime(epoch)[2], int(str(utime.localtime(epoch)[0])[-2:]))

def timestamp(epoch):
    """Returns a formatted time hhmmss

    Params:
        epoch(embedded_epoch)
    """

    return "{0:02d}{1:02d}{2:02d}".format(utime.localtime(epoch)[3], utime.localtime(epoch)[4], utime.localtime(epoch)[5])

def time_string(timestamp):
    """Formats a time string as YYYY-MM-DD hh:mm:ss

    Params:
        timestamp(int)
    Returns:
        (str): a properly formatted string
    """
    return "{0}-{1:02d}-{2:02d} {3:02d}:{4:02d}:{5:02d}".format(utime.localtime(timestamp)[0], utime.localtime(timestamp)[1], utime.localtime(timestamp)[2], utime.localtime(timestamp)[3], utime.localtime(timestamp)[4], utime.localtime(timestamp)[5])

def time_display(timestamp):
    """Formats a timestamp.

    Params:
        timestamp(int)
    Returns:
        string
    """
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

def log(data_string, msg_type="m", new_line=True):
    """Creates a log and prints a messagge on screen.

    Params:
        data_string(str): message
        msg_type(str): m (message), w (warning), e (error)
        new_line(bool): if False overwrites messages
    """
    log_string = "{: <23}{}".format(time_string(utime.time()), data_string)
    end_char = ""
    if new_line:
        end_char = "\n"
    print(log_string, end=end_char)
    if constants.LOG_TO_FILE:
        if msg_type in constants.LOG_LEVEL:
            try:
                with open(constants.LOG_DIR + "/" + constants.LOG_FILE_NAME, "a") as file_:  # TODO: start new file, zip old file, remove oldest
                    file_.write(log_string + end_char)
            except Exception as err:
                print(err)

def msg(msg=None):
    """Prints out a simple message."""
    if msg is None:
        print("")
    elif msg == "-":
        print("{:#^80}\n".format(""))
    else:
        print("\n{:#^80}".format(msg))

def _make_data_dir(dir):
    """Creates a dir structure."""
    dir_list = dir.split("/")  # split path into a list
    dir = "/"  # start from root
    for i in range(len(dir_list)-1):  # check for directories existence
        if i == 0:  # add a / to dir path
            sep = ""
        else:
            sep = "/"
        if dir_list[i+1] not in uos.listdir(dir):  # checks for directory existance
            log("Creating {} directory...".format(dir + sep + dir_list[i+1]), "m")
            try:
                uos.mkdir(dir + sep + dir_list[i+1])  # creates directory
            except:
                log("Unable to create directory {}".format(dir + sep + dir_list[i+1]), "m")
                return False
        dir = dir + sep + dir_list[i+1]  # changes dir
    return True

def _get_data_dir():
    """Gets the dir to write data to based on media availability."""
    import errno
    for media in constants.MEDIA:
        made = False
        while True:
            try:
                if constants.DATA_DIR in uos.listdir(media):
                    return media + "/" + constants.DATA_DIR
                elif not made:
                    _make_data_dir(media + "/" + constants.DATA_DIR)
                    made = True
                    continue
                else:
                    break
            except OSError as e:
                err = errno.errorcode[e.args[0]]
                if err == "ENODEV":  # media is unavailable.
                    break
    return False

def clean_dir(file):
    """Removes unwanted files.

    Params:
        file(str)
    """
    uos.remove(file)

def too_old(file):
    """Rename unsent files older than buffer days.

    Params:
        file(str)
    Returns:
        True or False
    """
    filename = file.split("/")[-1]
    pathname = file.replace("/" + file.split("/")[-1], "")
    if utime.mktime(utime.localtime()) - utime.mktime([int(filename[0:4]),int(filename[4:6]),int(filename[6:8]),0,0,0,0,0]) > constants.BUF_DAYS * 86400:
        uos.rename(file, pathname + "/" + constants.SENT_FILE_PFX + filename)
        if pathname + "/" + constants.TMP_FILE_PFX + filename in uos.listdir(pathname):
            uos.remove(pathname + "/" + constants.TMP_FILE_PFX + filename)
        return True
    return False

def files_to_send():
    """Checks for files to send."""
    global unsent_files, bytes_to_send
    unsent_files = []
    bytes_to_send = 0
    for media in constants.MEDIA:
        try:
            for file in uos.listdir(media + "/" + constants.DATA_DIR):
                if file[0] not in (constants.TMP_FILE_PFX, constants.SENT_FILE_PFX):  # check for unsent files
                    try:
                        int(file)
                    except:
                        clean_dir(media + "/" + constants.DATA_DIR + "/" + file)  # Deletes all except data files.
                        continue
                    if not too_old(media + "/" + constants.DATA_DIR + "/" + file):
                        # Checks if new data has been added to the file since the last transmission.
                        pointer = 0
                        try:
                            with open(media + "/" + constants.DATA_DIR + "/" + constants.TMP_FILE_PFX + file, "r") as tmp:
                                pointer = int(tmp.read())
                        except:
                            pass  # Tmp file does not exist.
                        if uos.stat(media + "/" + constants.DATA_DIR + "/" + file)[6] > pointer:
                            unsent_files.append(media + "/" + constants.DATA_DIR + "/" + file)
                            bytes_to_send += uos.stat(media + "/" + constants.DATA_DIR + "/" + file)[6] - pointer
        except:
            pass  # Data dir does not exist.
    if unsent_files:
        return True
    return False

def log_data(data):
    """Appends device samples to data log file.

    Params:
        data(str):
    """
    while file_lock.locked():
        continue
    file_lock.acquire()
    try:
        file = _get_data_dir() + "/" + eval(constants.DATA_FILE_NAME)
        with open(file, "a") as data_file:  # append row to existing file
            log("Writing out to file {} => {}".format(file, data), "m")
            data_file.write(data + "\r\n")
    except:
        log("Unable to write out to file {}".format(eval(constants.DATA_FILE_NAME)), "m")
    file_lock.release()

def verbose(msg, enable=True):
    """Shows extensive messages.

    Params:
        msg(str):
        enable(bool):
    """
    if enable:
        print(msg)

def mem_mon():
    import gc
    free = gc.mem_free()
    alloc = gc.mem_alloc()
    tot = free + alloc
    print("free {:2.0f}%, alloc {:2.0f}%".format(100 * free / tot, 100 - 100 * free / tot), end="\r")

def create_device(*args, **kwargs):
    ls = []
    for kwarg in kwargs:
        ls.append(kwarg + "=" + str(kwargs[kwarg]))
    ls = ",".join(ls)
    if ls:
        ls = "," + ls
    exec("import " + args[0].split(".")[0], globals())  # Imports the module.
    exec(args[0] + "=" + args[0].split(".")[0] + "." + args[0].split(".")[1].split("_")[0] + "(\"" + args[0].split(".")[1].split("_")[1] + "\"" + ls + ")", globals())  # Creates the object.
    return eval(args[0])

def delete_device(device):
    exec("del " + device, globals())  # Deletes the object.

def execute(device, tasks):
    """Manages processes list at thread starting/ending.

    Params:
        device(str)
        tasks(list)
    """
    global processes_access_lock, processes
    timeout = 10
    if processes_access_lock.acquire(1, timeout):
        processes.append(_thread.get_ident())
        processes_access_lock.release()
        #create_device(device, tasks=tasks)
        exec("import " + device.split(".")[0], globals())  # Imports the module.
        exec(device + "=" + device.split(".")[0] + "." + device.split(".")[1].split("_")[0] + "(\"" + device.split(".")[1].split("_")[1] + "\", tasks="+str(tasks)+")", globals())  # Creates the object.
        if processes_access_lock.acquire(1, timeout):
            processes.remove(_thread.get_ident())
            processes_access_lock.release()
    return

def time_to_send(event_table, now):
    global bytes_to_send
    tmp=[]
    for y in sorted(event_table):
        for k in event_table[y]:
            if "log" in event_table[y][k]:
                tmp.append(y)
    if tmp and min(tmp) - now > constants.SCHEDULE // 2: #bytes_to_send // 9600 * 1.3:  # TODO
        return True
    return False
