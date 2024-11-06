# SPDX-FileCopyrightText: 2018 Limor Fried for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
`adafruit_am2320`
====================================================

This is a CircuitPython driver for the AM2320 temperature and humidity sensor.

* Author(s): Limor Fried

Implementation Notes
--------------------

**Hardware:**

* Adafruit `AM2320 Temperature & Humidity Sensor
  <https://www.adafruit.com/product/3721>`_ (Product ID: 3721)

**Software and Dependencies:**

* Adafruit CircuitPython firmware for the supported boards:
  https://github.com/adafruit/circuitpython/releases
* Adafruit's Bus Device library: https://github.com/adafruit/Adafruit_CircuitPython_BusDevice

"""

# imports
import struct
import time

from adafruit_bus_device.i2c_device import I2CDevice
from micropython import const

try:
    # Used only for typing
    import typing  # pylint: disable=unused-import
    from busio import I2C
except ImportError:
    pass

__version__ = "0.0.0+auto.0"
__repo__ = "https://github.com/adafruit/Adafruit_CircuitPython_am2320.git"


AM2320_DEFAULT_ADDR = const(0x5C)
AM2320_CMD_READREG = const(0x03)
AM2320_REG_TEMP_H = const(0x02)
AM2320_REG_HUM_H = const(0x00)


def _crc16(data: bytearray) -> int:
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x0001:
                crc >>= 1
                crc ^= 0xA001
            else:
                crc >>= 1
    return crc


class AM2320:
    """A driver for the AM2320 temperature and humidity sensor.

    :param ~busio.I2C i2c_bus: The I2C bus the AM2320 is connected to.
                               This is the only required parameter.
    :param int address: (optional) The I2C address of the device. Defaults to :const:`0x5C`

    **Quickstart: Importing and using the AM2320**

        Here is an example of using the :class:`AM2320` class.
        First you will need to import the libraries to use the sensor

        .. code-block:: python

            import board
            import adafruit_am2320

        Once this is done you can define your `board.I2C` object and define your sensor object

        .. code-block:: python

            i2c = board.I2C()   # uses board.SCL and board.SDA
            am = adafruit_am2320.AM2320(i2c)

        Now you have access to the temperature using :attr:`temperature` attribute and
        the relative humidity using the :attr:`relative_humidity` attribute

        .. code-block:: python

            temperature = am.temperature
            relative_humidity = am.relative_humidity

    """

    def __init__(self, i2c_bus: I2C, address: int = AM2320_DEFAULT_ADDR):
        for _ in range(3):
            # retry since we have to wake up the devices
            try:
                self._i2c = I2CDevice(i2c_bus, address)
                return
            except ValueError:
                pass
            time.sleep(0.25)
        raise ValueError("AM2320 not found")

    def _read_register(self, register: int, length: int) -> bytearray:
        with self._i2c as i2c:
            write_success = False
            # wake up sensor
            for _ in range(3):
                try:
                    i2c.write(bytes([0x00]))
                    write_success = True
                    time.sleep(0.1)  # wait 100ms
                    break
                except OSError:
                    pass
            if not write_success:
                raise RuntimeError("Failed to wakeup I2C device")

            time.sleep(0.01)  # wait 10 ms

            # Send command to read register
            cmd = [AM2320_CMD_READREG, register & 0xFF, length]
            # print("cmd: %s" % [hex(i) for i in cmd])
            write_success = False
            for _ in range(3):
                try:
                    i2c.write(bytes(cmd))
                    write_success = True
                    time.sleep(0.005)
                    break
                except OSError:
                    pass
            if not write_success:
                raise RuntimeError("Failed to read from I2C device")

            time.sleep(0.002)  # wait 2 ms for reply
            result = bytearray(length + 4)  # 2 bytes pre, 2 bytes crc
            i2c.readinto(result)
            # print("$%02X => %s" % (register, [hex(i) for i in result]))
            # Check preamble indicates correct readings
            if result[0] != 0x3 or result[1] != length:
                raise RuntimeError("I2C read failure")
            # Check CRC on all but last 2 bytes
            crc1 = struct.unpack("<H", bytes(result[-2:]))[0]
            crc2 = _crc16(result[0:-2])
            if crc1 != crc2:
                raise RuntimeError("CRC failure 0x%04X vs 0x%04X" % (crc1, crc2))
            return result[2:-2]

    @property
    def temperature(self) -> float:
        """The measured temperature in Celsius."""
        temperature = struct.unpack(">H", self._read_register(AM2320_REG_TEMP_H, 2))[0]
        if temperature >= 32768:
            temperature = 32768 - temperature
        return temperature / 10.0

    @property
    def relative_humidity(self) -> float:
        """The measured relative humidity in percent."""
        humidity = struct.unpack(">H", self._read_register(AM2320_REG_HUM_H, 2))[0]
        return humidity / 10.0
