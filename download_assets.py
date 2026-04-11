# download_assets.py
# Downloads ALL MCU Lab images into /static/breadboard/

import os
import urllib.request

BASE = "static/breadboard"
BOARDS = f"{BASE}/boards"
COMP = f"{BASE}/components"

os.makedirs(BOARDS, exist_ok=True)
os.makedirs(COMP, exist_ok=True)

# -----------------------------
# MASTER IMAGE MAP
# -----------------------------
IMAGES = {
    # -------------------------
    # BOARDS
    # -------------------------
    f"{BOARDS}/esp32-devkit-v1.png":
        "https://raw.githubusercontent.com/wokwi/wokwi-assets/main/boards/esp32-devkit-v1.png",

    f"{BOARDS}/esp32-s3.png":
        "https://raw.githubusercontent.com/wokwi/wokwi-assets/main/boards/esp32-s3.png",

    f"{BOARDS}/esp8266.png":
        "https://raw.githubusercontent.com/wokwi/wokwi-assets/main/boards/esp8266-nodemcu.png",

    # -------------------------
    # BASIC COMPONENTS
    # -------------------------
    f"{COMP}/led.png":
        "https://raw.githubusercontent.com/wokwi/wokwi-assets/main/components/led.png",

    f"{COMP}/resistor.png":
        "https://raw.githubusercontent.com/wokwi/wokwi-assets/main/components/resistor.png",

    f"{COMP}/button.png":
        "https://raw.githubusercontent.com/wokwi/wokwi-assets/main/components/pushbutton.png",

    f"{COMP}/potentiometer.png":
        "https://raw.githubusercontent.com/wokwi/wokwi-assets/main/components/potentiometer.png",

    f"{COMP}/buzzer.png":
        "https://raw.githubusercontent.com/wokwi/wokwi-assets/main/components/buzzer.png",

    f"{COMP}/relay.png":
        "https://raw.githubusercontent.com/wokwi/wokwi-assets/main/components/relay-module.png",

    f"{COMP}/servo.png":
        "https://raw.githubusercontent.com/wokwi/wokwi-assets/main/components/servo.png",

    f"{COMP}/stepper-driver.png":
        "https://raw.githubusercontent.com/wokwi/wokwi-assets/main/components/a4988.png",

    # -------------------------
    # ENVIRONMENTAL SENSORS
    # -------------------------
    f"{COMP}/dht11.png":
        "https://raw.githubusercontent.com/wokwi/wokwi-assets/main/components/dht11.png",

    f"{COMP}/dht22.png":
        "https://raw.githubusercontent.com/wokwi/wokwi-assets/main/components/dht22.png",

    f"{COMP}/bme280.png":
        "https://raw.githubusercontent.com/wokwi/wokwi-assets/main/components/bme280.png",

    f"{COMP}/bmp280.png":
        "https://raw.githubusercontent.com/wokwi/wokwi-assets/main/components/bmp280.png",

    f"{COMP}/mq2.png":
        "https://raw.githubusercontent.com/wokwi/wokwi-assets/main/components/mq2.png",

    f"{COMP}/mq135.png":
        "https://raw.githubusercontent.com/wokwi/wokwi-assets/main/components/mq135.png",

    f"{COMP}/soil-moisture.png":
        "https://raw.githubusercontent.com/wokwi/wokwi-assets/main/components/soil-moisture.png",

    f"{COMP}/water-level.png":
        "https://raw.githubusercontent.com/wokwi/wokwi-assets/main/components/water-level.png",

    f"{COMP}/rain-sensor.png":
        "https://raw.githubusercontent.com/wokwi/wokwi-assets/main/components/rain-sensor.png",

    # -------------------------
    # MOTION / DISTANCE / LIGHT
    # -------------------------
    f"{COMP}/pir.png":
        "https://raw.githubusercontent.com/wokwi/wokwi-assets/main/components/pir.png",

    f"{COMP}/ultrasonic.png":
        "https://raw.githubusercontent.com/wokwi/wokwi-assets/main/components/hc-sr04.png",

    f"{COMP}/tof-vl53l0x.png":
        "https://raw.githubusercontent.com/wokwi/wokwi-assets/main/components/vl53l0x.png",

    f"{COMP}/ir-obstacle.png":
        "https://raw.githubusercontent.com/wokwi/wokwi-assets/main/components/ir-obstacle.png",

    f"{COMP}/ldr.png":
        "https://raw.githubusercontent.com/wokwi/wokwi-assets/main/components/ldr.png",

    # -------------------------
    # SPECIALTY SENSORS
    # -------------------------
    f"{COMP}/microwave-radar.png":
        "https://raw.githubusercontent.com/wokwi/wokwi-assets/main/components/rcwl-0516.png",

    f"{COMP}/laser-emitter.png":
        "https://raw.githubusercontent.com/wokwi/wokwi-assets/main/components/laser-emitter.png",

    f"{COMP}/laser-receiver.png":
        "https://raw.githubusercontent.com/wokwi/wokwi-assets/main/components/laser-receiver.png",

    f"{COMP}/flame-sensor.png":
        "https://raw.githubusercontent.com/wokwi/wokwi-assets/main/components/flame-sensor.png",

    f"{COMP}/sound-sensor.png":
        "https://raw.githubusercontent.com/wokwi/wokwi-assets/main/components/sound-sensor.png",

    f"{COMP}/vibration-sensor.png":
        "https://raw.githubusercontent.com/wokwi/wokwi-assets/main/components/vibration-sensor.png",

    f"{COMP}/hall-sensor.png":
        "https://raw.githubusercontent.com/wokwi/wokwi-assets/main/components/hall-sensor.png",

    # -------------------------
    # DISPLAYS
    # -------------------------
    f"{COMP}/oled-ssd1306.png":
        "https://raw.githubusercontent.com/wokwi/wokwi-assets/main/components/ssd1306.png",

    f"{COMP}/lcd1602.png":
        "https://raw.githubusercontent.com/wokwi/wokwi-assets/main/components/lcd1602.png",

    f"{COMP}/lcd2004.png":
        "https://raw.githubusercontent.com/wokwi/wokwi-assets/main/components/lcd2004.png",

    f"{COMP}/tft18.png":
        "https://raw.githubusercontent.com/wokwi/wokwi-assets/main/components/tft18.png",

    # -------------------------
    # COMMUNICATION MODULES
    # -------------------------
    f"{COMP}/nrf24l01.png":
        "https://raw.githubusercontent.com/wokwi/wokwi-assets/main/components/nrf24l01.png",

    f"{COMP}/lora-sx1278.png":
        "https://raw.githubusercontent.com/wokwi/wokwi-assets/main/components/sx1278.png",

    f"{COMP}/hc05.png":
        "https://raw.githubusercontent.com/wokwi/wokwi-assets/main/components/hc05.png",

    f"{COMP}/esp01.png":
        "https://raw.githubusercontent.com/wokwi/wokwi-assets/main/components/esp01.png",

    f"{COMP}/rfid-rc522.png":
        "https://raw.githubusercontent.com/wokwi/wokwi-assets/main/components/rc522.png",

    # -------------------------
    # POWER MODULES
    # -------------------------
    f"{COMP}/buck.png":
        "https://raw.githubusercontent.com/wokwi/wokwi-assets/main/components/buck.png",

    f"{COMP}/boost.png":
        "https://raw.githubusercontent.com/wokwi/wokwi-assets/main/components/boost.png",

    f"{COMP}/battery-holder.png":
        "https://raw.githubusercontent.com/wokwi/wokwi-assets/main/components/battery-holder.png",

    f"{COMP}/solar-panel.png":
        "https://raw.githubusercontent.com/wokwi/wokwi-assets/main/components/solar-panel.png",
}

# -----------------------------
# DOWNLOAD
# -----------------------------
print("\nDownloading ALL MCU Lab assets...\n")

for path, url in IMAGES.items():
    print(f"Downloading {path}...")
    try:
        urllib.request.urlretrieve(url, path)
        print("  ✔ Success")
    except Exception as e:
        print(f"  ✖ Failed: {e}")

print("\nALL DONE — Your MCU Lab now supports EVERYTHING.\n")
