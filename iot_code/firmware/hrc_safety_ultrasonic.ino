/*
 * HRC Safety Log - ESP32 + HC-SR04 distance warning logger.
 *
 * This firmware only measures distance and sends serial JSON telemetry.
 * It does not use a camera, AI model, relay, buzzer, or emergency-stop logic.
 * Configure ALERT_DISTANCE_CM to match the warning distance for your demo.
 */

#include <Arduino.h>
#include <math.h>

constexpr uint8_t TRIG_PIN = 25;
constexpr uint8_t ECHO_PIN = 26;
constexpr float ALERT_DISTANCE_CM = 50.0f;
constexpr unsigned long SAMPLE_INTERVAL_MS = 200;
constexpr unsigned long ECHO_TIMEOUT_US = 30000;

unsigned long lastSampleAt = 0;
unsigned long sequenceNumber = 0;

float readDistanceCm() {
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);

  const unsigned long duration = pulseIn(ECHO_PIN, HIGH, ECHO_TIMEOUT_US);
  if (duration == 0) {
    return NAN;
  }
  return (duration * 0.0343f) / 2.0f;
}

const char *stateFor(float distanceCm) {
  if (isnan(distanceCm)) {
    return "SENSOR_FAULT";
  }
  return distanceCm < ALERT_DISTANCE_CM ? "WARNING" : "SAFE";
}

void emitTelemetry(float distanceCm) {
  Serial.print("{\"device_id\":\"ESP32-HRC-01\",\"sensor_id\":\"HC-SR04\"");
  Serial.print(",\"timestamp_ms\":");
  Serial.print(millis());
  Serial.print(",\"distance_cm\":");
  if (isnan(distanceCm)) {
    Serial.print("null");
  } else {
    Serial.print(distanceCm, 1);
  }
  Serial.print(",\"state\":\"");
  Serial.print(stateFor(distanceCm));
  Serial.print("\",\"seq\":");
  Serial.print(++sequenceNumber);
  Serial.println("}");
}

void setup() {
  Serial.begin(115200);
  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);
  Serial.println("HRC Safety Log ultrasonic distance logger ready");
}

void loop() {
  const unsigned long now = millis();
  if (now - lastSampleAt < SAMPLE_INTERVAL_MS) {
    return;
  }
  lastSampleAt = now;
  emitTelemetry(readDistanceCm());
}