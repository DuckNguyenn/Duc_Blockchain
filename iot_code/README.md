# IoT code

Module chính của HRC Safety Log dùng ESP32 và HC-SR04.

- `ultrasonic_esp32.ino` là firmware nộp chính, đo tuần tự hai HC-SR04 và xuất `distance_cm,left=...,right=...`.
- `firmware/hrc_safety_ultrasonic.ino` là firmware/gateway prototype có sẵn từ repository trước đó và được giữ lại để không làm mất lịch sử.
- `gateway.py`, `logging_service.py`, `blockchain.py`, `verify.py` là các module gateway/audit cũ.

Pipeline mới đầy đủ gồm `gateway/pipeline.py`, `gateway/serial_reader.py`, `gateway/blockchain_client.py`, thư mục `ai/` và `contracts/HRCSafetyLog.sol`.

Cả hai firmware đều cần cầu phân áp cho tín hiệu ECHO 5 V trước khi vào GPIO ESP32. Prototype này không nên được xem là hệ thống an toàn công nghiệp đã chứng nhận.
