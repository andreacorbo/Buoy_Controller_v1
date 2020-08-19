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
import utime
import uselect
from pyboard import PYBOARD
from scheduler import SCHEDULER
from menu import MENU
from session import SESSION
import constants
import _thread
import tools.utils as utils
import gc

pyb.repl_uart(pyb.UART(1,9600))  # DEBUG Forwards repl to uart 1 to monitoring even if sleep.

for i in reversed(range(10)):  # DEBUG Delays main loop to stop before sleep.
    print("{:> 2d}\" to system startup...".format(i), end="\r")
    utime.sleep(1)

utils.log("{}".format(constants.RESET_CAUSE[machine.reset_cause()]), "e")  # DEBUG Prints out the reset cause.

print(utils.welcome_msg())

board = PYBOARD()  # Creates a board object.

session = SESSION(board=board, timeout=constants.SESSION_TIMEOUT)  # Starts up the remote session.

scheduler = SCHEDULER()  # Creates the scheduler object.

esc_buff = []  # Initializes the escape character counter.

gc.collect()  # Frees ram.

wdt = machine.WDT(timeout=constants.WD_TIMEOUT)  # Starts up the watchdog timer.

t0 = utime.time()  # Gets timestamp at startup.

while True:
    wdt.feed()  # Resets the watchdog timer.
    # Board has been woken up.
    if board.interrupted:
        # Prints out welcome msg if usb is connected, otherwise polls uart to catch escape sequence.
        if board.interrupted == 9:
            utime.sleep(2)
            board.prompted = True
            board.interrupted = False
        else:
            # Backs to scheduled mode after n-seconds.
            if not utils.timed:
                utils.tim.init(mode=machine.Timer.ONE_SHOT, period=constants.IRQ_TIMEOUT*1000, callback=board.timeout_interrupt)
                utils.timed = True
            try:
                if board.uart.any():
                    esc_buff.append(board.uart.read(1))
                    if esc_buff[-3:].count(b'#') == 3:
                        board.escaped = True
                        board.interrupted = False
                        esc_buff = []
            except:
                # Skips non unicode chars.
                pass
    # Escape sequence has been caught.
    elif board.escaped:
        if not session.loggedin:
            pyb.repl_uart(board.uart)
            _thread.start_new_thread(session.login, (constants.LOGIN_ATTEMPTS,))
            utime.sleep_ms(100)
        else:
            board.prompted = True
        board.escaped = False
    # Authentication in progress.
    elif session.authenticating:  # Prevents sleeping while user is authenticating.
        if session.loggedin:
            board.prompted = True
            session.authenticating = False
        elif session.loggedout:
            pyb.repl_uart(None)
            session.init()
            session.authenticating = False
    # Prompts user for interactive or file mode.
    elif board.prompted:
        if not utils.prompted:
            _thread.start_new_thread(board.set_mode, (constants.IRQ_TIMEOUT,))
            utils.prompted = True
        if board.interactive:
            menu = MENU(board, scheduler)  # Creates the menu object.
            _thread.start_new_thread(menu.main, ())
            board.prompted = False
            utils.prompted = False
        elif board.connected:
            pyb.repl_uart(None)  # Disables repl to avoid byte collision
            _thread.start_new_thread(utils.execute, ("dev_modem.MODEM_1", [("_recv", 10)],))
            board.prompted = False
            utils.prompted = False
    # Prevents sleeping while user is interacting.
    elif board.interactive or board.connected:
        if session.loggedout:
            pyb.repl_uart(None)  # Disables repl to avoid byte collision
            board.interactive = False
            session.init()
    else:
        utime.sleep_ms(100)  # Adds 100ms delay to allow threads startup.
        t0 = utime.time()  # Gets timestamp before sleep.
        if not utils.processes: # Waits for no running threads and no usb connection before sleep.
            if utils.gps_displacement > 0:
                _thread.start_new_thread(utils.execute, ("dev_modem.MODEM_1", [("sms",eval(constants.DISPLACEMENT_SMS))],))
                utils.gps_displacement = 0
            if utils.files_to_send():  # Checks for data files to send.
                if utils.time_to_send(scheduler.event_table, t0):  # TODO: calculate time based on bytes to send / baudrate.
                    _thread.start_new_thread(utils.execute, ("dev_modem.MODEM_1", ["data_transfer"],))
            elif scheduler.next_event > t0 and not board.usb.isconnected():
                board.go_sleep(scheduler.next_event - t0)  # Puts board in sleep mode.
                t0 = utime.time()  # Gets timestamp at wakeup.
    board.lastfeed = utime.time()
    wdt.feed()  # Resets the watchdog timer.
    scheduler.scheduled(t0)  # Checks out for scheduled events in event table.
gc.collect()  # Frees ram.
#utils.mem_mon()  # DEBUG
