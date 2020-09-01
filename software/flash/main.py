import machine
import pyb
import time
import board
from tools.utils import log, welcome_msg, timestring, read_cfg
import config

pyb.repl_uart(pyb.UART(1,9600))  # DEBUG Permanently forwards repl to uart to monitor execution during sleeping.
log("{}".format(config.RESET_CAUSE[machine.reset_cause()]), "e")  # DEBUG Prints out the reset cause.
print(welcome_msg())
board.init()  # Initializes the board module.
lastfeed = time.time()  # Initializes last wdt feed.
#wdt = machine.WDT(timeout=config.WD_TIMEOUT)  # Starts up the watchdog timer.
while True:
    if not board.processes:  # Checks for active threads.
        now = time.time()
        if board.next > now:  # and not pyb.USB_VCP().isconnected()
            board.sleep(board.next - now, lastfeed)  # Sleeps between events.
    lastfeed = time.time()  # Passes the last feed to sleep to wakeup before it expires.
    #wdt.feed()  # Feeds the wdt.
    if time.time() >= board.next:  # Checks for events to be executed.
        board.schedule(board.next)  # Recalculates the event table.
