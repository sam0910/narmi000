print("Version 0.0.2 by local update")

from machine import Pin, time_pulse_us, lightsleep, freq, SoftI2C
import uasyncio as asyncio
from micropython import const
import bluetooth
import random
import struct
import time
import json
import gc
import sys
import binascii
from app.aioble.ble_advertising import advertising_payload
from app.sensor.distance import HCSR04
from app.driver.iqsbuttons import IQSButtons
import app.common as common
from app.sensor.sht40.sht4xmod import SHT4xSensirion
from app.sensor.sht40.bus_service import I2cAdapter
from app.sensor.max17048 import max1704x
from calibration import CALIB_TEMP, CALIB_HUMIDITY

DEVICE_NAME = const("NARMI000")
BTN_DOWN = const(34)
BTN_UP = const(35)

_IRQ_CENTRAL_CONNECT = const(1)
_IRQ_CENTRAL_DISCONNECT = const(2)
_IRQ_GATTS_INDICATE_DONE = const(20)
_IRQ_ENCRYPTION_UPDATE = const(28)
_IRQ_PASSKEY_ACTION = const(31)
_IRQ_GET_SECRET = const(29)
_IRQ_SET_SECRET = const(30)
_FLAG_READ = const(0x0002)
_FLAG_NOTIFY = const(0x0010)
_FLAG_INDICATE = const(0x0020)
_FLAG_READ_ENCRYPTED = const(0x0200)

# org.bluetooth.service.environmental_sensing
_ENV_SENSE_UUID = bluetooth.UUID(0x181A)
# org.bluetooth.characteristic.temperature
_TEMP_CHAR = (
    bluetooth.UUID(0x2A6E),
    _FLAG_READ | _FLAG_NOTIFY | _FLAG_INDICATE | _FLAG_READ_ENCRYPTED,
)
# Custom UUID for distance
_DISTANCE_CHAR_UUID = bluetooth.UUID(0x2A5B)
_DISTANCE_CHAR = (
    _DISTANCE_CHAR_UUID,
    _FLAG_READ | _FLAG_NOTIFY | _FLAG_INDICATE | _FLAG_READ_ENCRYPTED,
)
# Custom UUID for interval - using Time Interval characteristic
_INTERVAL_CHAR_UUID = bluetooth.UUID(0x2A24)
_INTERVAL_CHAR = (
    _INTERVAL_CHAR_UUID,
    _FLAG_READ | _FLAG_NOTIFY | _FLAG_INDICATE | _FLAG_READ_ENCRYPTED,
)
# org.bluetooth.characteristic.humidity
_HUMIDITY_CHAR_UUID = bluetooth.UUID(0x2A6F)
_HUMIDITY_CHAR = (
    _HUMIDITY_CHAR_UUID,
    _FLAG_READ | _FLAG_NOTIFY | _FLAG_INDICATE | _FLAG_READ_ENCRYPTED,
)
# org.bluetooth.service.battery_service
_BATT_SVC_UUID = bluetooth.UUID(0x180F)
# org.bluetooth.characteristic.battery_level
_BATT_LVL_UUID = bluetooth.UUID(0x2A19)
_BATT_CHAR = (
    _BATT_LVL_UUID,
    _FLAG_READ | _FLAG_NOTIFY | _FLAG_INDICATE | _FLAG_READ_ENCRYPTED,
)
# org.bluetooth.characteristic.battery_voltage (custom UUID using 0x2B18)
_BATT_VOLT_UUID = bluetooth.UUID(0x2B18)
_BATT_VOLT_CHAR = (
    _BATT_VOLT_UUID,
    _FLAG_READ | _FLAG_NOTIFY | _FLAG_INDICATE | _FLAG_READ_ENCRYPTED,
)
_ENV_SENSE_SERVICE = (
    _ENV_SENSE_UUID,
    (
        _TEMP_CHAR,
        _DISTANCE_CHAR,
        _INTERVAL_CHAR,
        _HUMIDITY_CHAR,
    ),
)
_SERVICES = (
    _ENV_SENSE_SERVICE,
    (
        _BATT_SVC_UUID,
        (
            _BATT_CHAR,
            _BATT_VOLT_CHAR,
        ),
    ),
)
# org.bluetooth.characteristic.gap.appearance.xml
_ADV_APPEARANCE_GENERIC_THERMOMETER = const(768)
_IO_CAPABILITY_DISPLAY_ONLY = const(0)
_IO_CAPABILITY_DISPLAY_YESNO = const(1)
_IO_CAPABILITY_KEYBOARD_ONLY = const(2)
_IO_CAPABILITY_NO_INPUT_OUTPUT = const(3)
_IO_CAPABILITY_KEYBOARD_DISPLAY = const(4)
_PASSKEY_ACTION_INPUT = const(2)
_PASSKEY_ACTION_DISP = const(3)
_PASSKEY_ACTION_NUMCMP = const(4)
_ADDR_MODE = 0x00
# 0x00 - PUBLIC - Use the controller’s public address.
# 0x01 - RANDOM - Use a generated static address.
# 0x02 - RPA - Use resolvable private addresses.
# 0x03 - NRPA - Use non-resolvable private addresses.

