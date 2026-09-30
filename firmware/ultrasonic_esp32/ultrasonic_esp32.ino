/*
  ESP32 DevKit v1 + one HC-SR04 + active buzzer + momentary silence button.

  Important:
  - HC-SR04 is powered from 5 V. Its ECHO signal MUST go through the
    1 kOhm / 2 kOhm divider shown in the wiring diagram before GPIO18.
  - The button silences the buzzer temporarily. It is not a safety-rated
    emergency-stop circuit and must not be used as the sole protection for
    people or machinery.
  - The buzzer output is intended to drive an NPN transistor, not a large
    buzzer directly from an ESP32 GPIO.
*/
#include <Arduino.h>
#include <math.h>
#include <string.h>

constexpr uint8_t TRIG_PIN = 5;
constexpr uint8_t ECHO_PIN = 18;       // divider output, never raw 5 V ECHO
constexpr uint8_t BUZZER_PIN = 23;     // drives NPN transistor base via 1 kOhm
constexpr uint8_t SILENCE_BUTTON_PIN = 27; // button to GND, INPUT_PULLUP

constexpr float WARNING_DISTANCE_CM = 60.0f;
constexpr float DANGER_DISTANCE_CM = 30.0f;
constexpr unsigned long SAMPLE_INTERVAL_MS = 100;
constexpr unsigned long ECHO_TIMEOUT_US = 30000;
constexpr unsigned long DEBOUNCE_MS = 35;

unsigned long lastSampleAt = 0;
unsigned long lastButtonChangeAt = 0;
unsigned long sequenceNumber = 0;
bool lastButtonReading = HIGH;
bool stableButtonState = HIGH;
bool buzzerSilenced = false;

float readDistanceCm() {
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);

  const unsigned long duration = pulseIn(ECHO_PIN, HIGH, ECHO_TIMEOUT_US);
  return duration == 0 ? NAN : (duration * 0.0343f) / 2.0f;
}

const char* stateFor(float distanceCm) {
  if (isnan(distanceCm)) return "SENSOR_FAULT";
  if (distanceCm <= DANGER_DISTANCE_CM) return "EMERGENCY";
  if (distanceCm <= WARNING_DISTANCE_CM) return "WARNING";
  return "SAFE";
}

void updateButton() {
  const bool reading = digitalRead(SILENCE_BUTTON_PIN);
  const unsigned long now = millis();

  if (reading != lastButtonReading) {
    lastButtonChangeAt = now;
    lastButtonReading = reading;
  }

  if ((now - lastButtonChangeAt) >= DEBOUNCE_MS && reading != stableButtonState) {
    stableButtonState = reading;
    if (stableButtonState == LOW) {
      buzzerSilenced = true;
    }
  }
}

void emitTelemetry(float distanceCm, const char* state, bool buzzerOn) {
  Serial.print("{\"device_id\":\"ESP32-HRC-01\",\"sensor_id\":\"HC-SR04\",\"timestamp_ms\":");
  Serial.print(millis());
  Serial.print(",\"distance_cm\":");
  if (isnan(distanceCm)) Serial.print("null");
  else Serial.print(distanceCm, 1);
  Serial.print(",\"state\":\"");
  Serial.print(state);
  Serial.print("\",\"emergency_stop\":");
  Serial.print(strcmp(state, "EMERGENCY") == 0 ? "true" : "false");
  Serial.print(",\"buzzer_on\":");
  Serial.print(buzzerOn ? "true" : "false");
  Serial.print(",\"buzzer_silenced\":");
  Serial.print(buzzerSilenced ? "true" : "false");
  Serial.print(",\"seq\":");
  Serial.print(++sequenceNumber);
  Serial.println("}");
}

void setup() {
  Serial.begin(115200);
  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);
  pinMode(BUZZER_PIN, OUTPUT);
  pinMode(SILENCE_BUTTON_PIN, INPUT_PULLUP);
  digitalWrite(TRIG_PIN, LOW);
  digitalWrite(BUZZER_PIN, LOW);

  Serial.println("HRC Safety Log: ESP32 + HC-SR04 + buzzer + silence button ready");
}

void loop() {
  updateButton();

  const unsigned long now = millis();
  if (now - lastSampleAt < SAMPLE_INTERVAL_MS) return;
  lastSampleAt = now;

  const float distanceCm = readDistanceCm();
  const char* state = stateFor(distanceCm);

  // A safe reading rearms the next alarm. Sensor fault is fail-safe and alarms.
  if (strcmp(state, "SAFE") == 0) {
    buzzerSilenced = false;
  }

  const bool alarmState = strcmp(state, "EMERGENCY") == 0 || strcmp(state, "SENSOR_FAULT") == 0;
  const bool buzzerOn = alarmState && !buzzerSilenced;
  digitalWrite(BUZZER_PIN, buzzerOn ? HIGH : LOW);

  emitTelemetry(distanceCm, state, buzzerOn);
}
