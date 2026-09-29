/*
 * ESP32 + 2 x HC-SR04 ultrasonic sensors
 *
 * Pin mapping follows the supplied wiring diagram:
 *   Left sensor : TRIG -> GPIO5,  ECHO -> GPIO2 (through 1k/2k divider)
 *   Right sensor: TRIG -> GPIO18, ECHO -> GPIO4 (through 1k/2k divider) **CHECK BOARD LABEL**
 *
 * The supplied drawing's blue right-TRIG wire lands on the pin labelled D18.
 * On some cropped/low-resolution copies it can look like D17; use the board
 * silkscreen and the table in README.md rather than wire color alone.
 *   Both sensors: VCC -> VIN/5V, GND -> ESP32 GND
 *
 * The HC-SR04 ECHO output is 5 V. Do not connect ECHO directly to an
 * ESP32 GPIO. The 1 kOhm / 2 kOhm divider shown in the diagram reduces it
 * to approximately 3.33 V (assuming the 1 kOhm resistor is on ECHO side).
 */

#include <Arduino.h>

namespace Pins {
constexpr uint8_t LEFT_TRIG = 5;
constexpr uint8_t LEFT_ECHO = 2;   // boot-strap pin; keep LOW at reset
constexpr uint8_t RIGHT_TRIG = 18;
constexpr uint8_t RIGHT_ECHO = 4;  // input from the divider output

// These values match the supplied wiring diagram. GPIO2 is used as the left
// ECHO input in the diagram; if the board fails to boot, move that ECHO wire
// to another free input GPIO and update this constant.
}  // namespace Pins

constexpr uint32_t SERIAL_BAUD = 115200;
constexpr unsigned long ECHO_TIMEOUT_US = 30000UL;  // about 5 m maximum
constexpr uint32_t SENSOR_GUARD_MS = 60;            // avoid acoustic crosstalk
constexpr uint32_t SAMPLE_PERIOD_MS = 100;
constexpr float SOUND_SPEED_CM_PER_US = 0.0343f;

struct UltrasonicSensor {
  const char* name;
  uint8_t trigPin;
  uint8_t echoPin;
};

const UltrasonicSensor leftSensor{"left", Pins::LEFT_TRIG, Pins::LEFT_ECHO};
const UltrasonicSensor rightSensor{"right", Pins::RIGHT_TRIG, Pins::RIGHT_ECHO};

float readDistanceCm(const UltrasonicSensor& sensor) {
  // Guarantee a clean low-to-high trigger transition.
  digitalWrite(sensor.trigPin, LOW);
  delayMicroseconds(3);
  digitalWrite(sensor.trigPin, HIGH);
  delayMicroseconds(10);
  digitalWrite(sensor.trigPin, LOW);

  const unsigned long echoDuration = pulseIn(
      sensor.echoPin, HIGH, ECHO_TIMEOUT_US);

  // pulseIn returns zero on timeout; -1.0 is unambiguously "no reading".
  if (echoDuration == 0) {
    return -1.0f;
  }

  return (echoDuration * SOUND_SPEED_CM_PER_US) / 2.0f;
}

void printDistance(const char* label, float distanceCm) {
  Serial.print(label);
  Serial.print("=");
  if (distanceCm < 0.0f) {
    Serial.print("timeout");
  } else {
    Serial.print(distanceCm, 1);
    Serial.print("cm");
  }
}

void setup() {
  pinMode(Pins::LEFT_TRIG, OUTPUT);
  pinMode(Pins::RIGHT_TRIG, OUTPUT);
  pinMode(Pins::LEFT_ECHO, INPUT);
  pinMode(Pins::RIGHT_ECHO, INPUT);

  digitalWrite(Pins::LEFT_TRIG, LOW);
  digitalWrite(Pins::RIGHT_TRIG, LOW);

  Serial.begin(SERIAL_BAUD);
  delay(300);
  Serial.println();
  Serial.println("ESP32 dual HC-SR04 ready");
  Serial.println("left_trig=GPIO5 left_echo=GPIO2 right_trig=GPIO18 right_echo=GPIO4");
  Serial.println("ECHO must use a 5V-to-3.3V voltage divider");

  // GPIO2 is a boot-strap input on classic ESP32. The divider output must not
  // force it HIGH while the board is resetting.
}

void loop() {
  // Trigger only one sensor at a time. This prevents one sensor from hearing
  // the other sensor's ultrasonic burst.
  const float leftDistanceCm = readDistanceCm(leftSensor);
  delay(SENSOR_GUARD_MS);
  const float rightDistanceCm = readDistanceCm(rightSensor);

  Serial.print("distance_cm,");
  printDistance("left", leftDistanceCm);
  Serial.print(",");
  printDistance("right", rightDistanceCm);
  Serial.println();

  delay(SAMPLE_PERIOD_MS);
}
