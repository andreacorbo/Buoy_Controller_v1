import time

HOSTNAME = "MAMBO2"
LOG_LEVEL = ["e"]       # e, w, m.
LOG_TO_FILE = True      # False screen output, True log to file.
TIMEOUT = 10        # sec.
DEVS = ("dev_young.Y32500_1","dev_aml.METRECX_1","dev_aml.UVXCHANGE_1","dev_nortek.AQUADOPP_1",None)  # Ordered as bob ports.
SCHEDULE = 600  # sec.
TASK_SCHEDULE = {
    "dev_gps.GPS_1":{"last_fix":300, "sync_rtc":600},
    "dev_modem.MODEM_1":{"data_transfer":1800},
    "dev_aml.UVXCHANGE_1":{"off":600}
    }
ACTIVATION_DELAY = 60  # because meteo and gps share the same uart
#DATA_FILE = "\"{:04d}{:02d}{:02d}\".format(time.localtime()[0], time.localtime()[1], time.localtime()[2])"
DATA_FILE = "{:04d}{:02d}{:02d}".format(time.localtime()[0], time.localtime()[1], time.localtime()[2])
BUF_DAYS = 5
DISPLACEMENT_THRESHOLD = 0.05399568  # Nautical miles: (100meters)
DISPLACEMENT_SMS = "\"{}-{}-{} {}:{}:{} UTC ***WARNING*** {} current position: {}°{}'{} {}°{}'{} is {:.3f}nm away from previous position. Next msg in 5min.\".format(int(utils.gps_fix[9][-2:])+2000,utils.gps_fix[9][2:4],utils.gps_fix[9][0:2], utils.gps_fix[1][0:2], utils.gps_fix[1][2:4], utils.gps_fix[1][4:6], config.NAME, utils.gps_fix[3][0:2], utils.gps_fix[3][2:], utils.gps_fix[4], utils.gps_fix[5][0:3], utils.gps_fix[5][3:], utils.gps_fix[6], utils.gps_displacement)"
DEBUG = False
VERBOSE = False