freq(240_000_000)
gc.collect()
gc.enable()


def i2c_retry(retries=3, delay_ms=100):
    def decorator(func):
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(retries):
                try:
                    return func(*args, **kwargs)
                except OSError as e:
                    last_exception = e
                    print(f"I2C operation failed, attempt {attempt + 1}/{retries}")
                    time.sleep_ms(delay_ms)
            print(f"I2C operation failed after {retries} attempts")
            return None

        return wrapper

    return decorator


class BLENarmi:
    def __init__(self, ble, name=DEVICE_NAME):
        self._ble = ble
        self.loop = asyncio.get_event_loop()
        # self.btns = IQSButtons(self.btn_cb, 35, 34, loop=self.loop)
        self._name = name
        self.t = 25
        self._load_secrets()
        self._ble.irq(self._irq)
        self._ble.config(bond=True)
        self._ble.config(le_secure=True)
        self._ble.config(mitm=True)
        self._ble.config(io=_IO_CAPABILITY_NO_INPUT_OUTPUT)
        self._ble.active(True)
        self._ble.config(addr_mode=_ADDR_MODE)
        self.distance = HCSR04()
        self.INTERVAL_MS = 1000
        self.INTERVAL_GAP = 0
        self.pending_sleep = 0
        self.led = Pin(7, Pin.OUT, value=0)

        # Initialize SHT40 sensor
        self.i2c = SoftI2C(scl=Pin(22), sda=Pin(21), freq=100000)
        try:
            adaptor = I2cAdapter(self.i2c)
            self.sht = SHT4xSensirion(adaptor, address=0x44, check_crc=True)
            self.sht_available = True
        except Exception as e:
            print("SHT40 sensor init failed:", e)
            self.sht = None
            self.sht_available = False

        # Initialize battery sensor with better error handling
        self.battery = None
        try:
            self.battery = max1704x(self.i2c)
            # Test read to verify sensor is working
            soc, vcell = self.read_battery()
            if soc is None or vcell is None:
                raise ValueError("Battery sensor test read failed")
            print(f"Battery sensor initialized: SOC={soc}%, Voltage={vcell}V")
        except Exception as e:
            print("Battery sensor initialization failed:", e)
            self.battery = None

        # Update service registration to include battery service
        (
            (self._temp_handle, self._distance_handle, self._interval_handle, self._humidity_handle),
            (self._batt_level_handle, self._batt_volt_handle),
        ) = self._ble.gatts_register_services(_SERVICES)

        self._connections = set()
        self._payload = advertising_payload(
            name=name, services=[_ENV_SENSE_UUID], appearance=_ADV_APPEARANCE_GENERIC_THERMOMETER
        )
        self._pending_indications = {}  # Track pending indications
        print("BLE Device initialized and ready to advertise")
        self._advertise()

    def _irq(self, event, data):
        # Track connections so we can send notifications.
        if event == _IRQ_CENTRAL_CONNECT:
            conn_handle, _, _ = data
            print("\nConnected to central device")
            self._connections.add(conn_handle)
            # Send initial interval value when device connects
            self.set_interval(self.INTERVAL_MS, indicate=True)
        elif event == _IRQ_CENTRAL_DISCONNECT:
            conn_handle, _, _ = data
            print("\nDisconnected from central device")
            self._connections.remove(conn_handle)
            self._save_secrets()
            print("Starting advertising again...")
            self._advertise()
        elif event == _IRQ_ENCRYPTION_UPDATE:
            conn_handle, encrypted, authenticated, bonded, key_size = data
            print("encryption update", conn_handle, encrypted, authenticated, bonded, key_size)
        elif event == _IRQ_PASSKEY_ACTION:
            conn_handle, action, passkey = data
            print("passkey action", conn_handle, action, passkey)
            if action == _PASSKEY_ACTION_NUMCMP:
                accept = 1  # int(input("accept? "))
                self._ble.gap_passkey(conn_handle, action, accept)
            elif action == _PASSKEY_ACTION_DISP:
                print("displaying 1234")
                self._ble.gap_passkey(conn_handle, action, 1234)
            elif action == _PASSKEY_ACTION_INPUT:
                print("prompting for passkey")
                # passkey = int(input("passkey? "))
                self._ble.gap_passkey(conn_handle, action, passkey)
            else:
                print("unknown action")
        elif event == _IRQ_GATTS_INDICATE_DONE:
            conn_handle, value_handle, status = data
            if status == 0:
                if self.pending_sleep == 0:
                    self.pending_sleep = time.ticks_ms()
                print(f" -> Indication confirmed (handle: {conn_handle})", self.pending_sleep)

            else:
                print(f"Indication failed (handle: {conn_handle}, status: {status})")
            if conn_handle in self._pending_indications:
                del self._pending_indications[conn_handle]
        elif event == _IRQ_SET_SECRET:
            sec_type, key, value = data
            key = sec_type, bytes(key)
            value = bytes(value) if value else None
            print("set secret:", key, value)
            if value is None:
                if key in self._secrets:
                    del self._secrets[key]
                    return True
                else:
                    return False
            else:
                self._secrets[key] = value
            return True
        elif event == _IRQ_GET_SECRET:
            sec_type, index, key = data
            print("get secret:", sec_type, index, bytes(key) if key else None)
            if key is None:
                i = 0
                for (t, _key), value in self._secrets.items():
                    if t == sec_type:
                        if i == index:
                            return value
                        i += 1
                return None
            else:
                key = sec_type, bytes(key)
                return self._secrets.get(key, None)

    def btn_cb(self, args):
        btn = args[0]
        type = args[1]
        print("     [BTN_CB],", btn, type)
        if btn == 2 and type == 1:
            self.INTERVAL_MS = self.INTERVAL_MS + 1000
            print("     [INTERVAL_MS],", self.INTERVAL_MS)
            self.set_interval(self.INTERVAL_MS, indicate=True)
        elif btn == 1 and type == 1 and self.INTERVAL_MS > 1000:
            self.INTERVAL_MS = self.INTERVAL_MS - 1000
            print("     [INTERVAL_MS],", self.INTERVAL_MS)
            self.set_interval(self.INTERVAL_MS, indicate=True)

    def set_temperature(self, temp_deg_c, notify=False, indicate=False):
        # Write the local value, ready for a central to read.
        self._ble.gatts_write(self._temp_handle, struct.pack("<h", int(temp_deg_c * 100)))
        if notify or indicate:
            for conn_handle in self._connections:
                if notify:
                    self._ble.gatts_notify(conn_handle, self._temp_handle)
                    print("- Sending TEMPERATURE notify")
                if indicate:
                    self._pending_indications[conn_handle] = time.ticks_ms()
                    self._ble.gatts_indicate(conn_handle, self._temp_handle)
                    print(f"- Sending TEMPERATURE indication (handle: {conn_handle})")

    def measure_distance(self):
        return self.distance.measure_distance_cm()

    def set_distance(self, distance_cm, notify=False, indicate=False):
        # Pack distance as uint16 in mm
        self._ble.gatts_write(self._distance_handle, struct.pack("<H", int(distance_cm * 10)))
        if notify or indicate:
            for conn_handle in self._connections:
                if notify:
                    self._ble.gatts_notify(conn_handle, self._distance_handle)
                if indicate:
                    self._pending_indications[conn_handle] = time.ticks_ms()
                    self._ble.gatts_indicate(conn_handle, self._distance_handle)
                    print(f"- Sending DISTANCE indication (handle: {conn_handle})")

    # Add new method to set interval
    def set_interval(self, interval_ms, notify=False, indicate=False):
        self._ble.gatts_write(self._interval_handle, struct.pack("<I", interval_ms))
        if notify or indicate:
            for conn_handle in self._connections:
                if notify:
                    self._ble.gatts_notify(conn_handle, self._interval_handle)
                if indicate:
                    self._pending_indications[conn_handle] = time.ticks_ms()
                    self._ble.gatts_indicate(conn_handle, self._interval_handle)
                    print(f"- Sending INTERVAL indication (handle: {conn_handle})")

    def set_humidity(self, humidity, notify=False, indicate=False):
        # Write humidity value (scaled by 100 to preserve 2 decimal places)
        self._ble.gatts_write(self._humidity_handle, struct.pack("<H", int(humidity * 100)))
        if notify or indicate:
            for conn_handle in self._connections:
                if notify:
                    self._ble.gatts_notify(conn_handle, self._humidity_handle)
                if indicate:
                    self._pending_indications[conn_handle] = time.ticks_ms()
                    self._ble.gatts_indicate(conn_handle, self._humidity_handle)
                    print(f"- Sending HUMIDITY indication (handle: {conn_handle})")

    def set_battery_level(self, level, notify=False, indicate=False):
        """Set battery level (0-100%)"""
        self._ble.gatts_write(self._batt_level_handle, struct.pack("<B", int(level)))
        if notify or indicate:
            for conn_handle in self._connections:
                if notify:
                    self._ble.gatts_notify(conn_handle, self._batt_level_handle)
                if indicate:
                    self._pending_indications[conn_handle] = time.ticks_ms()
                    self._ble.gatts_indicate(conn_handle, self._batt_level_handle)
                    print(f"- Sending BATTERY LEVEL indication (handle: {conn_handle})")

    def set_battery_voltage(self, voltage, notify=False, indicate=False):
        """Set battery voltage (in mV)"""
        self._ble.gatts_write(self._batt_volt_handle, struct.pack("<H", int(voltage * 1000)))
        if notify or indicate:
            for conn_handle in self._connections:
                if notify:
                    self._ble.gatts_notify(conn_handle, self._batt_volt_handle)
                if indicate:
                    self._pending_indications[conn_handle] = time.ticks_ms()
                    self._ble.gatts_indicate(conn_handle, self._batt_volt_handle)
                    print(f"- Sending BATTERY VOLTAGE indication (handle: {conn_handle})")

    def read_battery(self):
        """Read battery values from MAX17048 with better error handling"""
        if not self.battery:
            return None, None

        try:
            soc = self.battery.getSoc()
            vcell = self.battery.getVCell()

            # # Validate readings are within reasonable ranges
            # if not (0 <= soc <= 100 and 2.5 <= vcell <= 4.5):
            #     print("Battery readings out of valid range")
            #     return None, None
            print("     Battery SOC: ", soc, "VCell: ", vcell)
            return soc, vcell
        except Exception as e:
            print("Battery read error:", e)

            print(sys.print_exception(e))
            self.battery = None  # Mark sensor as failed
            return None, None

    @i2c_retry(retries=3, delay_ms=100)
    def read_sht40(self):
        """Read temperature and humidity with retry logic"""
        if not self.sht_available:
            return None, None

        try:
            self.sht.start_measurement(with_heater=False, value=2)
            time.sleep_us(self.sht.get_conversion_cycle_time())
            results = self.sht.get_measurement_value()
            if results:
                temp, humidity = results
                # Validate readings are within reasonable ranges
                if -40 <= temp <= 125 and 0 <= humidity <= 100:
                    temp = temp + CALIB_TEMP
                    humidity = humidity + CALIB_HUMIDITY
                    print("     Temperature: ", temp, "Humidity: ", humidity)
                    return temp, humidity
                else:
                    print("Invalid sensor readings detected")
                    return None, None
            return None, None
        except Exception as e:
            print("SHT40 read error:", e)
            return None, None

    def _advertise(self, interval_us=200000):
        mac = self._ble.config("mac")
        mac_address_str = ":".join([f"{b:02x}" for b in mac[1]])
        print("\nStarting BLE advertising with address:", mac_address_str)
        self._payload = advertising_payload(
            name=self._name, services=[_ENV_SENSE_UUID], appearance=_ADV_APPEARANCE_GENERIC_THERMOMETER
        )
        self._ble.gap_advertise(interval_us, adv_data=self._payload)
        self.blink_led(1, 400)

    def blink_led(self, times, delay):

        for _ in range(times):
            self.led.on()
            time.sleep_ms(delay)
            self.led.off()
            time.sleep_ms(delay)

    def _reset_secrets(self):
        self._secrets = []
        self._save_secrets()

    def _load_secrets(self):
        self._secrets = {}
        try:
            with open("secrets.json", "r") as f:
                entries = json.load(f)
                for sec_type, key, value in entries:
                    self._secrets[sec_type, binascii.a2b_base64(key)] = binascii.a2b_base64(value)
        except:
            print("no secrets available")

    def _save_secrets(self):
        try:
            with open("secrets.json", "w") as f:
                json_secrets = [
                    (sec_type, binascii.b2a_base64(key), binascii.b2a_base64(value))
                    for (sec_type, key), value in self._secrets.items()
                ]
                json.dump(json_secrets, f)
        except:
            print("failed to save secrets")

    async def update_temperature(self):
        consecutive_failures = 0
        while True:
            try:
                temp, humidity = self.read_sht40()
                if temp is not None:
                    consecutive_failures = 0
                    self.set_temperature(temp, notify=False, indicate=True)
                    self.set_humidity(humidity, notify=False, indicate=True)
                else:
                    consecutive_failures += 1
                    print(f"Failed to read SHT40 ({consecutive_failures} times)")
                    if consecutive_failures >= 5:
                        print("Too many consecutive failures, reinitializing SHT40")
                        # Try to reinitialize the sensor
                        try:
                            adaptor = I2cAdapter(self.i2c)
                            self.sht = SHT4xSensirion(adaptor, address=0x44, check_crc=True)
                            self.sht_available = True
                            consecutive_failures = 0
                        except Exception as e:
                            print("SHT40 reinitialization failed:", e)
                            self.sht_available = False

                # Rest of the sensor readings
                distance = self.measure_distance()
                self.set_distance(distance, notify=False, indicate=True)

                batt_level, batt_voltage = self.read_battery()
                if batt_level is not None:
                    self.set_battery_level(batt_level, notify=False, indicate=True)
                    # self.set_battery_voltage(batt_voltage, notify=False, indicate=True)

                await asyncio.sleep_ms(self.INTERVAL_MS)
                await asyncio.sleep_ms(self.INTERVAL_GAP)
            except Exception as e:
                print("Error in update_temperature loop:", e)
                sys.print_exception(e)
                await asyncio.sleep_ms(1000)  # Wait before retrying

    async def check_buttons(self):
        while True:
            await asyncio.sleep_ms(500)
            print("Checking buttons", Pin(BTN_DOWN).value(), Pin(BTN_UP).value())

    async def go_sleep(self):
        while True:
            await asyncio.sleep_ms(500)
            if self.pending_sleep > 0:
                print("pending_sleep > 0", self.pending_sleep)
                after_pending_sleep = time.ticks_diff(time.ticks_ms(), self.pending_sleep)
                print(
                    f"after_pending_sleep({after_pending_sleep}) = time.ticks_diff(time.ticks_ms({time.ticks_ms()}), self.pending_sleep({self.pending_sleep}))"
                )
                print("after_pending_sleep", after_pending_sleep, ",sleeps for", self.INTERVAL_MS)
                if after_pending_sleep > 3000:
                    print("Going to sleep")
                    await asyncio.sleep_ms(100)

                    lightsleep(self.INTERVAL_MS)
                    self.pending_sleep = 0

    async def loops(self):
        temp_task = self.loop.create_task(self.update_temperature())
        self.loop.run_forever()

    def start(self):

        self.btns = IQSButtons(self.btn_cb, 35, 34, loop=self.loop)
        # temp_task = self.loop.create_task(self.check_buttons())
        # ps = self.loop.create_task(self.go_sleep())

        try:
            asyncio.run(self.loops())

        except KeyboardInterrupt:
            print("Interrupted")
            # dist_task.cancel()
        finally:
            self.loop.close()


if __name__ == "__main__":
    ble = bluetooth.BLE()
    temp = BLENarmi(ble)

    temp.start()
