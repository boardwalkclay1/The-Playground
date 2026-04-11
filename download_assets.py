# download_assets.py
# Downloads all MCU Lab images into /static/breadboard/

import os
import urllib.request

# -----------------------------
# TARGET FOLDERS
# -----------------------------
BASE = "static/breadboard"
BOARDS = f"{BASE}/boards"
COMP = f"{BASE}/components"

os.makedirs(BOARDS, exist_ok=True)
os.makedirs(COMP, exist_ok=True)

# -----------------------------
# IMAGE URLS (REALISTIC PHOTOS)
# These are stable, high-quality PNGs.
# -----------------------------
IMAGES = {
    # Boards
    f"{BOARDS}/esp32-devkit-v1.png":
        "https://raw.githubusercontent.com/wokwi/wokwi-assets/main/boards/esp32-devkit-v1.png",

    f"{BOARDS}/esp32-s3.png":
        "https://raw.githubusercontent.com/wokwi/wokwi-assets/main/boards/esp32-s3.png",

    f"{BOARDS}/esp8266.png":
        "https://raw.githubusercontent.com/wokwi/wokwi-assets/main/boards/esp8266-nodemcu.png",

    # Components
    f"{COMP}/led.png":
        "https://raw.githubusercontent.com/wokwi/wokwi-assets/main/components/led.png",

    f"{COMP}/resistor.png":
        "https://raw.githubusercontent.com/wokwi/wokwi-assets/main/components/resistor.png",

    f"{COMP}/button.png":
        "https://raw.githubusercontent.com/wokwi/wokwi-assets/main/components/pushbutton.png",

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
# DOWNLOAD
# -----------------------------
print("\nDownloading MCU Lab assets...\n")

for path, url in IMAGES.items():
    print(f"Downloading {path}...")
    try:
        urllib.request.urlretrieve(url, path)
        print("  ✔ Success")
    except Exception as e:
        print(f"  ✖ Failed: {e}")

print("\nAll done!\n")
