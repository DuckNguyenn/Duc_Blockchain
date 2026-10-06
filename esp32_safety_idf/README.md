# ESP32 Safety Log — Native ESP-IDF

Firmware native ESP-IDF cho ESP32 + HC-SR04 + buzzer + nút silence.

## Pin map

```text
HC-SR04 TRIG       -> GPIO5
HC-SR04 ECHO       -> bộ chuyển mức 5V -> 3.3V -> GPIO18
Buzzer control     -> GPIO23
Nút bấm            -> một nhóm chân vào GPIO27, nhóm đối diện vào GND (nhấn để bật/tắt silence)
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

## Phân loại và ngưỡng bảo vệ

```text
<= 30 cm               EMERGENCY (quy tắc ưu tiên)
> 30 cm                SAFE / APPROACHING / EMERGENCY theo model
Cảm biến lỗi/timeout   SENSOR_FAULT
Model lỗi              AI_FAULT
```

ESP32 xuất JSON telemetry ở baud 115200 để Python gateway đọc qua USB Serial.

## Build model Keras -> TFLite int8 -> TFLite Micro

Cài dependency trên máy huấn luyện:

```cmd
python -m pip install tensorflow pandas numpy
```

Từ thư mục repository root, chạy:

```cmd
python -m ai_model.train_keras_tflite
```

Script sẽ đọc `ai_model/data/single_sensor/processed_3class/dataset_3class.csv` và tạo:

```text
ai_model/artifacts/esp32_candidate/ultrasonic_safety_int8.tflite
ai_model/artifacts/esp32_candidate/model_data.cc
ai_model/artifacts/esp32_candidate/model_data.h
ai_model/artifacts/esp32_candidate/model_metadata.json
```

Candidate được giữ riêng. Copy cả `model_data.cc` và `model_data.h` vào `esp32_safety_idf/main/model/` trước khi build model mới. Hai tệp này phải thuộc cùng bản export vì chứa cả model và bộ chuẩn hóa. Cập nhật `model_metadata.json`, `ultrasonic_safety_int8.tflite` và `parity_vectors.json` cùng bản export để đối chiếu; xem hướng dẫn đầy đủ ở `../HUONG_DAN_CHAY_PROJECT.md`.

## Model đang tích hợp

Đã tích hợp bản `esp32_candidate.zip` và hai tệp `model_data (1).cc/.h` được cung cấp ngày 05/10/2026 vào `main/model/`. Mảng C++ khớp từng byte với TFLite trong ZIP.

- Model INT8, 3.352 byte; mạng Dense 16 → 8 → 3, ReLU tích hợp trong FullyConnected và Softmax đầu ra.
- Input `[1,3]`: `distance_cm`, `distance_delta_3`, `distance_std_5`; chuẩn hóa bằng `g_feature_mean` và `g_feature_scale` trong cùng tệp model.
- Output `[1,3]`: `SAFE`, `APPROACHING`, `EMERGENCY` theo đúng thứ tự này.
- Tensor arena giữ ở 24 KB; log khởi động in dung lượng model và RAM arena đã dùng.
- Bản model trước khi thay được lưu tại `../_work_extract/esp32_model_before_import_20261005/`.

## Build firmware với TFLite Micro

Từ ESP-IDF terminal:

```cmd
cd /d "C:\Users\P1 Gen 5\Downloads\Blockchain\esp32_safety_idf"
idf.py set-target esp32
idf.py -p COM5 reconfigure
idf.py -p COM5 build
idf.py -p COM5 flash monitor
```

Firmware tính `distance_cm`, `distance_delta_3`, `distance_std_5` với cửa sổ năm mẫu, std mẫu ddof=1. Hard rule `distance <=30 cm -> EMERGENCY` luôn ưu tiên; AI có thể nâng lên EMERGENCY phía ngoài. Không hạ dự đoán EMERGENCY thành APPROACHING. Input/output phải đúng `[1,3]` INT8; model 6 feature bị từ chối. Khi lỗi cảm biến, history được xóa.

Chu kỳ đặt hiện tại là 176 ms, theo median của dữ liệu huấn luyện trong metadata; `vTaskDelayUntil` tính cả thời gian đo/inference trong chu kỳ này. Thời gian thực tế được làm tròn theo tick FreeRTOS. Kiểm tra telemetry trên board trước khi kết luận độ chính xác thực tế. Kết quả offline và candidate xem `../docs/DANH_GIA_PROJECT_VA_MODEL.md`.

Nếu gặp lỗi `AllocateTensors failed`, tăng `TENSOR_ARENA_SIZE` trong `main/main.cpp`. Nếu dùng ESP32-S3 hoặc ESP32-C3, đổi target tương ứng trước khi build.

Lưu ý: `esp-tflite-micro` được khai báo trong `main/idf_component.yml`; lần build đầu tiên ESP-IDF sẽ tải component này.
