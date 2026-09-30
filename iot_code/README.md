# IoT code

Thư mục này chứa firmware ESP32 và gateway của đề tài HRC Safety Log.

- `ultrasonic_esp32.ino`: firmware chính, đo tuần tự một HC-SR04 và xuất telemetry qua Serial.
- `gateway/`: parser Serial/MQTT, replay CSV, feature-based safety classification và Web3 adapter.
- `gateway/mqtt_subscriber.py`: subscriber MQTT local, chuyển telemetry JSON vào evidence outbox và tùy chọn ghi chain.
- `../docker-compose.mqtt.yml` + `../config/mosquitto.conf`: MQTT broker Mosquitto cho môi trường local.

## MQTT local

Khởi động Mosquitto bằng Docker Desktop:

```cmd
docker compose -f docker-compose.mqtt.yml up -d
```

Broker lắng nghe MQTT ở `127.0.0.1:1883`; WebSocket tùy chọn ở `127.0.0.1:9001`. Topic mặc định là `hrc/telemetry/#`. Cấu hình hiện cho phép anonymous chỉ để demo local; không expose ra mạng thật nếu chưa thêm username/password và TLS.

Chạy gateway subscriber:

```cmd
python -m iot_code.gateway.mqtt_subscriber --host 127.0.0.1 --port 1883 --topic hrc/telemetry/# --device-id HRC-ESP32-01
```

Gửi thử một message từ terminal khác:

```cmd
docker exec hrc-mqtt mosquitto_pub -h 127.0.0.1 -t hrc/telemetry/HRC-ESP32-01 -q 1 -m "{\"device_id\":\"HRC-ESP32-01\",\"timestamp_ms\":1730000000000,\"distance_cm\":24.6}"
```

Subscriber sẽ tạo evidence tại `data/evidence_outbox/<evidence_hash>.json` và in `severity=EMERGENCY`, `emergency_stop=true`, `submission_status=queued`. Thêm `--write-chain` sau khi cấu hình `RPC_URL`, `CONTRACT_ADDRESS` và `PRIVATE_KEY` để submit commitment lên `HRCSafetyLog`.

Dừng broker:

```cmd
docker compose -f docker-compose.mqtt.yml down
```

Firmware hiện tại vẫn giữ Serial để không phá demo ESP32 cũ; MQTT subscriber có thể được kiểm thử bằng publisher giả lập hoặc một ESP32/Wi-Fi publisher bổ sung sau.


## Serial và evidence

- `evidence.py`: canonical evidence v1 và durable outbox cho ranh giới off-chain → on-chain.
- `pipeline.md`: mô tả luồng IoT → AI → Blockchain.

Firmware xuất dữ liệu theo định dạng:

```text
distance_cm,distance=42.7cm
```

HC-SR04 dùng ECHO 5 V, vì vậy phải lắp cầu phân áp xuống 3.3 V trước khi đưa tín hiệu vào GPIO ESP32. Prototype chưa phải hệ thống an toàn công nghiệp đã chứng nhận và chưa điều khiển E-Stop vật lý.

`gateway.pipeline.process_row` tạo evidence off-chain trước. Với `--evidence-dir`, envelope được lưu tại `data/evidence_outbox/<evidence_hash>.json`; khi ghi chain, chỉ digest/schema/device/timestamp/severity/stop được gửi tới `HRCSafetyLog.recordEvidence`. Raw distance, confidence, model và policy version không được đưa lên chain.

Retry các evidence pending sau khi RPC hoạt động:

```powershell
python -m iot_code.gateway.pipeline --retry-outbox --write-chain --evidence-dir data/evidence_outbox
```
