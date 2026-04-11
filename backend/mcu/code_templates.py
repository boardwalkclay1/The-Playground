CODE_TEMPLATES = {
    "dht11": """
#include <DHT.h>
DHT dht(4, DHT11);

void setup() {
  Serial.begin(115200);
  dht.begin();
}

void loop() {
  Serial.println(dht.readTemperature());
  delay(1000);
}
""",

    "pir": """
void setup() {
  pinMode(14, INPUT);
  Serial.begin(115200);
}

void loop() {
  int motion = digitalRead(14);
  Serial.println(motion);
  delay(200);
}
""",

    "ultrasonic": """
#define TRIG 5
#define ECHO 18

void setup() {
  Serial.begin(115200);
  pinMode(TRIG, OUTPUT);
  pinMode(ECHO, INPUT);
}

void loop() {
  digitalWrite(TRIG, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG, LOW);

  long duration = pulseIn(ECHO, HIGH);
  float distance = duration * 0.034 / 2;

  Serial.println(distance);
  delay(200);
}
""",

    "oled-ssd1306": """
#include <Wire.h>
#include <Adafruit_SSD1306.h>

Adafruit_SSD1306 display(128, 64, &Wire);

void setup() {
  Wire.begin(21, 22);
  display.begin(SSD1306_SWITCHCAPVCC, 0x3C);
  display.clearDisplay();
  display.setTextSize(2);
  display.setTextColor(WHITE);
}

void loop() {
  display.clearDisplay();
  display.setCursor(0,0);
  display.println("Hello!");
  display.display();
  delay(1000);
}
""",
}
