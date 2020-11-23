import pyb
import time
import ubinascii
from configs import dfl, cfg
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

    def __init__(self, instance):
        DEVICE.__init__(self, instance)

    def start_up(self):
        self.on()
        time.sleep_ms(500)  # Allows instrument to start properly prior to send commands
        if self.break_():
            self.set_clock()
            #self.set_usr_cfg()  DEBUG
            #self.get_cfg()  DEBUG
            self.start_delayed()
        self.parse_cfg()

    def get_reply(self, timeout=0):
        """Returns replies from instrument."""
        t0 = time.time()
        rx_buff = bytearray()
        while not self._timeout(t0, timeout):
            if self.uart.any():
                return self.uart.readinto(rx_buff)

    def ack(self, rx):
        """Parses acknowledgement bytes sequence."""
        if rx:
            if rx[-2:] == b'\x06\x06':
                return True
            elif rx[-2:] == b'\x15\x15':
                return False

    def break_(self):
        """Sends break sequence to instrument."""
        def confirm():
            """Enters command mode."""
            self.uart.write("MC")
            if self.ack(self.get_reply()):
                return True
            return False

        self.uart.write("@@@@@@")
        time.sleep_ms(100)
        self.uart.write("K1W%!Q")
        t0 = time.time()
        while not self._timeout(t0, cfg.TIMEOUT):
            rx = self.get_reply()
            if self.ack(rx):
                if b'\x0a\x0d\x43\x6f\x6e\x66\x69\x72\x6d\x3a' in rx:
                    confirm()
                else:
                    return True
        utils.log("{} => did not respond in {} secs.".format(self.name, cfg.TIMEOUT), "e")  # DEBUG
        return False

    def calc_checksum(self, reply):
        """Computes the data checksum: b58c(hex) + sum of all words in structure."""
        sum=0
        j=0
        for i in range(int.from_bytes(reply[2:4], "little")-1):
            sum += int.from_bytes(reply[j:j+2], "little")
            j = j+2
        return (int.from_bytes(b'\xb5\x8c', "big") + sum) % 65536

    def verify_checksum(self, reply):
        """Verifies the data checksum."""
        checksum = int.from_bytes(reply[-2:], "little")
        calc_checksum = self.calc_checksum(reply)
        if checksum != calc_checksum:
            utils.log("invalid checksum calculated: {} got: {}".format(calc_checksum, checksum), "e")
            return False
        return True

    def set_clock(self):
        """Sets up the instrument RTC.

        mm ss DD hh YY MM (3 words of 2 bytes each)
        """
        def get_clock():
            """Reads the instrument RTC."""
            t0 = time.time()
            while not self._timeout(t0, cfg.TIMEOUT):
                if self.break_():
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

        t0 = time.time()
        while not self._timeout(t0, cfg.TIMEOUT):
            if self.break_():
                now = time.localtime()
                self.uart.write("SC")
                self.uart.write(ubinascii.unhexlify("{:02d}{:02d}{:02d}{:02d}{:02d}{:02d}".format(now[4], now[5], now[2], now[3], int(str(now[0])[2:]), now[1])))
                if self.ack(self.get_reply()):
                    utils.log("{} => set clock (UTC {})".format(self.name, get_clock()))  # DEBUG
                    return True
        utils.log("{} => unable to synchronize the real time clock".format(self.name), "e")  # DEBUG
        return False

    def get_cfg(self):
        """Retreives the complete configuration data from the instrument."""
        t0 = time.time()
        while not self._timeout(t0, cfg.TIMEOUT):
            if self.break_():
                self.uart.write("GA")
                rx = self.get_reply()
                if self.ack(rx) and self.verify_checksum(rx[0:48]) and self.verify_checksum(rx[48:272]) and self.verify_checksum(rx[272:784]):
                    try:
                        with open(dfl.CONFIG_DIR + "/" + self.config["Adcp"]["Instrument_Config"], "wb") as cfg:
                            cfg.write(rx)
                            return True
                    except Exception as err:
                        utils.log("{} => get_cfg ({}): {}".format(self.name, type(err).__name__, err), "e")  # DEBUG
                        break
        utils.log("{} => unable to retreive the instrument configuration".format(self.name), "e")  # DEBUG
        return False

    def parse_cfg(self):
        """Parses the configuration data."""
        def parse_hw_cfg(reply):
            """Parses the hardware configuration."""
            def decode_hw_cfg(cfg):
                """Decodes hardware config."""
                try:
                    return (
                        "RECORDER {}".format("NO" if cfg >> 0 & 1  else "YES"),
                        "COMPASS {}".format("NO" if cfg >> 1 & 1  else "YES")
                        )
                except Exception as err:
                    utils.log("{} => decode_hw_cfg ({}): {}".format(self.name, type(err).__name__, err), "e")  # DEBUG

            def decode_hw_status(status):
                """Decodes hardware status."""
                try:
                    return "VELOCITY RANGE {}".format("HIGH" if status >> 0 & 1  else "NORMAL")
                except Exception as err:
                    utils.log("{} => decode_hw_status ({}): {}".format(self.name, type(err).__name__, err), "e")  # DEBUG

            try:
                return (
                    "{:02x}".format(reply[0]),                                         # [0] Sync
                    "{:02x}".format(int.from_bytes(reply[1:2], "little")),             # [1] Id
                    int.from_bytes(reply[2:4], "little"),                              # [2] Size
                    reply[4:18].decode("ascii"),                                       # [3] SerialNo
                    decode_hw_cfg(int.from_bytes(reply[18:20], "little")),       # [4] Config
                    int.from_bytes(reply[20:22], "little"),                            # [5] Frequency
                    reply[22:24],                                                      # [6] PICVersion
                    int.from_bytes(reply[24:26], "little"),                            # [7] HWRevision
                    int.from_bytes(reply[26:28], "little"),                            # [8] RecSize
                    decode_hw_status(int.from_bytes(reply[28:30], "little")),    # [9] Status
                    reply[30:42],                                                      # [10] Spare
                    reply[42:46].decode("ascii")                                       # [11] FWVersion
                    )
            except Exception as err:
                utils.log("{} => parse_hw_cfg ({}): {}".format(self.name, type(err).__name__, err), "e")  # DEBUG

        def parse_head_cfg(bytestring):
            """Parses the head config."""
            def decode_head_cfg(cfg):
                """Decodes the head config."""
                try:
                    return (
                        "PRESSURE SENSOR {}".format("YES" if cfg >> 0 & 1  else "NO"),
                        "MAGNETOMETER SENSOR {}".format("YES" if cfg >> 1 & 1  else "NO"),
                        "TILT SENSOR {}".format("YES" if cfg >> 2 & 1  else "NO"),
                        "{}".format("DOWN" if cfg >> 3 & 1  else "UP")
                        )
                except Exception as err:
                    utils.log("{} => decode_head_cfg ({}): {}".format(self.name, type(err).__name__, err), "e")  # DEBUG

            try:
                return (
                    "{:02x}".format(bytestring[0]),                               # [0] Sync
                    "{:02x}".format(int.from_bytes(bytestring[1:2], "little")),   # [1] Id
                    int.from_bytes(bytestring[2:4], "little") * 2,                # [2] Size
                    decode_head_cfg(int.from_bytes(bytestring[4:6], "little")),   # [3] Config
                    int.from_bytes(bytestring[6:8], "little"),                    # [4] Frequency
                    bytestring[8:10],                                             # [5] Type
                    bytestring[10:22].decode("ascii"),                            # [6] SerialNo
                    bytestring[22:198],                                           # [7] System
                    bytestring[198:220],                                          # [8] Spare
                    int.from_bytes(bytestring[220:222], "little")                  # [9] NBeams
                    )
            except Exception as err:
                utils.log("{} => parse_head_cfg ({}): {}".format(self.name, type(err).__name__, err), "e")  # DEBUG

        def parse_usr_cfg(bytestring):
            """Parses the deployment config."""
            def decode_usr_timctrlreg(bytestring):
                """Decodes timing control register."""
                try:
                    return "{:016b}".format(bytestring)
                except Exception as err:
                    utils.log("{} => decode_usr_timctrlreg ({}): {}".format(self.name, type(err).__name__, err), "e")  # DEBUG

            def decode_usr_pwrctrlreg(bytestring):
                """Decodes power control register."""
                try:
                    return "{:016b}".format(bytestring)
                except Exception as err:
                    utils.log("{} => decode_usr_pwrctrlreg ({}): {}".format(self.name, type(err).__name__, err), "e")  # DEBUG

            def decode_usr_mode(bytestring):
                """Decodes mode."""
                try:
                    return "{:016b}".format(bytestring)
                except Exception as err:
                    utils.log("{} => decode_usr_mode ({}): {}".format(self.name, type(err).__name__, err), "e")  # DEBUG

            def decode_usr_modetest(bytestring):
                """Decodes mode test."""
                try:
                    return "{:016b}".format(bytestring)
                except Exception as err:
                    utils.log("{} => decode_usr_modetest ({}): {}".format(self.name, type(err).__name__, err), "e")  # DEBUG

            def decode_usr_wavemode(bytestring):
                """Decodes wave mode."""
                try:
                    return "{:016b}".format(bytestring)
                except Exception as err:
                    utils.log("{} => decode_usr_wavemode ({}): {}".format(self.name, type(err).__name__, err), "e")  # DEBUG

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
                    decode_usr_timctrlreg(int.from_bytes(bytestring[20:22], "little")),   # [11] TimCtrlReg
                    decode_usr_pwrctrlreg(int.from_bytes(bytestring[22:24], "little")),   # [12] Pwrctrlreg
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
                    decode_usr_mode(int.from_bytes(bytestring[58:60], "little")),       # [25] Mode
                    int.from_bytes(bytestring[60:62], "little"),                        # [26] AdjSoundSpeed
                    int.from_bytes(bytestring[62:64], "little"),                        # [27] NSampDiag
                    int.from_bytes(bytestring[64:66], "little"),                        # [28] NbeamsCellDiag
                    int.from_bytes(bytestring[66:68], "little"),                        # [29] NpingDiag
                    decode_usr_modetest(int.from_bytes(bytestring[68:70], "little")),     # [30] ModeTest
                    int.from_bytes(bytestring[68:72], "little"),                        # [31] AnaInAddr
                    int.from_bytes(bytestring[72:74], "little"),                        # [32] SWVersion
                    int.from_bytes(bytestring[74:76], "little"),                        # [33] Salinity
                    ubinascii.hexlify(bytestring[76:256]),                              # [34] VelAdjTable
                    bytestring[256:336].decode("utf-8"),                                # [35] Comments
                    ubinascii.hexlify(bytestring[336:384]),                             # [36] Spare
                    int.from_bytes(bytestring[384:386], "little"),                      # [37] Processing Method
                    ubinascii.hexlify(bytestring[386:436]),                             # [38] Spare
                    decode_usr_wavemode(int.from_bytes(bytestring[436:438], "little")), # [39] Wave Measurement Mode
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

        try:
            with open(dfl.CONFIG_DIR + "/" + self.config["Adcp"]["Instrument_Config"], "rb") as cfg:
                bytes = cfg.read()
                self.hw_cfg = parse_hw_cfg(bytes[0:48])         # Hardware config (48 bytes)
                self.head_cfg = parse_head_cfg(bytes[48:272])   # Head config (224 bytes)
                self.usr_cfg = parse_usr_cfg(bytes[272:784])    # Deployment config (512 bytes)
            return True
        except Exception as err:
            utils.log("{} => parse_cfg ({}): {}".format(self.name, type(err).__name__, err), "e")  # DEBUG
            return False

    def set_usr_cfg(self):
        """Uploads a deployment config to the instrument and sets up the device
        Activation_Rate and Warmup_Interval parameters according to the current
        deployment config."""
        def set_deployment_start(sampling_interval, avg_interval):
            """Computes the measurement starting time to be in synch with the scheduler."""
            now = time.time() - self.activation_delay
            next_sampling = now - now % sampling_interval + sampling_interval + self.activation_delay
            sampling_start = next_sampling - self.samples // self.sample_rate
            utils.log("{} => deployment t0 at {}, measurement interval {}\", average interval {}\"".format(self.name, utils.timestring(sampling_start), sampling_interval, avg_interval))  # DEBUG
            deployment_start = time.localtime(sampling_start + sampling_interval - avg_interval)
            return ubinascii.unhexlify("{:02d}{:02d}{:02d}{:02d}{:02d}{:02d}".format(deployment_start[4], deployment_start[5], deployment_start[2], deployment_start[3], int(str(deployment_start[0])[2:]), deployment_start[1]))

        t0 = time.time()
        while not self._timeout(t0, cfg.TIMEOUT):
            if self.break_():
                try:
                    with open(dfl.CONFIG_DIR + "/" + self.config["Adcp"]["Deployment_Config"], "rb") as pfc:
                        cfg = pfc.read()
                        sampling_interval = int.from_bytes(cfg[38:40], "little")
                        avg_interval = int.from_bytes(cfg[16:18], "little")
                        dfg.TASK_SCHEDULE[self.name] = {"log":sampling_interval}
                        usr_cfg = cfg[0:48] + set_deployment_start(sampling_interval, avg_interval) + cfg[54:510]
                        checksum = self.calc_checksum(usr_cfg)
                        self.uart.write(b'\x43\x43')
                        self.uart.write(usr_cfg + ubinascii.unhexlify(hex(checksum)[-2:] + hex(checksum)[2:4]))
                        if self.ack(self.get_reply()):
                            return True
                except Exception as err:
                    utils.log("{} => set_usr_cfg ({}): {}".format(self.name, type(err).__name__, err), "e")  # DEBUG
                    break
        utils.log("{} => unable to upload the deployment configuration".format(self.name), "e")  # DEBUG
        return False

    def start_delayed(self):
        """Starts a measurement at a specified time based on the current
        configuration of the instrument. Data is stored to a new file in
        the recorder. Data is output on the serial port only if specified in
        the configuration.
        """
        def format_recorder():
            """Erase all recorded data if it reached the maximum allowed files number (31)"""
            t0 = time.time()
            while not self._timeout(t0, cfg.TIMEOUT):
                if self.break_():
                    self.uart.write(b'\x46\x4F\x12\xD4\x1E\xEF')
                    if self.ack(self.get_reply()):
                        utils.log("{} => recorder formatted".format(self.name), "e")  # DEBUG
                        return True
            utils.log("{} => unable to format the recorder".format(self.name), "e")  # DEBUG
            return False

        t0 = time.time()
        while not self._timeout(t0, cfg.TIMEOUT):
            if self.break_():
                self.uart.write("SD")
                if self.ack(self.get_reply()):
                    return True
                format_recorder()
        utils.log("{} => unable to start measurement".format(self.name), "e")  # DEBUG
        return False

    '''def get_cells(self, bytestring):
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
        return tuple(cells)'''

    def conv_data(self, bytestring):
        """Converts sample bytestring to ascii string."""
        def get_error(error):
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

        def get_status(status):
            """Decodes the tilt mounting."""
            def get_wkup_state(status):
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

            def get_power_level(status):
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

            try:
                return(
                    "{}".format("DOWN" if status >> 0 & 1 else "UP"),
                    "SCALING {} mm/s".format("0.1" if status >> 1 & 1 else "1"),
                    "PITCH {}".format("OUT OF RANGE" if status >> 2 & 2 else "OK"),
                    "ROLL {}".format("OUT OF RANGE" if status >> 3 & 1 else "OK"),
                    get_wkup_state(status),
                    get_power_level(status)
                    )
            except Exception as err:
                utils.log("{} => get_status ({}): {}".format(self.name, type(err).__name__, err), "e")  # DEBUG

        def calc_pressure(pressureMSB, pressureLSW):
            """Calculates pressure value."""
            try:
                return 65536 * int.from_bytes(pressureMSB, "little") + int.from_bytes(pressureLSW, "little")
            except Exception as err:
                utils.log("{} => calc_pressure ({}): {}".format(self.name, type(err).__name__, err), "e")  # DEBUG

        def get_cells(bytestring):
            """Extracts cells data from sample bytestring.

            Params:
                bytestring
            Returns:
                list(x1, x2, x3... y1, y2, y3... z1, z2, z3..., a11, a12 , a13..., a21, a22, a23..., a31, a32, a33...)
            """
            try:
                if self.usr_cfg:
                    nbins = self.usr_cfg[18]
                    nbeams = self.usr_cfg[10]
                    j = 0
                    for beam in range(nbeams):
                        for bin in range(nbins):
                            yield int.from_bytes(bytestring[j:j+2], "little")
                            j += 2
                    for beam in range(nbeams):
                        for bin in range(nbins):
                            yield int.from_bytes(bytestring[j:j+1], "little")
                            j += 1
            except Exception as err:
                utils.log("{} => get_cells ({}): {}".format(self.name, type(err).__name__, err), "e")  # DEBUG

        print(bytestring)
        try:
            return (
                ubinascii.hexlify(bytestring[9:10]),                           # [0] Month
                ubinascii.hexlify(bytestring[6:7]),                            # [1] Day
                ubinascii.hexlify(bytestring[8:9]),                            # [2] Year
                ubinascii.hexlify(bytestring[7:8]),                            # [3] Hour
                ubinascii.hexlify(bytestring[4:5]),                            # [4] Minute
                ubinascii.hexlify(bytestring[5:6]),                            # [5] Second
                get_error(int.from_bytes(bytestring[10:12], "little")),        # [6] Error code
                get_status(int.from_bytes(bytestring[25:26], "little")),       # [7] Status code
                int.from_bytes(bytestring[14:16], "little") / 10,              # [8] Battery voltage
                int.from_bytes(bytestring[16:18], "little") / 10,              # [9] Soundspeed
                int.from_bytes(bytestring[18:20], "little") / 10,              # [10] Heading
                int.from_bytes(bytestring[20:22], "little") / 10,              # [11] Pitch
                int.from_bytes(bytestring[22:24], "little") / 10,              # [12] Roll
                calc_pressure(bytestring[24:25], bytestring[26:28]) / 1000,    # [13] Pressure
                int.from_bytes(bytestring[28:30], "little") / 100,             # [14] Temperature
                int.from_bytes(bytestring[12:14], "little") / 10,              # [15] Analog input 1
                int.from_bytes(bytestring[16:18], "little") / 10               # [16] Analog input 2
                ) + tuple(get_cells(bytestring[30:]))                          # [17:] x1,y1,z1, x2, y2, z2, x3, y3, z3...
        except Exception as err:
            utils.log("{} => conv_data ({}): {}".format(self.name, type(err).__name__, err), "e")  # DEBUG

    def format_data(self, sample):
        """Formats data according to output format."""
        def get_flow():
            """Calculates the fluid flow (rivers only). TODO"""
            return 0

        record = [
        self.config["String_Label"],
        "{:2s}/{:2s}/20{:2s}".format(sample[1], sample[0], sample[2]),  # dd/mm/yyyy
        "{:2s}:{:2s}".format(sample[3], sample[4]),                     # hh:mm
        "{:.2f}".format(sample[8]),                                     # Battery
        "{:.2f}".format(sample[9]),                                     # SoundSpeed
        "{:.2f}".format(sample[10]),                                    # Heading
        "{:.2f}".format(sample[11]),                                    # Pitch
        "{:.2f}".format(sample[12]),                                    # Roll
        "{:.2f}".format(sample[13]),                                    # Pressure
        "{:.2f}".format(sample[14]),                                    # Temperature
        "{:.2f}".format(get_flow()),                                    # Flow
        "{}".format(self.usr_cfg[17]),                                  # CoordSystem
        "{}".format(self.usr_cfg[4]),                                   # BlankingDistance
        "{}".format(self.usr_cfg[20]),                                  # MeasInterval
        "{}".format(self.usr_cfg[19]),                                  # BinLength
        "{}".format(self.usr_cfg[18]),                                  # NBins
        "{}".format(self.head_cfg[3][3])                                # TiltSensorMounting
        ]

        j = 17
        for bin in range(self.usr_cfg[18]):
            record.append("#{}".format(bin + 1))                        # (#Cell number)
            for beam in range(self.usr_cfg[10]):
                record.append("{}".format(sample[j]))                   # East, North, Up/Down
                j += 1
        return record

    def log(self):
        """Writes out acquired data to file."""
        print(self.data)
        utils.log_data(dfl.DATA_SEPARATOR.join(self.format_data(self.conv_data(self.data))))

    def main(self, tasks=[]):
        """Retreives data from a serial device."""
        utils.log("{} => acquiring data...".format(self.name))  # DEBUG
        self.status(2)
        self.init_uart()
        pyb.LED(3).on()
        t0 = time.time()
        while True:
            if self._timeout(t0, self.timeout):
                utils.log("{} => no data received".format(self.name), "e")  # DEBUG
                break
            if self.uart.any():
                print(self.uart.read())
                break
        for t in tasks:
            exec("self."+t+"()",{"self":self})
        pyb.LED(3).off()
        self.uart.deinit()
