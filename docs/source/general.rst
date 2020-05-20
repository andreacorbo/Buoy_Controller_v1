

####################
General informations
####################

The ``Buoy Controller v1`` has been developed to meet the requirements and best
fit the needs of the OGS MAMBO buoys of the Northern Adriatic Sea.
The controller itself is based on a commercial MCU development board
called :ref:`pyboard <pyboard_quickref>`, hosted on a customized in-house
developed breakout board. The latter represent the hardware interface to the
instruments that form an oceanographic telemetry buoy system.

The ``pyboard`` is a :term:`baremetal` OS'less SoM, which runs the
:doc:`MicroPython <micropython:index>` firmware, an implementation of the
Python 3.4 that has been ported on several MCU-based systems.
In this scenario ``MicroPython`` effectively functions like a small operating system,
running user programs and providing a command interpreter ``REPL``.
