import utime
import ubinascii
import config
import tools.utils as utils
from device import DEVICE

class AQUADOPP(DEVICE):

    modes = {
        b"\x00\x00":"Firmware upgrade",
        b"\x01\x00":"Measurement",
        b"\x02\x00":"Command",
        b"\x04\x00":"Data retreival",
        b"\x05\x00":"Confirmation",
        b"\x0a\x0d\x43\x6f\x6e\x66\x69\x72\x6d\x3a":"Confirmation"
        }

    coord_system = {
        0:"ENU",
        1:"XYZ",
        2:"BEAM"
        }

    head_cfg = ("Pressure sensor", "Magnetometer sensor", "Tilt sensor")

    hw_cfg = ("Recorder installed", "Compass installed")

    def __init__(self, instance, tasks=[]):
        DEVICE.__init__(self, instance)
        self.data = []
        ########################################################################
        self.tasks = tasks
        if self.tasks:
            if not any( elem in ["start_up","on","off"] for elem in self.tasks):
                self.main()
            for task in self.tasks:
                method = task
                param_dict={"self":self}
                param_list=[]
                params=""
                if type(task) == tuple:
                    method = task[0]
                    i = 0
                    for param in task[1:]:
                        param_dict["param"+str(i)] = task[1:][i]
                        param_list.append("param"+str(i))
                        params = ",".join(param_list)
                exec("self."+ method +"(" + params + ")", param_dict)
        ########################################################################

    def start_up(self):
        self.on()
        utime.sleep_ms(500)  # Allows instrument to start properly prior to send commands
        if self.break_():
            self.set_clock()
            self.set_usr_cfg()
            self.get_cfg()
            self.start_delayed()

    def get_reply(self, timeout=0):
        """Returns replies from instrument."""
        t0 = utime.time()
        while not self._timeout(t0, timeout):
            if self.uart.any():
                x = self.uart.read()
                return x

    def ack(self, rx):
        """Parses acknowledgement bytes sequence."""
        if rx:
            if rx[-2:] == b"\x06\x06":
                utils.verbose("<= ACK", config.VERBOSE)
                return True
            elif rx[-2:] == b"\x15\x15":
                utils.verbose("<= NAK", config.VERBOSE)
                return False

    def break_(self):
        """Sends break sequence to instrument."""
        utils.verbose("=> @@@@@@K1W%!Q", config.VERBOSE)
        self.uart.write("@@@@@@")
        utime.sleep_ms(100)
        self.uart.write("K1W%!Q")
        t0 = utime.time()
        while not self._timeout(t0, config.TIMEOUT):
            rx = self.get_reply()
            if self.ack(rx):
                if b"\x0a\x0d\x43\x6f\x6e\x66\x69\x72\x6d\x3a" in rx:
                    self.confirm()
                else:
                    utils.verbose(rx, config.VERBOSE)
                    return True
        utils.log("{} => did not respond in {} secs.".format(self.name, config.TIMEOUT), "e")  # DEBUG
        return False

    def confirm(self):
        """Enters command mode."""
        utils.verbose("=> MC", config.VERBOSE)
        self.uart.write("MC")
        rx = self.get_reply()
        if self.ack(rx):
            return True
        return False

    def calc_checksum(self, reply):
        """Computes the data checksum: b58c(hex) + sum of all words in structure."""
        sum=0
        j=0
        for i in range(int.from_bytes(reply[2:4], "little")-1):
            sum += int.from_bytes(reply[j:j+2], "little")
            j = j+2
        return (int.from_bytes(b"\xb5\x8c", "big") + sum) % 65536

    def verify_checksum(self, reply):
        """Verifies the data checksum."""
        checksum = int.from_bytes(reply[-2:], "little")
        calc_checksum = self.calc_checksum(reply)
        if checksum != calc_checksum:
            utils.log("invalid checksum calculated: {} got: {}".format(calc_checksum, checksum), "e")
            return False
        return True

    def get_cfg(self):
        """Retreives the complete configuration data from the instrument."""
        t0 = utime.time()
        while not self._timeout(t0, config.TIMEOUT):
            if self.break_():
                utils.verbose("=> GA", config.VERBOSE)
                self.uart.write("GA")
                rx = self.get_reply()
                if self.ack(rx) and self.verify_checksum(rx[0:48]) and self.verify_checksum(rx[48:272]) and self.verify_checksum(rx[272:784]):
                    try:
                        with open(config.CONFIG_DIR + "/" + self.config["Adcp"]["Instrument_Config"], "wb") as cfg:
                            cfg.write(rx)
                            return True
                    except Exception as err:
                        utils.log("{} => get_cfg ({}): {}".format(self.name, type(err).__name__, err), "e")  # DEBUG
                        break
        utils.log("{} => unable to retreive the instrument configuration".format(self.name), "e")  # DEBUG
        return False

    def parse_cfg(self):
        """Parses the configuration data."""
        try:
            with open(config.CONFIG_DIR + "/" + self.config["Adcp"]["Instrument_Config"], "rb") as cfg:
                bytes = cfg.read()
                self.hw_cfg = self.parse_hw_cfg(bytes[0:48])         # Hardware config (48 bytes)
                self.head_cfg = self.parse_head_cfg(bytes[48:272])   # Head config (224 bytes)
                self.usr_cfg = self.parse_usr_cfg(bytes[272:784])    # Deployment config (512 bytes)
            return True
        except Exception as err:
            utils.log("{} => parse_cfg ({}): {}".format(self.name, type(err).__name__, err), "e")  # DEBUG
            return False

    def parse_hw_cfg(self, reply):
        """Parses the hardware configuration."""
        try:
            return (
                "{:02x}".format(reply[0]),                                         # [0] Sync
                "{:02x}".format(int.from_bytes(reply[1:2], "little")),             # [1] Id
                int.from_bytes(reply[2:4], "little"),                              # [2] Size
                reply[4:18].decode("ascii"),                                       # [3] SerialNo
                self.decode_hw_cfg(int.from_bytes(reply[18:20], "little")),       # [4] Config
                int.from_bytes(reply[20:22], "little"),                            # [5] Frequency
                reply[22:24],                                                      # [6] PICVersion
                int.from_bytes(reply[24:26], "little"),                            # [7] HWRevision
                int.from_bytes(reply[26:28], "little"),                            # [8] RecSize
                self.decode_hw_status(int.from_bytes(reply[28:30], "little")),    # [9] Status
                reply[30:42],                                                      # [10] Spare
                reply[42:46].decode("ascii")                                       # [11] FWVersion
                )
        except Exception as err:
            utils.log("{} => parse_hw_cfg ({}): {}".format(self.name, type(err).__name__, err), "e")  # DEBUG

    def decode_hw_cfg(self, cfg):
        """Decodes hardware config."""
        try:
            return (
                "RECORDER {}".format("NO" if cfg >> 0 & 1  else "YES"),
                "COMPASS {}".format("NO" if cfg >> 1 & 1  else "YES")
                )
        except Exception as err:
            utils.log("{} => decode_hw_cfg ({}): {}".format(self.name, type(err).__name__, err), "e")  # DEBUG

    def decode_hw_status(self, status):
        """Decodes hardware status."""
        try:
            return "VELOCITY RANGE {}".format("HIGH" if status >> 0 & 1  else "NORMAL")
        except Exception as err:
            utils.log("{} => decode_hw_status ({}): {}".format(self.name, type(err).__name__, err), "e")  # DEBUG

    def set_usr_cfg(self):
        """Uploads a deployment config to the instrument and sets up the device
        Activation_Rate and Warmup_Interval parameters according to the current
        deployment config."""
        t0 = utime.time()
        while not self._timeout(t0, config.TIMEOUT):
            if self.break_():
                try:
                    with open(config.CONFIG_DIR + "/" + self.config["Adcp"]["Deployment_Config"], "rb") as pfc:
                        cfg = pfc.read()
                        sampling_interval = int.from_bytes(cfg[38:40], "little")
                        avg_interval = int.from_bytes(cfg[16:18], "little")
                        config.TASK_SCHEDULE[self.name] = {"log":sampling_interval}
                        usr_cfg = cfg[0:48] + self.set_deployment_start(sampling_interval, avg_interval) + cfg[54:510]
                        checksum = self.calc_checksum(usr_cfg)
                        tx = usr_cfg + ubinascii.unhexlify(hex(checksum)[-2:] + hex(checksum)[2:4])
                        self.uart.write(b"\x43\x43")
                        self.uart.write(tx)
                        utils.verbose("=> CC", config.VERBOSE)
                        rx = self.get_reply()
                        if self.ack(rx):
                            return True
                except Exception as err:
                    utils.log("{} => set_usr_cfg ({}): {}".format(self.name, type(err).__name__, err), "e")  # DEBUG
                    break
        utils.log("{} => unable to upload the deployment configuration".format(self.name), "e")  # DEBUG
        return False

    def set_deployment_start(self, sampling_interval, avg_interval):
        """Computes the measurement starting time to be in synch with the scheduler."""
        now = utime.time() - self.activation_delay
        next_sampling = now - now % sampling_interval + sampling_interval + self.activation_delay
        sampling_start = next_sampling - self.samples // self.sample_rate
        utils.log("{} => deployment t0 at {}, measurement interval {}\", average interval {}\"".format(self.name, utils.timestring(sampling_start), sampling_interval, avg_interval))  # DEBUG
        deployment_start = utime.localtime(sampling_start + sampling_interval - avg_interval)
        deployment_start = ubinascii.unhexlify("{:02d}{:02d}{:02d}{:02d}{:02d}{:02d}".format(deployment_start[4], deployment_start[5], deployment_start[2], deployment_start[3], int(str(deployment_start[0])[2:]), deployment_start[1]))
        return deployment_start

    def parse_usr_cfg(self, bytestring):
        """Parses the deployment config."""
        try:
            return (
                "{:02x}".format(bytestring[0]),                                     # [0] Sync
                "{:02x}".format((int.from_bytes(bytestring[1:2], "little"))),       # [1] Id
                int.from_bytes(bytestring[2:4], "little"),                          # [2] Size
                int.from_bytes(bytestring[4:6], "little"),                          # [3] T1
                int.from_bytes(bytestring[6:8], "little"),                          # [4] T2, BlankingDistance
                int.from_bytes(bytestring[8:10], "little"),                         # [5] T3
                int.from_bytes(bytestring[10:12], "little"),                        # [6] T4
                int.from_bytes(bytestring[12:14], "little"),                        # [7] T5
                int.from_bytes(bytestring[14:16], "little"),                        # [8] NPings
                int.from_bytes(bytestring[16:18], "little"),                        # [9] AvgInterval
                int.from_bytes(bytestring[18:20], "little"),                        # [10] NBeams
                self.decode_usr_timctrlreg(int.from_bytes(bytestring[20:22], "little")),   # [11] TimCtrlReg
                self.decode_usr_pwrctrlreg(int.from_bytes(bytestring[22:24], "little")),   # [12] Pwrctrlreg
                bytestring[24:26],                                                  # [13] A1 Not used.
                bytestring[26:28],                                                  # [14] B0 Not used.
                bytestring[28:30],                                                  # [15] B1 Not used.
                int.from_bytes(bytestring[30:32], "little"),                        # [16] CompassUpdRate
                self.coord_system[int.from_bytes(bytestring[32:34], "little")],     # [17] CoordSystem
                int.from_bytes(bytestring[34:36], "little"),                        # [18] Nbins
                int.from_bytes(bytestring[36:38], "little"),                        # [19] BinLength
                int.from_bytes(bytestring[38:40], "little"),                        # [20] MeasInterval
                bytestring[40:46].decode("utf-8"),                                  # [21] DeployName
                int.from_bytes(bytestring[46:48], "little"),                        # [22] WrapMode
                ubinascii.hexlify(bytestring[48:54]).decode("utf-8"),               # [23] ClockDeploy
                int.from_bytes(bytestring[54:58], "little"),                        # [24] DiagInterval
                self.decode_usr_mode(int.from_bytes(bytestring[58:60], "little")), # [25] Mode
                int.from_bytes(bytestring[60:62], "little"),                        # [26] AdjSoundSpeed
                int.from_bytes(bytestring[62:64], "little"),                        # [27] NSampDiag
                int.from_bytes(bytestring[64:66], "little"),                        # [28] NbeamsCellDiag
                int.from_bytes(bytestring[66:68], "little"),                        # [29] NpingDiag
                self.decode_usr_modetest(int.from_bytes(bytestring[68:70], "little")),     # [30] ModeTest
                int.from_bytes(bytestring[68:72], "little"),                        # [31] AnaInAddr
                int.from_bytes(bytestring[72:74], "little"),                        # [32] SWVersion
                int.from_bytes(bytestring[74:76], "little"),                        # [33] Salinity
                ubinascii.hexlify(bytestring[76:256]),                              # [34] VelAdjTable
                bytestring[256:336].decode("utf-8"),                                # [35] Comments
                ubinascii.hexlify(bytestring[336:384]),                             # [36] Spare
                int.from_bytes(bytestring[384:386], "little"),                      # [37] Processing Method
                ubinascii.hexlify(bytestring[386:436]),                             # [38] Spare
                self.decode_usr_wavemode(int.from_bytes(bytestring[436:438], "little")),   # [39] Wave Measurement Mode
                int.from_bytes(bytestring[438:440], "little"),                      # [40] DynPercPos
                int.from_bytes(bytestring[440:442], "little"),                      # [41] T1
                int.from_bytes(bytestring[442:444], "little"),                      # [42] T2
                int.from_bytes(bytestring[444:446], "little"),                      # [43] T3
                int.from_bytes(bytestring[446:448], "little"),                      # [44] NSamp
                bytestring[448:450].decode("utf-8"),                                # [45] A1 Not used.
                bytestring[450:452].decode("utf-8"),                                # [46] B0 Not used.
                bytestring[452:454].decode("utf-8"),                                # [47] B1 Not used.
                ubinascii.hexlify(bytestring[454:456]),                             # [48] Spare
                int.from_bytes(bytestring[456:458], "little"),                      # [49] AnaOutScale
                int.from_bytes(bytestring[458:460], "little"),                      # [50] CorrThresh
                ubinascii.hexlify(bytestring[460:462]),                             # [51] Spare
                int.from_bytes(bytestring[462:464], "little"),                      # [52] TiLag2
                ubinascii.hexlify(bytestring[464:486]),                             # [53] Spare
                bytestring[486:510]                                                 # [54] QualConst
                )
        except Exception as err:
            utils.log("{} => parse_usr_cfg ({}): {}".format(self.name, type(err).__name__, err), "e")  # DEBUG

    def decode_usr_timctrlreg(self, bytestring):
        """Decodes timing control register."""
        try:
            timctrlreg = "{:016b}".format(bytestring)
            return timctrlreg
        except Exception as err:
            utils.log("{} => decode_usr_timctrlreg ({}): {}".format(self.name, type(err).__name__, err), "e")  # DEBUG

    def decode_usr_pwrctrlreg(self, bytestring):
        """Decodes power control register."""
        try:
            pwrctrlreg = "{:016b}".format(bytestring)
            return pwrctrlreg
        except Exception as err:
            utils.log("{} => decode_usr_pwrctrlreg ({}): {}".format(self.name, type(err).__name__, err), "e")  # DEBUG

    def decode_usr_mode(self, bytestring):
        """Decodes mode."""
        try:
            mode = "{:016b}".format(bytestring)
            return mode
        except Exception as err:
            utils.log("{} => decode_usr_mode ({}): {}".format(self.name, type(err).__name__, err), "e")  # DEBUG

    def decode_usr_modetest(self, bytestring):
        """Decodes mode test."""
        try:
            modetest = "{:016b}".format(bytestring)
            return modetest
        except Exception as err:
            utils.log("{} => decode_usr_modetest ({}): {}".format(self.name, type(err).__name__, err), "e")  # DEBUG

    def decode_usr_wavemode(self, bytestring):
        """Decodes wave mode."""
        try:
            wavemode = "{:016b}".format(bytestring)
            return wavemode
        except Exception as err:
            utils.log("{} => decode_usr_wavemode ({}): {}".format(self.name, type(err).__name__, err), "e")  # DEBUG

    def parse_head_cfg(self, bytestring):
        """Parses the head config."""
        try:
            return (
                "{:02x}".format(bytestring[0]),                                     # [0] Sync
                "{:02x}".format(int.from_bytes(bytestring[1:2], "little")),         # [1] Id
                int.from_bytes(bytestring[2:4], "little") * 2,                      # [2] Size
                self.decode_head_cfg(int.from_bytes(bytestring[4:6], "little")),   # [3] Config
                int.from_bytes(bytestring[6:8], "little"),                          # [4] Frequency
                bytestring[8:10],                                                   # [5] Type
                bytestring[10:22].decode("ascii"),                                  # [6] SerialNo
                bytestring[22:198],                                                 # [7] System
                bytestring[198:220],                                                # [8] Spare
                int.from_bytes(bytestring[220:222], "little")                       # [9] NBeams
                )
        except Exception as err:
            utils.log("{} => parse_head_cfg ({}): {}".format(self.name, type(err).__name__, err), "e")  # DEBUG

    def decode_head_cfg(self, cfg):
        """Decodes the head config."""
        try:
            return (
                "PRESSURE SENSOR {}".format("YES" if cfg >> 0 & 1  else "NO"),
                "MAGNETOMETER SENSOR {}".format("YES" if cfg >> 1 & 1  else "NO"),
                "PRESSURE SENSOR {}".format("YES" if cfg >> 2 & 1  else "NO"),
                "{}".format("DOWN" if cfg >> 3 & 1  else "UP")
                )
        except Exception as err:
            utils.log("{} => decode_head_cfg ({}): {}".format(self.name, type(err).__name__, err), "e")  # DEBUG

    def get_status(self, status):
        """Decodes the tilt mounting."""
        try:
            return(
                "{}".format("DOWN" if status >> 0 & 1 else "UP"),
                "SCALING {} mm/s".format("0.1" if status >> 1 & 1 else "1"),
                "PITCH {}".format("OUT OF RANGE" if status >> 2 & 2 else "OK"),
                "ROLL {}".format("OUT OF RANGE" if status >> 3 & 1 else "OK"),
                self.get_wkup_state(status),
                self.get_power_level(status)
                )
        except Exception as err:
            utils.log("{} => get_status ({}): {}".format(self.name, type(err).__name__, err), "e")  # DEBUG

    def get_wkup_state(self, status):
        """Decodes the wakeup state."""
        try:
            return (
                "WKUP STATE {}".format(
                    "BAD POWER" if ~ status >> 5 & 1 and ~ status >> 4 & 1 else
                    "POWER APPLIED" if ~ status >> 5 & 1 and status >> 4 & 1 else
                    "BREAK" if status >> 5 & 1 and ~ status >> 4 & 1 else
                    "RTC ALARM" if status >> 5 & 1 and status >> 4 & 1 else None)
                )
        except Exception as err:
            utils.log("{} => get_wkup_state ({}): {}".format(self.name, type(err).__name__, err), "e")  # DEBUG

    def get_power_level(self, status):
        """Decodes the power level."""
        try:
            return (
                "POWER LEVEL {}".format(
                    "0" if ~ status >> 7 & 1 and ~ status >> 6 & 1 else
                    "1" if ~ status >> 7 & 1 and status >> 6 & 1 else
                    "2" if status >> 7 & 1 and ~ status >> 6 & 1 else
                    "3" if status >> 7 & 1 and status >> 6 & 1 else None)
                )
        except Exception as err:
            utils.log("{} => get_power_level ({}): {}".format(self.name, type(err).__name__, err), "e")  # DEBUG

    def get_error(self, error):
        """Decodes the error codes."""
        try:
            return(
                "COMPASS {}".format("ERROR" if error >> 0 & 1 else "OK"),
                "MEASUREMENT DATA {}".format("ERROR" if error >> 1 & 1 else "OK"),
                "SENSOR DATA {}".format("ERROR" if error >> 2 & 2 else "OK"),
                "TAG BIT {}".format("ERROR" if error >> 3 & 1 else "OK"),
                "FLASH {}".format("ERROR" if error >> 4 & 1 else "OK"),
                "BEAM NUMBER {}".format("ERROR" if error >> 5 & 1 else "OK"),
                "COORD. TRANSF. {}".format("ERROR" if error >> 3 & 1 else "OK")
                )
        except Exception as err:
            utils.log("{} => get_error ({}): {}".format(self.name, type(err).__name__, err), "e")  # DEBUG

    def format_recorder(self):
        """Erase all recorded data if it reached the maximum allowed files number (31)"""
        t0 = utime.time()
        while not self._timeout(t0, config.TIMEOUT):
            if self.break_():
                utils.verbose("=> FO", config.VERBOSE)
                self.uart.write(b"\x46\x4F\x12\xD4\x1E\xEF")
                if self.ack(self.get_reply()):
                    utils.log("{} => recorder formatted".format(self.name), "e")  # DEBUG
                    return True
        utils.log("{} => unable to format the recorder".format(self.name), "e")  # DEBUG
        return False

    def start_delayed(self):
        """Starts a measurement at a specified time based on the current
        configuration of the instrument. Data is stored to a new file in
        the recorder. Data is output on the serial port only if specified in
        the configuration.
        """
        t0 = utime.time()
        while not self._timeout(t0, config.TIMEOUT):
            if self.break_():
                utils.verbose("=> SD", config.VERBOSE)
                self.uart.write("SD")
                rx = self.get_reply()
                if self.ack(rx):
                    return True
                self.format_recorder()
        utils.log("{} => unable to start measurement".format(self.name), "e")  # DEBUG
        return False

    def conv_data(self, bytestring):
        """Converts sample bytestring to ascii string."""
        try:
            return (
                ubinascii.hexlify(bytestring[9:10]),                                # [0] Month
                ubinascii.hexlify(bytestring[6:7]),                                 # [1] Day
                ubinascii.hexlify(bytestring[8:9]),                                 # [2] Year
                ubinascii.hexlify(bytestring[7:8]),                                 # [3] Hour
                ubinascii.hexlify(bytestring[4:5]),                                 # [4] Minute
                ubinascii.hexlify(bytestring[5:6]),                                 # [5] Second
                self.get_error(int.from_bytes(bytestring[10:12], "little")),       # [6] Error code
                self.get_status(int.from_bytes(bytestring[25:26], "little")),      # [7] Status code
                int.from_bytes(bytestring[14:16], "little") / 10,                   # [8] Battery voltage
                int.from_bytes(bytestring[16:18], "little") / 10,                   # [9] Soundspeed
                int.from_bytes(bytestring[18:20], "little") / 10,                   # [10] Heading
                int.from_bytes(bytestring[20:22], "little") / 10,                   # [11] Pitch
                int.from_bytes(bytestring[22:24], "little") / 10,                   # [12] Roll
                self.calc_pressure(bytestring[24:25], bytestring[26:28]) / 1000,   # [13] Pressure
                int.from_bytes(bytestring[28:30], "little") / 100,                  # [14] Temperature
                int.from_bytes(bytestring[12:14], "little") / 10,                   # [15] Analog input 1
                int.from_bytes(bytestring[16:18], "little") / 10                    # [16] Analog input 2
                ) + self.get_cells(bytestring[30:])                                # [17:] x1,y1,z1, x2, y2, z2, x3, y3, z3...
        except Exception as err:
            utils.log("{} => conv_data ({}): {}".format(self.name, type(err).__name__, err), "e")  # DEBUG

    def calc_pressure(self, pressureMSB, pressureLSW):
        """Calculates pressure value."""
        try:
            return 65536 * int.from_bytes(pressureMSB, "little") + int.from_bytes(pressureLSW, "little")
        except Exception as err:
            utils.log("{} => calc_pressure ({}): {}".format(self.name, type(err).__name__, err), "e")  # DEBUG

    def get_cells(self, bytestring):
        """Extracts cells data from sample bytestring.

        Params:
            bytestring
        Returns:
            list(x1, x2, x3... y1, y2, y3... z1, z2, z3..., a11, a12 , a13..., a21, a22, a23..., a31, a32, a33...)
        """
        cells = []
        try:
            if self.usr_cfg:
                nbins = self.usr_cfg[18]
                nbeams = self.usr_cfg[10]
                j = 0
                for beam in range(nbeams):
                    for bin in range(nbins):
                        cells.append(int.from_bytes(bytestring[j:j+2], "little"))
                        j += 2
                for beam in range(nbeams):
                    for bin in range(nbins):
                        cells.append(int.from_bytes(bytestring[j:j+1], "little"))
                        j += 1
        except Exception as err:
            utils.log("{} => get_cells ({}): {}".format(self.name, type(err).__name__, err), "e")  # DEBUG
        return tuple(cells)

    def get_flow(self):
        """Calculates the fluid flow (rivers only). TODO"""
        return 0

    def _(self, bytestring):
        """Gets the response to a break commmand."""
        try:
            return bytestring.decode("utf-8")
        except Exception as err:
            utils.log("{} => _ ({}): {}".format(self.name, type(err).__name__, err), "e")  # DEBUG

    def get_clock(self):
        """Reads the instrument RTC."""
        t0 = utime.time()
        while not self._timeout(t0, config.TIMEOUT):
            if self.break_():
                utils.verbose("=> RC", config.VERBOSE)
                self.uart.write("RC")
                rx = self.get_reply()
                if self.ack(rx):
                    try:
                        rx = ubinascii.hexlify(rx)
                        return "20{:2s}-{:2s}-{:2s} {:2s}:{:2s}:{:2s}".format(
                            rx[8:10], # Year
                            rx[10:12],# Month
                            rx[4:6],  # Day
                            rx[6:8],  # Hour
                            rx[0:2],  # Minute
                            rx[2:4])  # Seconds
                    except Exception as err:
                        utils.log("{} => get_clock ({}): {}".format(self.name, type(err).__name__, err), "e")  # DEBUG
                        break
        return False

    def set_clock(self):
        """Sets up the instrument RTC.

        mm ss DD hh YY MM (3 words of 2 bytes each)
        """
        t0 = utime.time()
        while not self._timeout(t0, config.TIMEOUT):
            if self.break_():
                now = utime.localtime()
                tx = "{:02d}{:02d}{:02d}{:02d}{:02d}{:02d}".format(now[4], now[5], now[2], now[3], int(str(now[0])[2:]), now[1])
                self.uart.write("SC")
                self.uart.write(ubinascii.unhexlify(tx))
                utils.verbose("=> SC" + str(tx), config.VERBOSE)
                if self.ack(self.get_reply()):
                    utils.log("{} => set clock (UTC {})".format(self.name, self.get_clock()))  # DEBUG
                    return True
        utils.log("{} => unable to synchronize the real time clock".format(self.name), "e")  # DEBUG
        return False

    def format_data(self, sample):
        """Formats data according to output format."""
        data = [
            self.config["String_Label"],
            "{:2s}/{:2s}/20{:2s}".format(sample[1], sample[0], sample[2]),  # dd/mm/yyyy
            "{:2s}:{:2s}".format(sample[3], sample[4]),                     # hh:mm
            "{}".format(sample[8]),                                         # Battery
            "{}".format(sample[9]),                                         # SoundSpeed
            "{}".format(sample[10]),                                        # Heading
            "{}".format(sample[11]),                                        # Pitch
            "{}".format(sample[12]),                                        # Roll
            "{}".format(sample[13]),                                        # Pressure
            "{}".format(sample[14]),                                        # Temperature
            "{}".format(self.get_flow()),                                  # Flow
            "{}".format(self.usr_cfg[17]),                                  # CoordSystem
            "{}".format(self.usr_cfg[4]),                                   # BlankingDistance
            "{}".format(self.usr_cfg[20]),                                  # MeasInterval
            "{}".format(self.usr_cfg[19]),                                  # BinLength
            "{}".format(self.usr_cfg[18]),                                  # NBins
            "{}".format(self.head_cfg[3][3]),                               # TiltSensorMounting
            ]
        j = 17
        for bin in range(self.usr_cfg[18]):
            data.append("#{}".format(bin + 1))                              # (#Cell number)
            for beam in range(self.usr_cfg[10]):
                data.append("{}".format(sample[j]))                         # East, North, Up/Down
                j += 1
        return data

    def log(self):
        """Writes out acquired data to file."""
        if self.data:
            utils.log_data(config.DATA_SEPARATOR.join(self.format_data(map(str, self.data))))

    def main(self):
        """Retreives data from a serial device."""
        utils.log("{} => acquiring data...".format(self.name))
        self.led.on()
        t0 = utime.time()
        while True:
            if self._timeout(t0, self.timeout):
                utils.log("{} => timeout occourred".format(self.name), "e")  # DEBUG
                if not self.data:
                    utils.log("{} => no data received".format(self.name), "e")  # DEBUG
                break
            if self.uart.any():
                self.parse_cfg()
                self.data.extend(self.conv_data(self.uart.read()))
                break
        self.led.off()
