WIRING_RULES = {
    "dht11": {
        "vcc": "3V3",
        "gnd": "GND",
        "data": "GPIO4",
        "notes": "Requires 10k pull-up resistor on data line."
    },
    "dht22": {
        "vcc": "3V3",
        "gnd": "GND",
        "data": "GPIO4",
        "notes": "Same wiring as DHT11."
    },
    "pir": {
        "vcc": "5V",
        "gnd": "GND",
        "out": "GPIO14"
    },
    "ultrasonic": {
        "vcc": "5V",
        "gnd": "GND",
        "trig": "GPIO5",
        "echo": "GPIO18"
    },
    "tof-vl53l0x": {
        "vcc": "3V3",
        "gnd": "GND",
        "sda": "GPIO21",
        "scl": "GPIO22"
    },
    "microwave-radar": {
        "vcc": "5V",
        "gnd": "GND",
        "out": "GPIO27"
    },
    "laser-emitter": {
        "vcc": "5V",
        "gnd": "GND"
    },
    "laser-receiver": {
        "vcc": "5V",
        "gnd": "GND",
        "out": "GPIO34"
    },
    "oled-ssd1306": {
        "vcc": "3V3",
        "gnd": "GND",
        "sda": "GPIO21",
        "scl": "GPIO22"
    },
    "lcd1602": {
        "vcc": "5V",
        "gnd": "GND",
        "sda": "GPIO21",
        "scl": "GPIO22"
    },
    "rfid-rc522": {
        "vcc": "3V3",
        "gnd": "GND",
        "sck": "GPIO18",
        "mosi": "GPIO23",
        "miso": "GPIO19",
        "rst": "GPIO22",
        "ss": "GPIO5"
    },
}
