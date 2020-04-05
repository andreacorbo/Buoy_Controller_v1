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
import ujson
import uos
import utime
import constants
import _thread

"""Creates a lock for data file secure handling."""
file_lock = _thread.allocate_lock()

def read_config(file, path=constants.CONFIG_PATH):
    """Parses a json configuration file.

    Params:
        file(str)
        path(str): default CONFIG_PATH
    """
    try:
        with open(path + '/' + file) as file_:
            return ujson.load(file_)
    except:
        log_file('SYSTEM => unable to read file {}'.format(file), constants.LOG_LEVEL)
        return None

def unix_epoch(epoch):
    """Converts embedded epoch since 2000-01-01 00:00:00
    to unix epoch since 1970-01-01 00:00:00
    """
    return str(946684800 + epoch)

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
        timestring.append(str(days) + 'd')
    if hours > 0:
        timestring.append(str(hours) + 'h')
    if mins > 0:
        timestring.append(str(mins) + '\'')
    if secs >= 0:
        timestring.append(str(secs) + '\"')
    return ' '.join(timestring)

def log_file(data_string, mode=0, new_line=True):
    """Creates a log and prints a messagge on screen.

    Params:
        data_string(str): message
        mode(int): 0 print, 1 save, 2 print & save
        new_line(bool): if False overwrites messages
    """
    log_string = time_string(utime.time()) + '\t' + data_string
    end_char = " "
    if new_line:
        end_char = "\n"
    if constants.LOG_LEVEL == 0:
        print(log_string, end=end_char)
    else:
        with open('Log.txt', 'a') as file_:
            file_.write(log_string + end_char)
        print(log_string, end=end_char)

def _make_data_dir(dir):
    """Creates a dir structure."""
    dir_list = dir.split('/')  # split path into a list
    dir = '/'  # start from root
    for i in range(len(dir_list)-1):  # check for directories existence
        if i == 0:  # add a / to dir path
            sep = ''
        else:
            sep = '/'
        if dir_list[i+1] not in uos.listdir(dir):  # checks for directory existance
            log_file('CREATING {} DIRECTORY...'.format(dir + sep + dir_list[i+1]), constants.LOG_LEVEL)
            try:
                uos.mkdir(dir + sep + dir_list[i+1])  # creates directory
            except:
                log_file('UNABLE TO CREATE DIRECTORY {}'.format(dir + sep + dir_list[i+1]), constants.LOG_LEVEL)
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
                    return media + '/' + constants.DATA_DIR
                elif not made:
                    _make_data_dir(media + '/' + constants.DATA_DIR)
                    made = True
                    continue
                else:
                    break
            except OSError as e:
                err = errno.errorcode[e.args[0]]
                if err == 'ENODEV':  # media is unavailable.
                    break
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
        file = _get_data_dir() + '/' + eval(constants.DATA_FILE_NAME)
        with open(file, 'a') as data_file:  # append row to existing file
            log_file('WRITING TO FILE {} => {}'.format(file, data), constants.LOG_LEVEL)
            data_file.write(data + '\r\n')
    except:
        log_file('UNABLE TO WRITE TO FILE {}'.format(eval(constants.DATA_FILE_NAME)), constants.LOG_LEVEL)
    file_lock.release()

def verbose(msg, enable=True):
    """Shows extensive messages.

    Params:
        msg(str):
        enable(bool):
    """
    if enable:
        print(msg)
