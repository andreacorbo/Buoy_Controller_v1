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
import uos
import uselect
import sys
from board import BOARD
from scheduler import SCHEDULER
from menu import MENU
from tools.session import SESSION
import tools.utils as utils
import constants
import gc
import _thread

for i in reversed(range(5)):  # DEBUG Delays main loop to stop before sleep.
    print('{:> 2d}" TO STARTUP'.format(i), end='\r')
    utime.sleep(1)
print('\r')

utils.log_file('RESET CAUSE: {}'.format(machine.reset_cause()), constants.LOG_LEVEL)

board = BOARD()  # Creates a board object.

session = SESSION(board=board, timeout=constants.SESSION_TIMEOUT)  # Starts the remote session.

wdt = machine.WDT(timeout=constants.WD_TIMEOUT)  # Starts the watchdog.

scheduler = SCHEDULER(board)  # Creates the scheduler object.

menu = MENU(board, scheduler)  # Creates the menu object.

t0 = utime.time()  # Gets timestamp at startup.

rx = ''


while True:
    wdt.feed()  # Resets the watchdog timer.
    if board.escaped:
        if not session.loggedin:
            pyb.repl_uart(board.uart)
            _thread.start_new_thread(session.login, (constants.LOGIN_ATTEMPTS,))
            utime.sleep_ms(100)
        else:
            board.prompted = True
        board.escaped = False
    elif session.authenticating:  # Prevents sleeping while user is authenticating.
        if session.loggedin:
            board.prompted = True
            session.authenticating = False
        elif session.loggedout:
            pyb.repl_uart(None)
            session.init()
            session.authenticating = False
    elif board.prompted:  # Prompts user for interactive or file mode.
        if board.set_mode(5):
            if board.interactive:
                _thread.start_new_thread(menu.main, ())
            elif board.connected:
                pyb.repl_uart(None)  # Disables repl to avoid byte collision
                _thread.start_new_thread(board.devices[101].receive, (3,))
        board.prompted = False
    elif board.interactive or board.connected:  # Prevents sleeping while user is interacting.
        if session.loggedout:
            pyb.repl_uart(None)  # Disables repl to avoid byte collision
            board.interactive = False
            session.init()
    else:
        r, w, x = uselect.select(board.input,[],[],0)
        if r:
            try:
                rx += chr(ord(r[0].read(1)))
            except:
                pass
            if constants.ESC_SEQ in rx:
                if r[0] == board.usb:
                    board.prompted = True
                else:
                    board.escaped = True
                board.interrupted = False
                rx = ''
                continue
        utime.sleep_ms(100)  # Adds 100ms delay to allow threads startup.
        t0 = utime.time()  # Gets timestamp before sleep.
        if not scheduler.threads and not board.interrupted and not board.usb.isconnected() :  # Waits for no running threads and no usb connetion before sleep.
            if scheduler.next_event > t0:
                utils.log_file('SLEEP FOR {}'.format(utils.time_display(scheduler.next_event - t0)), constants.LOG_LEVEL)  # DEBUG
                board.go_sleep(scheduler.next_event - t0)  # Puts board in sleep mode.
                t0 = utime.time()  # Gets timestamp at wakeup.
        board.lastfeed = utime.time()
        wdt.feed()  # Resets the watchdog timer.
        scheduler.scheduled(t0)  # Checks for scheduled events in event table.
        gc.collect()  # Frees ram.
