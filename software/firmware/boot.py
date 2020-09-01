import pyb
import os

pyb.freq(84000000)  # Sets main clock to reduce power consumption.

pyb.usb_mode("VCP")  # Sets usb device to act only as virtual com port, needed
                     # to map pyboard to static dev on linux systems.
try:
    os.mount(pyb.SDCard(), "/sd")  # Mounts SD card to save data into.
except:
    print("UNABLE TO MOUNT SD")
