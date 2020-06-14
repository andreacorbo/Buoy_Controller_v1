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

CONFIG_DIR = "configs"
CONFIG_TYPE = "json"
LOG_DIR = "log"
LOG_LEVEL = 0  # 0 screen output, 1 log to file
VERBOSE = 1  # 0 nothing, 1 shows device activity
DEVICE_STATUS = {0:"OFF", 1:"ON", 2:"READY"}
DEVICES = {
    0:"dev_gps.GPS_1",
    2:"dev_nortek.AQUADOPP_1",
    3:"dev_aux.AUX_1",  # configured to enable uart 1 as monitor
    4:"dev_young.Y32500_1",  # virtually assigned to slot 2 to avoid conflict with gps
    5:"dev_aml.METRECX_1",  # virtually assigned to slot 2 to avoid conflict with gps
    99:"dev_modem.MODEM_1"
    }
UARTS = {0:2, 1:4, 2:6, 3:1}  # uart number to uart channel mapping
                              # uart number = device number % number of uart channels
LEDS = {"IO":1, "PWR":2, "RUN":3, "SLEEP":4}  # red, green, yellow, blue
TIMEOUT = 60  # sec.
WD_TIMEOUT = 30000  # 1000ms < watchdog timer timeout < 32000ms
ESC_CHAR = "#"
STORAGE = ""
THREAD_TIMEOUT = 60  # sec.
PASSWD = "pippo"
LOGIN_ATTEMPTS = 3
SESSION_TIMEOUT = 604800  # sec.
MEDIA = ["/sd", "/flash"]
DATA_DIR = "data"
DATA_FILE_NAME = "\"{:04d}{:02d}{:02d}\".format(utime.localtime()[0], utime.localtime()[1], utime.localtime()[2])"
DATA_SEPARATOR = ","
SCHEDULE = 900  # sec.
TASK_SCHEDULE = {
    "dev_modem.MODEM_1":{"off":3600, "start_up":3600},
    "dev_gps.GPS_1":{"sync_rtc":3600, "last_fix":300},
    "dev_nortek.AQUADOPP_1":{"log":300},
    "dev_aml.UVXCHANGE_1":{"off":600}
    }
SLOT_DELAY = 60  # because meteo and gps share the same uart
                 # meteo must remain OFF until gps finishes its tasks to
                 # avoid byte collision.
                 # This parameter can be drastically reduced to few seconds when
                 # uarts will be multiplexed.
TMP_FILE_PFX = "$"
SENT_FILE_PFX = "_"
BUF_DAYS = 3
DISPLACEMENT_THRESHOLD = 0.002
