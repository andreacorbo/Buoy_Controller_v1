#########
Constants
#########

The ``constants.py`` file contains the global system parameters.

.. list-table::
    :widths: 1, 1, 1000

    *   - ``CONFIG_DIR``
        - :obj:`str`
        - Configuration files directory

    *   - ``CONFIG_TYPE``
        - :obj:`str`
        - Configuration files type

    *   - ``LOG_DIR``
        - :obj:`str`
        - Log files directory

    *   - ``LOG_LEVEL``
        - :obj:`int`
        - Log level 0 = screen output, 1 = log to file

    *   - ``VERBOSE``
        - :obj:`int`
        - Message verbosity 0 = nothing, 1 = shows device activity

    *   - ``DEVICE_STATUS``
        - :obj:`dict`
        - Device status stored in the :attr:`tools.utils.status_table` *{0:"OFF", 1:"ON", 2:"READY"}*

    *   - ``DEVICES``
        - :obj:`dict`
        - Device to uart number mapping *{"device1_instance":1, ...}*

    *   - ``UARTS``
        - :obj:`dict`
        - Uart number to bus mapping *{1:2, 2:4, 3:6, 4:1}*

    *   - ``LEDS``
        - :obj:`dict`
        - Board status to leds mapping red=1, green=2, yellow=3, blue=4 *{"IO":1, "PWR":2, "RUN":3, "SLEEP":4}*

    *   - ``TIMEOUT``
        - :obj:`int`
        - Generic timeout in seconds.

    *   - ``WD_TIMEOUT``
        - :obj:`int`
        - Watchdog timer timeout in milliseconds.

    *   - ``ESC_CHAR``
        - :obj:`str`
        - Escape character that has to be typed 3 times to break main loop.

    *   - ``PASSWD``
        - :obj:`str`
        - Login password.

    *   - ``LOGIN_ATTEMPTS``
        - :obj:`int`
        - Maximum number of login attempts.

    *   - ``SESSION_TIMEOUT``
        - :obj:`int`
        - Session timeout in seconds.

    *   - ``MEDIA``
        - :obj:`list`
        - Available data files locations *["/sd", "/flash"]*

    *   - ``DATA_DIR``
        - :obj:`str`
        - Data files directory.

    *   - ``DATA_FILE_NAME``
        - :obj:`str`
        - Data files conventional name.

    *   - ``DATA_SEPARATOR``
        - :obj:`str`
        - Record data separator.

    *   - ``DATA_ACQUISITION_INTERVAL``
        - :obj:`int`
        - Seconds between two data acquisitions, valid unless specified in the ``SCHEDULER`` parameter.

    *   - ``TASK_SCHEDULER``
        - :obj:`dict`
        -  Bidimensional dictionary used to schedule any kind of task. Each device is identified by it's name and instance number. The task name corresponds to the object method to invoke. The interval is in seconds. *{"device1_instance1":{"task1":interval, ...}, ...}*

    *   - ``TMP_FILE_PFX``
        - :obj:`str`
        - Partially sent data file prefix.

    *   - ``SENT_FILE_PFX``
        - :obj:`str`
        - Totally sent data file prefix.

    *   - ``BUF_DAYS``
        - :obj:`int`
        - Days data files will be kept in the transmission queue. Elder files will be ignored.

.. warning::

    Due to limited flash capacity, redirect data to this location in case of an
    SD failure it's not possible.

.. note::

    To set the data acquisition interval for a certain device that is different
    from the value specified by the ``DATA_ACQUISITION_INTERVAL`` parameter,
    insert a task **"log"** for that device.
