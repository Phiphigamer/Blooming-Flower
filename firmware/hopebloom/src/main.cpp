// HopeBloom firmware
//
// Touch the ring  -> the ring LEDs swirl and a "bloom" is sent to the partner flower.
// Receive a bloom -> the petals open and the core glows warm, fading out over GLOW_MINUTES.
//                    When the glow is gone, the petals close again.
// Hold the ring 3 s -> dismiss the current glow.
//
// Hardware (main board):
//   GPIO4 -> servo signal
//   GPIO5 -> WS2812B data (8 ring LEDs, then 12 core LEDs on the flower board)
//   GPIO6 <- TTP223 output (HIGH while touched)

#include <Arduino.h>
#include <WiFi.h>
#include <PubSubClient.h>
#include <Adafruit_NeoPixel.h>
#include <ESP32Servo.h>
#include <time.h>

#if __has_include("config.h")
#include "config.h"
#else
#include "config.example.h"
#warning "config.h not found: using config.example.h"
#endif

// ---------- pins and LEDs ----------
constexpr int PIN_SERVO = 4;
constexpr int PIN_LEDS  = 5;
constexpr int PIN_TOUCH = 6;

constexpr int RING_LEDS  = 8;
constexpr int CORE_LEDS  = 12;
constexpr int TOTAL_LEDS = RING_LEDS + CORE_LEDS;
constexpr int CORE_FIRST = RING_LEDS;   // core LEDs come after the ring in the chain

// Warm white / soft peach for the core glow
constexpr uint8_t GLOW_R = 255, GLOW_G = 140, GLOW_B = 60;
// Ring colour when sending
constexpr uint8_t SEND_R = 255, SEND_G = 90, SEND_B = 140;

Adafruit_NeoPixel leds(TOTAL_LEDS, PIN_LEDS, NEO_GRB + NEO_KHZ800);
Servo servo;
WiFiClient net;
PubSubClient mqtt(net);

String topicIn, topicOut;

// ---------- state ----------
time_t bloomStart = 0;          // epoch seconds of the bloom being shown (0 = none)
time_t lastSeen = 0;            // newest bloom ever received, so a dismissed one never comes back
bool petalsOpen = false;
uint32_t lastReconnectTry = 0;

// ---------- helpers ----------
bool timeValid() { return time(nullptr) > 1700000000; }   // NTP has synced

void moveServo(int targetDeg) {
  // Move slowly so the petals open gently, then detach to stop jitter and save power.
  servo.attach(PIN_SERVO, 500, 2400);
  static int current = SERVO_CLOSED_DEG;
  int step = targetDeg > current ? 1 : -1;
  while (current != targetDeg) {
    current += step;
    servo.write(current);
    delay(25);
  }
  delay(300);
  servo.detach();
}

void openPetals()  { if (!petalsOpen) { moveServo(SERVO_OPEN_DEG);   petalsOpen = true;  } }
void closePetals() { if (petalsOpen)  { moveServo(SERVO_CLOSED_DEG); petalsOpen = false; } }

void setCore(float level) {          // level 0.0 - 1.0
  float k = level * MAX_BRIGHTNESS / 255.0f;
  for (int i = 0; i < CORE_LEDS; i++)
    leds.setPixelColor(CORE_FIRST + i, leds.Color(GLOW_R * k, GLOW_G * k, GLOW_B * k));
}

void clearRing() {
  for (int i = 0; i < RING_LEDS; i++) leds.setPixelColor(i, 0);
}

void swirlRing(uint8_t r, uint8_t g, uint8_t b, int turns) {
  float k = MAX_BRIGHTNESS / 255.0f;
  for (int t = 0; t < turns * RING_LEDS; t++) {
    clearRing();
    for (int tail = 0; tail < 3; tail++) {
      float f = k / (1 + tail * 2);
      leds.setPixelColor((t - tail + RING_LEDS) % RING_LEDS, leds.Color(r * f, g * f, b * f));
    }
    leds.show();
    delay(60);
  }
  clearRing();
  leds.show();
}

