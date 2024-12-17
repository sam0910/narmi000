import machine
import esp32

# Configure pins
btn1 = machine.Pin(34, machine.Pin.IN, machine.Pin.PULL_DOWN)
btn2 = machine.Pin(35, machine.Pin.IN, machine.Pin.PULL_DOWN)
esp32.wake_on_ext1(pins=(btn1, btn2), level=esp32.WAKEUP_ANY_HIGH)

# Enter deep sleep mode
print("Entering deep sleep...")
machine.deepsleep(10000)
