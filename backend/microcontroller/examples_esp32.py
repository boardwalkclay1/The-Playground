# backend/microcontroller/examples_esp32.py
from typing import Dict
from .templates import save_template, load_template


def _has_template(template_id: str) -> bool:
    return load_template(template_id) is not None


def ensure_esp32_examples_installed() -> None:
    examples: Dict[str, Dict[str, str]] = {
        "esp32-wifi-scan": {
            "main.ino": """#include <WiFi.h>

void setup() {
  Serial.begin(115200);
  delay(1000);
  Serial.println("ESP32 WiFi scan example");
  WiFi.mode(WIFI_STA);
  WiFi.disconnect();
  delay(100);

  int n = WiFi.scanNetworks();
  Serial.printf("Found %d networks\\n", n);
  for (int i = 0; i < n; ++i) {
    Serial.printf("%d: %s (%d dBm) %s\\n",
                  i + 1,
                  WiFi.SSID(i).c_str(),
                  WiFi.RSSI(i),
                  (WiFi.encryptionType(i) == WIFI_AUTH_OPEN) ? "open" : "secured");
  }
}

void loop() {
  delay(5000);
}
"""
        },
        "esp32-wifi-connect": {
            "main.ino": """#include <WiFi.h>

const char* ssid = "YOUR_SSID";
const char* password = "YOUR_PASSWORD";

void setup() {
  Serial.begin(115200);
  delay(1000);
  Serial.println("ESP32 WiFi connect example");

  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);

  Serial.print("Connecting");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println();
  Serial.print("Connected, IP address: ");
  Serial.println(WiFi.localIP());
}

void loop() {
}
"""
        },
        "esp32-ble-uart": {
            "main.ino": """#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <BLE2902.h>

BLEServer* pServer = nullptr;
BLECharacteristic* pTxCharacteristic;
bool deviceConnected = false;

#define SERVICE_UUID        "6E400001-B5A3-F393-E0A9-E50E24DCCA9E"
#define CHARACTERISTIC_UUID_RX "6E400002-B5A3-F393-E0A9-E50E24DCCA9E"
#define CHARACTERISTIC_UUID_TX "6E400003-B5A3-F393-E0A9-E50E24DCCA9E"

class MyServerCallbacks: public BLEServerCallbacks {
  void onConnect(BLEServer* pServer) {
    deviceConnected = true;
  }
  void onDisconnect(BLEServer* pServer) {
    deviceConnected = false;
  }
};

class MyCallbacks: public BLECharacteristicCallbacks {
  void onWrite(BLECharacteristic *pCharacteristic) {
    std::string rxValue = pCharacteristic->getValue();
    if (rxValue.length() > 0) {
      Serial.print("Received: ");
      Serial.println(rxValue.c_str());
    }
  }
};

void setup() {
  Serial.begin(115200);
  BLEDevice::init("ESP32-BLE-UART");
  pServer = BLEDevice::createServer();
  pServer->setCallbacks(new MyServerCallbacks());

  BLEService *pService = pServer->createService(SERVICE_UUID);
  pTxCharacteristic = pService->createCharacteristic(
                      CHARACTERISTIC_UUID_TX,
                      BLECharacteristic::PROPERTY_NOTIFY
                    );
  pTxCharacteristic->addDescriptor(new BLE2902());

  BLECharacteristic * pRxCharacteristic = pService->createCharacteristic(
                       CHARACTERISTIC_UUID_RX,
                       BLECharacteristic::PROPERTY_WRITE
                     );
  pRxCharacteristic->setCallbacks(new MyCallbacks());

  pService->start();
  pServer->getAdvertising()->start();
  Serial.println("Waiting for a client connection...");
}

void loop() {
  if (deviceConnected) {
    pTxCharacteristic->setValue("Hello from ESP32");
    pTxCharacteristic->notify();
    delay(1000);
  } else {
    delay(1000);
  }
}
"""
        }
    }

    meta = {
        "esp32-wifi-scan": {
            "name": "ESP32 WiFi Scan",
            "description": "Scan for nearby WiFi networks and print them to Serial.",
            "tags": ["esp32", "wifi", "scan"],
        },
        "esp32-wifi-connect": {
            "name": "ESP32 WiFi Connect",
            "description": "Connect to a WiFi network and print IP address.",
            "tags": ["esp32", "wifi", "connect"],
        },
        "esp32-ble-uart": {
            "name": "ESP32 BLE UART",
            "description": "Simple BLE UART service example.",
            "tags": ["esp32", "ble", "uart"],
        },
    }

    for tid, files in examples.items():
        if _has_template(tid):
            continue
        m = meta[tid]
        save_template(
            template_id=tid,
            name=m["name"],
            description=m["description"],
            tags=m["tags"],
            files=files,
            board_id="esp32-devkit-v1",
        )
