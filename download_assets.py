# download_assets.py
# Downloads MCU Lab images into /static/breadboard/

import os
import urllib.request

BASE = "static/breadboard"
BOARDS = f"{BASE}/boards"
COMP = f"{BASE}/components"

os.makedirs(BOARDS, exist_ok=True)
os.makedirs(COMP, exist_ok=True)

# -----------------------------
# CORE, HIGH-CONFIDENCE ASSETS
# -----------------------------
CORE_IMAGES = {
    # Boards
    f"{BOARDS}/esp32-devkit-v1.png":
        "https://raw.githubusercontent.com/wokwi/wokwi-assets/main/boards/esp32-devkit-v1.png",

    f"{BOARDS}/esp32-s3.png":
        "https://raw.githubusercontent.com/wokwi/wokwi-assets/main/boards/esp32-s3.png",

    f"{BOARDS}/esp8266.png":
        "https://raw.githubusercontent.com/wokwi/wokwi-assets/main/boards/esp8266-nodemcu.png",

    # Basic components
    f"{COMP}/led.png":
        "https://raw.githubusercontent.com/wokwi/wokwi-assets/main/components/led.png",

    f"{COMP}/resistor.png":
        "https://raw.githubusercontent.com/wokwi/wokwi-assets/main/components/resistor.png",

    f"{COMP}/button.png":
        "https://raw.githubusercontent.com/wokwi/wokwi-assets/main/components/pushbutton.png",

    # Sensors / modules
    f"{COMP}/dht11.png":
        "https://raw.githubusercontent.com/wokwi/wokwi-assets/main/components/dht11.png",

    f"{COMP}/dht22.png":
        "https://raw.githubusercontent.com/wokwi/wokwi-assets/main/components/dht22.png",

    f"{COMP}/pir.png":
        "https://raw.githubusercontent.com/wokwi/wokwi-assets/main/components/pir.png",

    f"{COMP}/ultrasonic.png":
        "https://raw.githubusercontent.com/wokwi/wokwi-assets/main/components/hc-sr04.png",

    f"{COMP}/oled-ssd1306.png":
        "https://raw.githubusercontent.com/wokwi/wokwi-assets/main/components/ssd1306.png",

    f"{COMP}/jumper-wire.png":
        "https://raw.githubusercontent.com/wokwi/wokwi-assets/main/components/jumper-wire.png",
}

# -----------------------------
# EXTENSION HOOK:
# Add more modules here as you decide to support them.
# Just follow the same pattern: path -> URL.
# -----------------------------
EXTRA_IMAGES = {
    # Examples (uncomment / adjust as you add support):
    # f"{COMP}/servo.png":
    #     "https://raw.githubusercontent.com/wokwi/wokwi-assets/main/components/servo.png",
    # f"{COMP}/relay.png":
    #     "https://raw.githubusercontent.com/wokwi/wokwi-assets/main/components/relay-module.png",
    # f"{COMP}/laser.png":
    #     "<YOUR_LASER_MODULE_IMAGE_URL>",
    # f"{COMP}/microwave-radar.png":
    #     "<YOUR_MICROWAVE_RADAR_SENSOR_IMAGE_URL>",
}

IMAGES = {}
IMAGES.update(CORE_IMAGES)
IMAGES.update(EXTRA_IMAGES)

print("\nDownloading MCU Lab assets...\n")

for path, url in IMAGES.items():
    print(f"Downloading {path} from {url}")
    try:
        urllib.request.urlretrieve(url, path)
        print("  ✔ Success")
    except Exception as e:
        print(f"  ✖ Failed: {e}")

print("\nDone.\n")
