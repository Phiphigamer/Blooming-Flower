// Copy this file to config.h and fill it in. config.h is ignored by git,
// so your Wi-Fi password never ends up on GitHub.
#pragma once

// ---- Wi-Fi ----
#define WIFI_SSID      "your-wifi-name"
#define WIFI_PASSWORD  "your-wifi-password"

// ---- Pairing ----
// Both flowers of a pair use the same PAIR_ID (pick something long and random).
// One flower is "A", the other is "B".
#define PAIR_ID        "change-me-to-something-random"
#define DEVICE_ID      "A"
#define PARTNER_ID     "B"

// ---- MQTT broker ----
// The public HiveMQ broker is fine for testing. Anyone who knows the topic can
// read it, so use your own broker for real patients.
#define MQTT_HOST      "broker.hivemq.com"
#define MQTT_PORT      1883

// ---- Servo (adjust after assembly) ----
// Angles of the servo arm for a closed bud and fully open petals.
// The pushrod travel is about 5.7 mm (12 mm arm, about +/-14 degrees).
#define SERVO_CLOSED_DEG  76
#define SERVO_OPEN_DEG    104

// ---- Light ----
#define GLOW_MINUTES      60    // how long a bloom glows before fading out
#define MAX_BRIGHTNESS    160   // 0-255, keeps USB current within budget
