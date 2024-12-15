"""
{Andre Peeters 2017/10/31}<https://github.com/andrethemac/max17043.py/tree/master>

Description: This is a Micropython library for the MAX17043/17044 LiPo fuel gauge.  
Creation date: 2017/10/31
Modification date:
Version: 1.0
Dependencies: binascii, machine
modified by: @Cesar
"""

from machine import Pin, SoftI2C
import binascii
from micropython import const


class max1704x:
    REGISTER_VCELL = const(0x02)
    REGISTER_SOC = const(0x04)
    REGISTER_MODE = const(0x06)
    REGISTER_VERSION = const(0x08)
    REGISTER_CONFIG = const(0x0C)
    REGISTER_COMMAND = const(0xFE)

    def __init__(self, i2c):
        """
        Initializes the I2C connection and checks for sensor presence.
        """
        try:
            self.i2c = i2c
            self.max1704xAddress = 0x36

            # Validate sensor presence and version
            if not self.sensor_exists():
                raise ValueError("MAX1704X not detected")

            version = self.getVersion()
            if version == 0 or version == 65535:  # Invalid version numbers
                raise ValueError("Invalid sensor version")

        except Exception as e:
            raise ValueError(f"Failed to initialize MAX1704X: {str(e)}")

    def __str__(self):
        """
        String representation of the values.
        """
        rs = "The I2C address is {}\n".format(self.max1704xAddress)
        rs += "The I2C pins are SDA: {} and SCL: {}\n".format(self.sda_pin, self.scl_pin)
        rs += "The version is {}\n".format(self.getVersion())
        rs += "VCell is {} V\n".format(self.getVCell())
        rs += "Compensate value is {}\n".format(self.getCompensateValue())
        rs += "The alert threshold is {} %\n".format(self.getAlertThreshold())
        rs += "Is it in alert? {}\n".format(self.inAlert())
        return rs

    def sensor_exists(self):
        """
        Checks if the sensor responds at the expected I2C address.
        """
        try:
            # Try to read version register
            data = self.i2c.readfrom_mem(self.max1704xAddress, self.REGISTER_VERSION, 2)
            return len(data) == 2
        except:
            return False

    def address(self):
        """
        Returns the I2C address.
        """
        return self.max1704xAddress

    def reset(self):
        """
        Resets the sensor.
        """
        self.__writeRegister(REGISTER_COMMAND, binascii.unhexlify("0054"))

    def getVCell(self):
        """
        Gets the remaining volts in the cell.
        """
        buf = self.__readRegister(REGISTER_VCELL)
        return (buf[0] << 4 | buf[1] >> 4) / 1000.0

    def getSoc(self):
        """
        Gets the state of charge.
        """
        buf = self.__readRegister(REGISTER_SOC)
        return buf[0] + (buf[1] / 256.0)

    def getVersion(self):
        """
        Gets the version of the max17043 module.
        """
        buf = self.__readRegister(REGISTER_VERSION)
        return (buf[0] << 8) | (buf[1])

    def getCompensateValue(self):
        """
        Gets the compensation value.
        """
        return self.__readConfigRegister()[0]

    def getAlertThreshold(self):
        """
        Gets the alert level.
        """
        return 32 - (self.__readConfigRegister()[1] & 0x1F)

    def setAlertThreshold(self, threshold):
        """
        Sets the alert level.
        """
        self.threshold = 32 - threshold if threshold < 32 else 32
        buf = self.__readConfigRegister()
        buf[1] = (buf[1] & 0xE0) | self.threshold
        self.__writeConfigRegister(buf)

    def inAlert(self):
        """
        Checks if the max17043 module is in alert.
        """
        return (self.__readConfigRegister())[1] & 0x20

    def clearAlert(self):
        """
        Clears the alert.
        """
        self.__readConfigRegister()

    def quickStart(self):
        """
        Performs a quick reset.
        """
        self.__writeRegister(REGISTER_MODE, binascii.unhexlify("4000"))

    def __readRegister(self, address):
        """
        Reads the register at the specified address, always returns a 2-byte bytearray.
        """
        return self.i2c.readfrom_mem(self.max1704xAddress, address, 2)

    def __readConfigRegister(self):
        """
        Reads the configuration register, always returns a 2-byte bytearray.
        """
        return self.__readRegister(REGISTER_CONFIG)

    def __writeRegister(self, address, buf):
        """
        Writes the buf to the register address.
        """
        self.i2c.writeto_mem(self.max1704xAddress, address, buf)

    def __writeConfigRegister(self, buf):
        """
        Writes the buf to the configuration register.
        """
        self.__writeRegister(REGISTER_CONFIG, buf)

    def deinit(self):
        """
        Turns off the peripheral.
        """
        self.i2c.deinit()


if __name__ == "__main__":

    my_sensor = max1704x()

    # Get the I2C address of the sensor
    print("I2C address of the sensor:", my_sensor.address())

    # Get the version of the max1704x module
    print("Module version:", my_sensor.getVersion())

    # Get the remaining voltage in the cell
    print("Remaining cell voltage (V):", my_sensor.getVCell())

    # Get the state of charge
    print("State of charge (%):", my_sensor.getSoc())

    # Get the compensation value
    print("Compensation value:", my_sensor.getCompensateValue())

    # Get the alert threshold
    print("Alert threshold (%):", my_sensor.getAlertThreshold())

    # Check if the sensor is in alert
    print("Is in alert?:", "Yes" if my_sensor.inAlert() else "No")

    # Perform a quick start reset of the sensor
    my_sensor.quickStart()
