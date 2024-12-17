"""Tests for the unittest module. v0.0.0"""

"""
async def start_indicating(self):
        consecutive_failures = 0
        while True:
            await asyncio.sleep_ms(self.SLEEP_FOR_MS)

            if len(self._connections) == 0:
                continue

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

            except Exception as e:
                print("Error in start_indicating loop:", e)
                sys.print_exception(e)
                await asyncio.sleep_ms(1000)  # Wait before retrying
"""
