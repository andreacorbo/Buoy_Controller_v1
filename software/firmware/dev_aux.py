import utime
from device import DEVICE
import tools.utils as utils
import constants

class AUX(DEVICE):
    """Creates an aux object."""

    def __init__(self, instance, tasks=[]):
        DEVICE.__init__(self, instance, tasks)

    def start_up(self):
        """Performs device specific initialization sequence."""
        self.off()
        return
