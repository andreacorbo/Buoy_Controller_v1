SW_NAME = "BUOY_CONTROLLER"
SW_VERSION = "v1"
RESET_CAUSE = ("SOFT_RESET","PWRON_RESET","HARD_RESET","WDT_RESET","DEEPSLEEP_RESET")
CONFIG_DIR = "configs/"
CONFIG_TYPE = ".json"
LOG_DIR = "/sd/log"
LOG_FILE = "syslog"
ESC_CHAR = "#"
PASSWD = "ogsp4lme"
LOGIN_ATTEMPTS = 3
SESSION_TIMEOUT = 120   # sec.
DEVS = (None,None,None,None,None,"dev_gps.GPS_1","dev_modem.MODEM_1")  # Ordered as bob ports
UARTS = (2,4,None,6,1,2,3)    # Ordered as bob ports.
CTRL_PINS = ("X12","Y6","Y4","Y3","X11","Y7","Y5")    # Ordered as bob ports.
WD_TIMEOUT = 30000  # 1000ms < watchdog timer timeout < 32000ms
IRQS = [["Y10", "IRQ_FALLING", "PULL_UP"], ["A9", "IRQ_RISING", "PULL_UP"]]
IRQ_TIMEOUT = 60  # millis. Waits at least 60 secs to allow usb_vcp gets ready and prevent sleep mode.
DATA_DIR = "/sd/data"
BKP_FILE_PFX = "$"
TMP_FILE_PFX = "."
SENT_FILE_PFX = "_"
DATA_SEPARATOR = ","
DEVICE_STATUS = [None]*len(DEVS)
STATUS = ("off","on","run_until_expire","run_until_complete")