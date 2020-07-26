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

#_thread.stack_size(16 * 1024)  # Icreases thread stack size to avoid RuntimeError: maximum recursion depth exceeded.

pyb.repl_uart(pyb.UART(1,9600))  # DEBUG Forwards repl to uart 1 to monitoring even if sleep.

utils.log("{}".format(constants.RESET_CAUSE[machine.reset_cause()]), "e")  # DEBUG Prints out the reset cause.

print(utils.welcome_msg())

board = PYBOARD()  # Creates a board object.

session = SESSION(board=board, timeout=constants.SESSION_TIMEOUT)  # Starts up the remote session.

scheduler = SCHEDULER()  # Creates the scheduler object.

esc_buff = []  # Initializes the escape character counter.

gc.collect()  # Frees ram.

for i in reversed(range(10)):  # DEBUG Delays main loop to stop before sleep.
    print("{:> 2d}\" to system startup...".format(i), end="\r")
    utime.sleep(1)

_wdt = machine.WDT(timeout=constants.WD_TIMEOUT)  # Starts up the watchdog timer.

"""_poll = uselect.poll()  # Creates a poll object to listen to.
for input in board.input:
    _poll.register(input, uselect.POLLIN)"""

t0 = utime.time()  # Gets timestamp at startup.

while True:
    _wdt.feed()  # Resets the watchdog timer.
    # Board has been woken up.
    if board.interrupted:
        # Backs to scheduled mode after n-seconds.
        if not utils.timed:
            utils.tim.init(mode=machine.Timer.ONE_SHOT, period=constants.IRQ_TIMEOUT, callback=board.timeout_interrupt)
            utils.timed = True
        # Prints out welcome msg if usb is connected, otherwise polls uart to catch escape sequence.
        if board.interrupted == 9:
            utime.sleep(2)
            board.prompted = True
            board.interrupted = False
        """else:
            poll = _poll.ipoll(0, 0)
            try:
                for stream in poll:
                    if stream[0].read(1).decode("utf-8") == constants.ESC_CHAR:
                        esc_cnt += 1
                        if  esc_cnt  == 3:
                            if stream[0] == board.uart:
                                board.escaped = True
                                board.interrupted = False
                            esc_cnt = 0
                            continue
            except:
                # Skips non unicode chars.
                pass"""
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
        if board.set_mode(10):
            if board.interactive:
                menu = MENU(board, scheduler)  # Creates the menu object.
                _thread.start_new_thread(menu.main, ())
            elif board.connected:
                pyb.repl_uart(None)  # Disables repl to avoid byte collision
                _thread.start_new_thread(utils.execute, ("dev_modem.MODEM_1", ["_recv", 60],))
        board.prompted = False
    # Prevents sleeping while user is interacting.
    elif board.interactive or board.connected:
        if session.loggedout:
            pyb.repl_uart(None)  # Disables repl to avoid byte collision
            board.interactive = False
            session.init()
    #elif not utils.processes and not board.interactive and not board.prompted: # Waits for no running threads and no usb connection before sleep.
    #    t0 = utime.time()
    #    if utils.files_to_send():  # Checks for data files to send.
    #        if utils.time_to_send(scheduler.event_table, t0):  # TODO: calculate time based on bytes to send / baudrate.
    #            _thread.start_new_thread(utils.execute, ("dev_modem.MODEM_1", ["data_transfer"],))
    else:
        """if board.usb.isconnected():
            if board.usb.any():
                esc_buff.append(board.usb.read(1))
                if esc_buff[-3:].count(b'#') == 3:
                    esc_buff = []
                    board.prompted = True"""
        utime.sleep_ms(100)  # Adds 100ms delay to allow threads startup.
        t0 = utime.time()  # Gets timestamp before sleep.
        if not utils.processesand and not board.usb.isconnected(): # Waits for no running threads and no usb connection before sleep.
            if utils.files_to_send():  # Checks for data files to send.
                if utils.time_to_send(scheduler.event_table, t0):  # TODO: calculate time based on bytes to send / baudrate.
                    _thread.start_new_thread(utils.execute, ("dev_modem.MODEM_1", ["data_transfer"],))
        if scheduler.next_event > t0 and not utils.processes and not board.interactive and not board.prompted and not board.usb.isconnected():
            board.go_sleep(scheduler.next_event - t0)  # Puts board in sleep mode.
            t0 = utime.time()  # Gets timestamp at wakeup.
        board.lastfeed = utime.time()
        if not constants.DEBUG:
            _wdt.feed()  # Resets the watchdog timer.
        scheduler.scheduled(t0)  # Checks out for scheduled events in event table.
gc.collect()  # Frees ram.
#utils.mem_mon()  # DEBUG
"""if not constants.DEBUG:
    _wdt.feed()  # Resets the watchdog timer.
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
    if board.set_mode(10):
        if board.interactive:
            menu = MENU(board, scheduler)  # Creates the menu object.
            _thread.start_new_thread(menu.main, ())
        elif board.connected:
            pyb.repl_uart(None)  # Disables repl to avoid byte collision
            _thread.start_new_thread(utils.execute, ("dev_modem.MODEM_1", ["_recv", 60],))
    board.prompted = False
elif board.interactive or board.connected:  # Prevents sleeping while user is interacting.
    if session.loggedout:
        pyb.repl_uart(None)  # Disables repl to avoid byte collision
        board.interactive = False
        session.init()
else:
    poll = _poll.ipoll(0, 0)
    try:
        for stream in poll:
            if stream[0].read(1).decode("utf-8") == constants.ESC_CHAR:
                esc_cnt += 1
                if  esc_cnt  == 3:
                    if stream[0] == board.usb:
                        board.prompted = True
                    else:
                        board.escaped = True
                    board.interrupteded = False
                    esc_cnt = 0
                    continue
    except:
        pass

    if utils.gps_displacement > constants.DISPLACEMENT_THRESHOLD:
        _poll.unregister(board.uart)
        _thread.start_new_thread(utils.execute, ("dev_modem.MODEM_1", [("sms",eval(constants.DISPLACEMENT_SMS))],))
        utils.gps_displacement = 0
    if not utils.processes and not board.interactive and not board.interrupteded: # Waits for no running threads and no usb connection before sleep.
        if utils.files_to_send():  # Checks for data files to send.
            if utils.time_to_send(scheduler.event_table, t0):  # TODO: calculate time based on bytes to send / baudrate.
                _poll.unregister(board.uart)
                _thread.start_new_thread(utils.execute, ("dev_modem.MODEM_1", ["data_transfer"],))"""
