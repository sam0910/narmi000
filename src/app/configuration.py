from micropython import const

ENABLE_SLEEP = True  # Enable sleep mode

ADVERTIZING_LIMIT_MS = const(10_000)  # Advertising time in ms
SLEEP_TIME_S = const(5)  # Sleep Time in seconds
NO_INTERACTION = const(12_000)  # Time in ms to go to sleep if no interaction
INDICATE_TIMES = const(2)  # Number of times to indicate the sensor value per connection

DEVICE_NAME = const("NARMI000")  # Device name
BTN_DOWN = const(34)  # Pin number for button down
BTN_UP = const(35)  # Pin number for button up
