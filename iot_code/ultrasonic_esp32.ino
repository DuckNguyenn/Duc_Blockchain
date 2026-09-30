/* Compatibility copy: one HC-SR04 sensor, JSON telemetry for the gateway. */
#include <Arduino.h>
#include <math.h>
#include <string.h>
constexpr uint8_t TRIG_PIN = 25, ECHO_PIN = 26;
constexpr float WARNING_DISTANCE_CM = 60.0f, DANGER_DISTANCE_CM = 30.0f;
constexpr unsigned long SAMPLE_INTERVAL_MS = 100, ECHO_TIMEOUT_US = 30000;
unsigned long lastSampleAt = 0, sequenceNumber = 0;
float readDistanceCm(){ digitalWrite(TRIG_PIN,LOW); delayMicroseconds(2); digitalWrite(TRIG_PIN,HIGH); delayMicroseconds(10); digitalWrite(TRIG_PIN,LOW); unsigned long d=pulseIn(ECHO_PIN,HIGH,ECHO_TIMEOUT_US); return d==0?NAN:(d*0.0343f)/2.0f; }
const char* stateFor(float d){ if(isnan(d)) return "SENSOR_FAULT"; if(d<=DANGER_DISTANCE_CM) return "EMERGENCY"; if(d<=WARNING_DISTANCE_CM) return "WARNING"; return "SAFE"; }
void emitTelemetry(float d){ const char* state=stateFor(d); Serial.print("{\"device_id\":\"ESP32-HRC-01\",\"sensor_id\":\"HC-SR04\",\"timestamp_ms\":"); Serial.print(millis()); Serial.print(",\"distance_cm\":"); if(isnan(d)) Serial.print("null"); else Serial.print(d,1); Serial.print(",\"state\":\""); Serial.print(state); Serial.print("\",\"emergency_stop\":"); Serial.print(strcmp(state,"EMERGENCY")==0?"true":"false"); Serial.print(",\"seq\":"); Serial.print(++sequenceNumber); Serial.println("}"); }
void setup(){ Serial.begin(115200); pinMode(TRIG_PIN,OUTPUT); pinMode(ECHO_PIN,INPUT); Serial.println("HRC Safety Log single HC-SR04 ready"); }
void loop(){ unsigned long now=millis(); if(now-lastSampleAt<SAMPLE_INTERVAL_MS) return; lastSampleAt=now; emitTelemetry(readDistanceCm()); }
