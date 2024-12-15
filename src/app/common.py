import os
import gc
from machine import Pin
import time
from micropython import const

LED = Pin(7, Pin.OUT, value=0)
BTN_DOWN = const(35)
BTN_UP = const(34)
INITIAL_WIFI_PASSWORD = "12345678"
DEVICE_NAME = const("NARMI000")


def blink_led(times, delay):

    for _ in range(times):
        LED.on()
        time.sleep_ms(delay)
        LED.off()
        time.sleep_ms(delay)


def check_both_buttons():
    # Check if both buttons are pressed
    button1 = Pin(34, Pin.IN, Pin.PULL_UP)
    button2 = Pin(35, Pin.IN, Pin.PULL_UP)
    if not button1.value() and not button2.value():
        print("Both buttons are pressed")
        return True
    return False


def get_flash_info():
    try:
        # Get filesystem stats
        stats = os.statvfs("/")

        # Calculate storage info in KB
        block_size = stats[0]  # Block size
        total_blocks = stats[2]  # Total blocks
        free_blocks = stats[3]  # Free blocks 3

        total_space = (block_size * total_blocks) / 1024  # Convert to KB
        free_space = (block_size * free_blocks) / 1024  # Convert to KB
        used_space = total_space - free_space

        # Get RAM info
        gc.collect()
        ram_free = gc.mem_free() / 1024  # Convert to KB
        ram_alloc = gc.mem_alloc() / 1024  # Convert to KB

        print("Flash Storage:")
        print(f"Total: {total_space:.2f}KB")
        print(f"Used: {used_space:.2f}KB")
        print(f"Free: {free_space:.2f}KB")
        print("\nRAM Memory:")
        print(f"Free: {ram_free:.2f}KB")
        print(f"Allocated: {ram_alloc:.2f}KB")

        # import uos
        # uos.VfsFat.mkfs(bdev)

    except Exception as e:
        print("Error getting storage info:", e)


def connectToWifiAndUpdate():
    print("Connecting to WiFi and checking for updates...")
    import time, machine, network, gc
    import app.secrets as secrets

    time.sleep(1)
    print("Memory free", gc.mem_free())

    from app.ota_updater import OTAUpdater

    sta_if = network.WLAN(network.STA_IF)
    if not sta_if.isconnected():
        print("connecting to network...")

        sta_if.active(True)
        sta_if.connect(secrets.WIFI_SSID, secrets.WIFI_PASSWORD)
        while not sta_if.isconnected():
            pass
    print("network config:", sta_if.ifconfig())
    otaUpdater = OTAUpdater(
        "https://github.com/sam0910/narmi000", main_dir="app", github_src_dir="src", secrets_file="secrets.py"
    )
    hasUpdated = otaUpdater.install_update_if_available()
    if hasUpdated:
        blink_led(6, 1000)
        machine.reset()
    else:
        del otaUpdater
        gc.collect()

        blink_led(6, 100)
        machine.reset()
