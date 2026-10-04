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

## Build model Keras -> TFLite int8 -> TFLite Micro

Cài dependency trên máy huấn luyện:

```cmd
python -m pip install tensorflow pandas numpy
```

Từ thư mục repository root, chạy:

```cmd
python ai_model\\train_keras_tflite.py
```

Script sẽ đọc `ai_model/data/single_sensor/processed_3class/dataset_3class.csv` và tạo:

```text
esp32_safety_idf/main/model/ultrasonic_safety_int8.tflite
esp32_safety_idf/main/model/model_data.cc
esp32_safety_idf/main/model/model_data.h
esp32_safety_idf/main/model/model_metadata.json
```

`model_data.cc` là mảng byte được firmware nạp bằng TensorFlow Lite Micro. Chạy script này lại mỗi lần huấn luyện model mới; không sửa thủ công file `model_data.cc`.

## Build firmware với TFLite Micro

Từ ESP-IDF terminal:

```cmd
cd /d "C:\Users\P1 Gen 5\Downloads\Blockchain\esp32_safety_idf"
idf.py set-target esp32
idf.py -p COM5 reconfigure
idf.py -p COM5 build
idf.py -p COM5 flash monitor
```

Firmware tính cùng sáu feature như notebook, dùng cửa sổ năm mẫu, lượng tử hóa input theo metadata của model và giữ hard rule `distance <= 30 cm -> EMERGENCY`. Nếu chưa chạy bước export model, firmware chỉ chứa model placeholder và không được dùng để thử nghiệm thật.

Nếu gặp lỗi `AllocateTensors failed`, tăng `TENSOR_ARENA_SIZE` trong `main/main.cpp`. Nếu dùng ESP32-S3 hoặc ESP32-C3, đổi target tương ứng trước khi build.

Lưu ý: `esp-tflite-micro` được khai báo trong `main/idf_component.yml`; lần build đầu tiên ESP-IDF sẽ tải component này.
