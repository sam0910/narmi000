./esptool-macos/esptool --chip esp32 --port $PORT --baud 460800 write_flash -z 0x1000 ESP32_GENERIC-SPIRAM-20241025-v1.24.0.bin