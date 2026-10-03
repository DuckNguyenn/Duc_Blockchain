# ESP32 Safety Log — Native ESP-IDF

Firmware native ESP-IDF cho ESP32 + HC-SR04 + buzzer + nút silence.

## Pin map

```text
HC-SR04 TRIG       -> GPIO5
HC-SR04 ECHO       -> bộ chuyển mức 5V -> 3.3V -> GPIO18
Buzzer control     -> GPIO23
Nút bấm            -> GPIO27 và GND
HC-SR04 VCC        -> V5/VIN
HC-SR04 GND        -> GND
Level converter HV -> V5/VIN
Level converter LV -> 3V3
Level converter GND -> GND
```

Không nối ECHO 5 V trực tiếp vào GPIO18. Dùng bộ chuyển mức trước khi đưa tín hiệu vào ESP32.

## Build và nạp

Mở ESP-IDF terminal, thay `COM5` bằng cổng thật:

```cmd
cd /d "C:\Users\P1 Gen 5\Downloads\Blockchain\esp32_safety_idf"
idf.py set-target esp32
idf.py -p COM5 build
idf.py -p COM5 flash monitor
```

Thoát monitor bằng `Ctrl + ]`. Không chạy monitor cùng lúc với Python gateway vì cả hai cùng mở một cổng COM.

## Ngưỡng

```text
> 60 cm       SAFE
31–60 cm      WARNING
<= 30 cm      EMERGENCY
SENSOR timeout SENSOR_FAULT
```

ESP32 xuất JSON telemetry ở baud 115200 để Python gateway đọc qua USB Serial.
