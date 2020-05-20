##################
Software reference
##################

The ``Buoy Controller v1`` software is composed of a :ref:`base system` that provides
the basic functionalities to run a fully autonomous telemetry system and an
extensible collection of instrument specific modules. Both globals and
instruments related parameters are kept separate from the source code allowing
the change of the system behavior by simply uploading a new configuration file.


***********
Base system
***********

.. rst-class:: dirtree

.. toctree::
    :maxdepth: 2

    configs<configs/index>
    tools<tools/index>
    boot<boot>
    constants<constants>
    device<device>
    main<main>
    menu<menu>
    pyboard<pyboard>
    scheduler<scheduler>
    session<session>

Multithreading
==============

The ``Buoy Controller v1`` software takes advantage of the ``MicroPython``
native support to the :doc:`multithreading<library/_thread>` programming
to parallelize instruments tasks. This reduce the total duration of the data
acquisition session, allowing the system to stay in sleep mode for the majority
of the time saving precious energy. Furthermore in a big instrument set scenario
the time gap between the first and the last instrument data acquisition session
is drastically reduced.

Watchdog
========

A software ``watchdog`` object is created at system boot up and "fed" every 30
seconds during normal conditions. An unexpected exception that produce the stall
of the ``main`` routine, cause the watchdog to restart the system.

.. attention::

    Because of the system normally goes to sleep mode if no tasks are running,
    it wakes up periodically before the watchdog timeout get expired just to
    feed it and then goes back to sleep mode.

.. note::

    The watchdog timeout has to be great than 1000ms and less than 32000ms.


***************
Devices modules
***************

Devices modules extend the :ref:`Base system`.
The module file name corresponds to the instrument manufacturer and contains a
``class`` for each instrument model.
A configuration file with the same name is included in the ``config`` directory
as at system startup all the modules with a valid configuration will be loaded
and one or more instances of the correspondent device object created.

.. hint::

    To keep things ordered and easily identify a device module in the directory
    tree, a prefix *dev_* has been added both to the module and its configuration
    file name.


.. toctree::
   :maxdepth: 1

   devices/adcp
   devices/ctd
   devices/gps
   devices/meteo
   devices/modem


**********************
Firmware (Micropython)
**********************

.. toctree::
    :maxdepth: 1
    :hidden:

    ../firmware_uploader

.. attention::

    Due to the restricted hardware resource (RAM and FLASH) of the Pyboard,
    the software must be compiled and loaded toghether with the Micropython
    firmware , this way the compiler does not allocate precious RAM to load
    modules into. This process has been automated with a bash script
    :doc:`firmware_uploader.sh<../firmware_uploader>`.

    To boot up the system from the internal flash, instead of the SD card, an empty
    file named SKIPSD has to be created in the software root.
    The SD card should acts only as a data acquisition files storage under the
    ``data`` directory .
