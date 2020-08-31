import pyb
import sys
import _thread
import uselect
import utime
import config

class SESSION:

    def __init__(self, **kwargs):
        self.input = kwargs["board"].input
        self.timeout = kwargs["timeout"]
        self.logging = False
        self.loggedin = False
        self.loggedout = False
        self.authenticating = False
        self.active = False
        self.passwd = config.PASSWD

    def init(self):
        self.loggedin = False
        self.loggedout = False

    def login(self, attempts):
        """Prompts user for authentication.

        Params:
            attempts(int): allowed login attempts
        """
        self.authenticating = True
        self.loggedin = False
        self.loggedout = False
        for i in range(attempts):
            rx = ""
            char = ""
            utime.sleep_ms(250)
            print("ENTER PASSWORD:", end="")
            while True:
                r, w, x = uselect.select(self.input, [], [], 10)
                if r:
                    byte = r[0].read(1)
                    if  byte == b"\r":
                        if rx[len(rx) - len(self.passwd):] == self.passwd:
                            _thread.start_new_thread(self._expire, (self.timeout,))
                            self.loggedin = True
                            print("")
                            return
                        elif i < attempts-1:
                            print("\n\rTRY AGAIN.")
                            break
                        else:
                            print("\n\rAUTH FAILED.")
                            break
                    else:
                        try:
                            rx += chr(ord(byte))  # Discharge wrong chars.
                        except:
                            print("\n\rUNEXPECTED CHAR {}.".format(byte))  # DEBUG
                else:
                    print("\n\rAUTH TIMEOUT.")
                    break
        print("")
        self.loggedout = True
        return

    def _expire(self, timeout):
        """Timeouts session.

        Params:
            timeout(int): seconds
        """
        t0 = utime.time()
        while utime.time() - t0 < timeout:
            pass
        print("SESSION EXPIRED.")
        self.loggedin = False
        self.loggedout = True
        return

    def _check_activity(self, timeout):
        """Checks for user activity.

        Params:
            timeout(int): seconds
        """
        while True:
            r, w, x = uselect.select(self.input, [], [], timeout)
            if not r:
                self.active = False
                return

    def check_activity(self):
        """Starts check_activity method as a thread."""
        self.active = True
        _thread.start_new_thread(self._check_activity, (self.timeout,))
