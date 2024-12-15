"""
This is local version 0.0.0
"""


def connectToWifiAndUpdate():
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
        machine.reset()
    else:
        del otaUpdater
        gc.collect()


def startApp():
    import app.start


connectToWifiAndUpdate()
startApp()
