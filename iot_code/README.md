# IoT code

Thư mục này chứa firmware ESP32 và gateway của đề tài HRC Safety Log.

- `ultrasonic_esp32.ino`: firmware chính, đo tuần tự hai HC-SR04 và xuất telemetry qua Serial.
- `gateway/`: parser Serial, replay CSV, feature-based safety classification và Web3 adapter.
- `pipeline.md`: mô tả luồng IoT → AI → Blockchain.

Firmware xuất dữ liệu theo định dạng:

```text
distance_cm,left=42.7cm,right=38.1cm
```

HC-SR04 dùng ECHO 5 V, vì vậy phải lắp cầu phân áp xuống 3.3 V trước khi đưa tín hiệu vào GPIO ESP32. Prototype chưa phải hệ thống an toàn công nghiệp đã chứng nhận và chưa điều khiển E-Stop vật lý.