// Glow level from 1.0 (just received) down to 0.0 (GLOW_MINUTES later).
float glowLevel() {
  if (bloomStart == 0 || !timeValid()) return 0;
  double elapsed = difftime(time(nullptr), bloomStart);
  double total = GLOW_MINUTES * 60.0;
  if (elapsed < 0) elapsed = 0;
  if (elapsed >= total) return 0;
  float x = 1.0 - elapsed / total;
  return x * x;                       // eased: fades quickly at the end, slowly at first
}

// ---------- network ----------
void onMessage(char* topic, byte* payload, unsigned int len) {
  String msg;
  for (unsigned int i = 0; i < len; i++) msg += (char)payload[i];
  // Payload: "bloom:<epoch seconds>" (retained, so a flower that was offline still gets it)
  if (!msg.startsWith("bloom:")) return;
  time_t sent = (time_t)msg.substring(6).toInt();
  if (sent <= lastSeen) return;       // already handled (retained messages repeat on reconnect)
  lastSeen = sent;
  bloomStart = sent;
  if (glowLevel() > 0) {
    swirlRing(GLOW_R, GLOW_G, GLOW_B, 1);
    openPetals();
  }
}

void connectMqtt() {
  if (mqtt.connected() || WiFi.status() != WL_CONNECTED) return;
  if (millis() - lastReconnectTry < 5000) return;
  lastReconnectTry = millis();
  String clientId = String("hopebloom-") + PAIR_ID + "-" + DEVICE_ID;
  if (mqtt.connect(clientId.c_str())) {
    mqtt.subscribe(topicIn.c_str(), 1);
    Serial.println("MQTT connected");
  }
}

void sendBloom() {
  if (!mqtt.connected() || !timeValid()) {
    swirlRing(255, 30, 0, 1);         // orange swirl = could not send
    return;
  }
  String payload = "bloom:" + String((long)time(nullptr));
  mqtt.publish(topicOut.c_str(), payload.c_str(), true);   // retained
  swirlRing(SEND_R, SEND_G, SEND_B, 2);
}

// ---------- touch ----------
void handleTouch() {
  static bool wasTouched = false;
  static uint32_t pressedAt = 0;
  static bool longHandled = false;
  bool touched = digitalRead(PIN_TOUCH) == HIGH;

  if (touched && !wasTouched) { pressedAt = millis(); longHandled = false; }
  if (touched && !longHandled && millis() - pressedAt > 3000) {
    bloomStart = 0;                    // dismiss the glow
    longHandled = true;
  }
  if (!touched && wasTouched && !longHandled && millis() - pressedAt > 50) {
    sendBloom();
  }
  wasTouched = touched;
}

// ---------- main ----------
void setup() {
  Serial.begin(115200);
  pinMode(PIN_TOUCH, INPUT);

  leds.begin();
  leds.clear();
  leds.show();

  servo.attach(PIN_SERVO, 500, 2400);
  servo.write(SERVO_CLOSED_DEG);
  delay(500);
  servo.detach();

  topicIn  = String("hopebloom/") + PAIR_ID + "/to/" + DEVICE_ID;
  topicOut = String("hopebloom/") + PAIR_ID + "/to/" + PARTNER_ID;

  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  configTime(0, 0, "pool.ntp.org", "time.google.com");

  mqtt.setServer(MQTT_HOST, MQTT_PORT);
  mqtt.setCallback(onMessage);
}

void loop() {
  connectMqtt();
  mqtt.loop();
  handleTouch();

  float level = glowLevel();
  if (level > 0) {
    openPetals();
  } else {
    if (bloomStart != 0 && timeValid()) bloomStart = 0;
    closePetals();
  }
  setCore(level);
  leds.show();
  delay(20);
}
