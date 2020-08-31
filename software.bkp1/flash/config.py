NAME = "MAMBO2"
SW_NAME = "BUOY_CONTROLLER"
SW_VERSION = "v1"
RESET_CAUSE = {0:"SOFT_RESET",1:"PWRON_RESET",2:"HARD_RESET",3:"WDT_RESET",4:"DEEPSLEEP_RESET"}
CONFIG_DIR = "configs/"
CONFIG_TYPE = "json"
LOG_DIR = "/sd/log"
LOG_FILE = "syslog"
LOG_LEVEL = ["e"]  # e, w, m
LOG_TO_FILE = True  # False screen output, True log to file
VERBOSE = 0  # 0 nothing, 1 shows device activity
DEVICE_STATUS = {0:"off", 1:"on", 2:"ready"}
DEVICES = {
    0:"dev_gps.GPS_1",
    -3:"dev_aux.AUX_1",  # configured to enable uart 1 as monitor
    4:"dev_young.Y32500_1",  # virtually assigned to slot 2 to avoid conflict with gps
    5:"dev_aml.METRECX_1",  # virtually assigned to slot 2 to avoid conflict with gps
    6:"dev_nortek.AQUADOPP_1",  # virtually assigned to slot 2 to stay in sync with the other instruments
    100:"dev_modem.MODEM_1",
    101:"dev_aml.UVXCHANGE_1",
    999:"pyboard.SYSMON_1"
    }
UARTS = {0:2, 1:4, 2:6, 3:1}  # uart number to uart channel mapping
                              # uart number = device number % number of uart channels
CTRL_PINS = {                 # ctrl_pin to device position mapping this parameter will be removed in v2
    0:"Y7",
    3:"X11",
    4:"X12",
    5:"Y6",
    6:"Y3",
    100:"Y5",
    101:"Y4"
    }
LEDS = {"IO":1, "PWR":2, "RUN":3, "SLEEP":4}  # red, green, yellow, blue
TIMEOUT = 1                                                                      # sec.
WD_TIMEOUT = 30000  # 1000ms < watchdog timer timeout < 32000ms
IRQ_TIMEOUT = 60  # millis. Waits at least 60 secs to allow usb_vcp gets ready and prevent sleep mode.
ESC_CHAR = "#"
STORAGE = ""
PASSWD = "ogsp4lme"
LOGIN_ATTEMPTS = 3
SESSION_TIMEOUT = 120  # sec.
DATA_DIR = "/sd/data"
DATA_FILE = "\"{:04d}{:02d}{:02d}\".format(utime.localtime()[0], utime.localtime()[1], utime.localtime()[2])"
DATA_SEPARATOR = ","
SCHEDULE = 300  # sec.
TASK_SCHEDULE = {
    "dev_gps.GPS_1":{"last_fix":300, "sync_rtc":600},
    "dev_modem.MODEM_1":{"data_transfer":1800},
    "dev_aml.UVXCHANGE_1":{"disable":600}
    }
SLOT_DELAY = 80  # because meteo and gps share the same uart
                 # meteo must remain OFF until gps finishes its tasks to
                 # avoid byte collision.
                 # This parameter can be drastically reduced to few seconds when
                 # uarts will be multiplexed.
BKP_FILE_PFX = "$"
TMP_FILE_PFX = "."
SENT_FILE_PFX = "_"
BUF_DAYS = 3
DISPLACEMENT_THRESHOLD = 0.05399568  # Nautical miles: (100meters)
DISPLACEMENT_SMS = "\"{}-{}-{} {}:{}:{} UTC ***WARNING*** {} current position: {}°{}'{} {}°{}'{} is {:.3f}nm away from previous position. Next msg in 5min.\".format(int(utils.gps_fix[9][-2:])+2000,utils.gps_fix[9][2:4],utils.gps_fix[9][0:2], utils.gps_fix[1][0:2], utils.gps_fix[1][2:4], utils.gps_fix[1][4:6], config.NAME, utils.gps_fix[3][0:2], utils.gps_fix[3][2:], utils.gps_fix[4], utils.gps_fix[5][0:3], utils.gps_fix[5][3:], utils.gps_fix[6], utils.gps_displacement)"
DEBUG = False
