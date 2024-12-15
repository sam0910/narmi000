import os
import gc
from machine import Pin
import time
import app.common as common


# common.get_flash_info()
common.blink_led(5, 100)
check = common.check_both_buttons()
if check:
    print("No buttons are pressed")
    common.blink_led(1, 2000)
    from app.start import BLENarmi
    import bluetooth

    ble = bluetooth.BLE()
    narmi = BLENarmi(ble)
    narmi.start()
else:
    print("Both buttons are pressed, lets update the firmware")
    common.blink_led(4, 500)
    # active wifi sta mode
    import network

    sta_if = network.WLAN(network.STA_IF)
    sta_if.active(True)
    scans = sta_if.scan()
    print("scans:", scans)

    # Sort networks by RSSI (index 3 in scan result tuple)
    sorted_networks = sorted(scans, key=lambda x: x[3], reverse=True)
    if len(sorted_networks) > 0:
        # Try connecting to the 3 strongest networks
        for network_info in sorted_networks[:3]:
            if not sta_if.active():
                sta_if.active(True)
            ssid = network_info[0].decode("utf-8")
            print(f"Attempting to connect to network: {ssid}")
            sta_if.connect(ssid, common.INITIAL_WIFI_PASSWORD)

            # Wait for connection
            attempts = 0
            while not sta_if.isconnected() and attempts < 15:
                time.sleep_ms(500)
                attempts += 1

            if sta_if.isconnected():
                print("Connected! Network config:", sta_if.ifconfig())
                break
            else:
                print(f"Failed to connect to {ssid}, trying next network...")
                sta_if.active(False)
                time.sleep(0.2)

        if not sta_if.isconnected():
            print("Failed to connect networks w/ initial password", common.INITIAL_WIFI_PASSWORD)

    sta_if.active(False)
    time.sleep(0.2)
    common.connectToWifiAndUpdate()
