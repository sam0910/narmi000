"""SHT4x Sensirion module"""
import time
from machine import I2C, Pin
from sensor.sht40 import bus_service
from sensor.sht40.base_sensor import BaseSensorEx, IBaseSensorEx, check_value
from sensor.sht40.crc_mod import crc8
from sensor.sht40.bus_service import I2cAdapter

def _calc_crc(sequence) -> int:
    """Wrapper for short call."""
    return crc8(sequence, polynomial=0x31, init_value=0xFF)

class SHT4xSensirion(BaseSensorEx, IBaseSensorEx):
    """Class for work with Sensirion SHT4x sensor"""
    cmd_get_id = 0x89
    cmd_soft_reset = 0x94
    magic = -1 + 2 ** 16

    def __init__(self, adapter: bus_service.BusAdapter, address=0x44, check_crc: bool = True):
        """If check_crc is True, each data packet received from the sensor is verified 
        for correctness by calculating the checksum."""
        check_value(address, range(0x44, 0x47), f"Invalid device address: {address}")
        super().__init__(adapter, address, True)
        self._check_crc = check_crc
        self._last_cmd_code = None
        #
        self._with_heater = None
        self._value = None
        self._long_pulse = None
        #
        self._buf_1 = bytearray(1)
        self._buf_6 = bytearray(6)

    #@staticmethod
    #def get_answer_len(command_code: int) -> int:
    #    """Возвращает количество байт в ответе датчика"""
    #    if SHT4xSensirion.cmd_soft_reset == command_code:
    #        return 0
    #    return 6

    def get_last_cmd_code(self) -> int:
        """Returns the last command code sent to the sensor via the bus"""
        return self._last_cmd_code

    def _send_command(self, command_code: int):
        """Sends command to sensor via bus"""
        check_value(command_code, range(0x100), f"Invalid command code: {command_code}")
        _local = self._buf_1
        _local[0] = command_code
        self.write(_local)
        self._last_cmd_code = command_code

    def _read_answer(self) -> [bytes, None]:
        """Reads response to command sent by _send_command method.
        Returns reference to buffer with received data.
        Checks CRC"""
        _cmd = self.get_last_cmd_code()
        if SHT4xSensirion.cmd_soft_reset == _cmd:
            return None
        _buf = self._buf_6
        self.read_to_buf(_buf)
        # response read
        if self._check_crc:
            crc_from_buf = [_buf[i] for i in (2, 5)]  # list with CRC values
            calculated_crc = [_calc_crc(_buf[rng.start:rng.stop]) for rng in (range(2), range(3, 5))]
            if crc_from_buf != calculated_crc:
                raise ValueError(f"Invalid CRC! Calculated: {calculated_crc}. From buffer: {crc_from_buf};")
        return _buf

    def get_id(self) -> tuple[int, int]:
        _cmd = SHT4xSensirion.cmd_get_id
        self._send_command(_cmd)
        # This 'wonder-sensor' cannot immediately return its programmed number! Need to call sleep_us!
        time.sleep_us(110)
        _buf = self._read_answer()
        t = self.unpack("HBH", _buf)
        # discard CRC
        return t[0], t[2]

    def soft_reset(self):
        """Software reset of the sensor. After reset, sensor enters idle state!"""
        self._send_command(SHT4xSensirion.cmd_soft_reset)

    def get_conversion_cycle_time(self) -> int:
        """Returns conversion time in microseconds(!) for signal to digital code conversion 
        and its readiness for bus reading! For current sensor settings. 
        When settings change, this method should be called again!"""
        if not self._with_heater:   # work without heating!
            _val = self._value  # 0..2; 0 - low, 1 - medium, 2 - high repeatability/accuracy
            _ms = 1_600, 4_500, 8_300
            return _ms[_val]

        if self._long_pulse:    # work with heating!
            return 1_100_000
        # short heating pulse
        return 110_000

    def start_measurement(self, with_heater: bool = False, value: int = 0, long_pulse: bool = False):
        """Configures sensor parameters and starts measurement process.
        with_heater - if True, measurement will be done with heating (NOT normal mode)
        value - repeatability if with_heater is False:
            0       - low (lowest accuracy)
            1       - medium (medium accuracy) 
            2       - high (high accuracy)
        value - heater power if with_heater is True:
            0       -   20 mW
            1       -   110 mW 
            2       -   200 mW
        long_pulse - heating duration, used if with_heater is True:
            False   -   0.1 sec
            True    -   1.0 sec"""
        check_value(value, range(3), f"Invalid value: {value}")

        _cmd = None
        if not with_heater:
            # heater NOT used! 0xE0, 0xF6, 0xFD
            _t = 0xE0, 0xF6, 0xFD
            _cmd = _t[value]

        if with_heater:
            # heater used! (0x15, 0x1E), (0x24, 0x2F), (0x32, 0x39)
            _t = (0x15, 0x1E), (0x24, 0x2F), (0x32, 0x39)
            _cmd = _t[value][long_pulse]

        self._send_command(_cmd)
        # get_conversion_cycle_time
        self._with_heater = with_heater
        self._value = value
        self._long_pulse = long_pulse

    def get_measurement_value(self) -> [None, tuple[float, float]]:
        _cmd = self.get_last_cmd_code()
        if SHT4xSensirion.cmd_get_id == _cmd:
            return
        _buf = self._read_answer()
        _t = self.unpack("HBH", _buf)
        t = 175.0 * _t[0] / SHT4xSensirion.magic - 45.0    
        rh = 125.0 * _t[2] / SHT4xSensirion.magic - 6.0    
        return t, rh

    def is_single_shot_mode(self) -> bool:
        return True

    def is_continuously_mode(self) -> bool:
        return False

    # Iterator

    if __name__ == '__main__':
        from sensor.sht40.sht4xmod import SHT4xSensirion
        i2c = I2C(0, scl=Pin(22), sda=Pin(21), freq=100000)
        adaptor = I2cAdapter(i2c)
        # sensor
        sen = SHT4xSensirion(adaptor, address=0x44, check_crc=True)
        sid = sen.get_id()
        # sen.soft_reset()
        # time.sleep_ms(100)
        repeats = 3_000
        print(f"Sensor id: 0x{sid[0]:x}\t0x{sid[1]:x}")
        #
        # print("Working with sensor's built-in heater")
        # sen.start_measurement(with_heater=False, value=2, long_pulse=False)
        # wt = sen.get_conversion_cycle_time()
        # time.sleep_us(wt)
        # results = sen.get_measurement_value()
        # print("Results after heating!")
        # print(f"T: {results[0]}; RH: {results[1]}")
        #
        print("Results without heating!")
        for _ in range(repeats):
            sen.start_measurement(with_heater=False, value=2, long_pulse=False)
            wt = sen.get_conversion_cycle_time()
            time.sleep_us(wt)
            results = sen.get_measurement_value()
            print(f"T: {results[0]}; RH: {results[1]}")
            time.sleep_ms(500)	# to prevent IDE from hanging