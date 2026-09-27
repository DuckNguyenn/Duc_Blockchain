# HRC Safety Log — Hộp đen an toàn và định danh cho robot hợp tác

Đề tài xây dựng pipeline an toàn cho không gian làm việc chung giữa người và robot, sử dụng ESP32 + hai cảm biến siêu âm HC-SR04, mô hình phát hiện bất thường và Smart Contract ghi nhật ký chống sửa đổi.

## Cấu trúc repository theo yêu cầu nộp bài

```text
README.md                    # Cài đặt, cấu hình và hướng dẫn Demo
Report_NhomXX.pdf            # Báo cáo kỹ thuật chính thức
contracts/                   # Smart Contract Solidity và Hardhat
├── HRCSafetyLog.sol
├── abi/HRCSafetyLog.json
├── scripts/deploy.js
├── scripts/demo.js
├── test/HRCSafetyLog.js
├── hardhat.config.js
└── package.json
ai_model/                    # Huấn luyện và artifact AI
├── feature_engineering.py
├── train_model.py
├── notebooks/01_train_anomaly_detection.ipynb
└── data/raw/*.csv
.iot_code/                    # Firmware ESP32 và gateway IoT
├── ultrasonic_esp32.ino
├── gateway/pipeline.py
├── gateway/serial_reader.py
├── gateway/blockchain_client.py
└── pipeline.md
```

## Cài đặt

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
cd contracts
npm install
cd ..
```

## 1. IoT: ESP32 và hai HC-SR04

Mở `iot_code/ultrasonic_esp32.ino` trong Arduino IDE, chọn board ESP32 và nạp chương trình. Firmware đo tuần tự hai cảm biến để giảm nhiễu xuyên âm, sau đó xuất:

```text
distance_cm,left=42.7cm,right=38.1cm
```

Tín hiệu ECHO của HC-SR04 là 5 V; phải dùng cầu phân áp xuống 3.3 V trước khi nối vào GPIO ESP32. Pin hiện tại là LEFT TRIG 5, LEFT ECHO 2, RIGHT TRIG 18, RIGHT ECHO 4.

## 2. AI: huấn luyện anomaly detection

Dữ liệu mẫu nằm trong `ai_model/data/raw/`. Huấn luyện bằng Isolation Forest, trong đó các mẫu `SAFE` được dùng để học vùng hoạt động bình thường:

```powershell
python ai_model/train_model.py --data-dir ai_model/data/raw --model-path ai_model/model.joblib --metrics-path ai_model/metrics.json
```

Notebook tương ứng là `ai_model/notebooks/01_train_anomaly_detection.ipynb`. Các đặc trưng gồm khoảng cách trái/phải, khoảng cách nhỏ nhất, độ lệch hai cảm biến và tốc độ tiếp cận.

AI chỉ bổ sung cảnh báo bất thường. Lớp fail-safe ưu tiên ngưỡng khoảng cách: `<= 30 cm` tạo `EMERGENCY_STOP`, `<= 60 cm` tạo `WARNING`. Đây là ngưỡng thực nghiệm, không phải khoảng cách bảo vệ đã được chứng nhận ISO/TS 15066.

## 3. Gateway và replay dữ liệu

Có thể chạy Demo không cần phần cứng bằng cách replay CSV:

```powershell
python -m iot_code.gateway.pipeline --csv ai_model/data/raw/son_dungyen_30_DANGER.csv --limit 10
```

Đọc dữ liệu trực tiếp từ ESP32 qua Serial:

```powershell
python -m iot_code.gateway.serial_reader --port COM5 --device-id HRC-ESP32-01
```

Gateway tạo `event_id` bằng SHA-256 từ device ID, timestamp, hai khoảng cách và severity. Dữ liệu chi tiết vẫn ở off-chain để phục vụ phân tích.

## 4. Blockchain local

Terminal 1:

```powershell
cd contracts
npm run node
```

Terminal 2:

```powershell
cd contracts
npm run compile
npm run deploy -- --network localhost
npm run test
```

Sau khi copy địa chỉ contract và private key của tài khoản Hardhat vào `.env`, có thể ghi sự kiện lên chain:

```powershell
cd ..
python -m iot_code.gateway.pipeline --csv ai_model/data/raw/son_dungyen_30_DANGER.csv --limit 3 --write-chain
```

`HRCSafetyLog.sol` lưu `eventHash`, `deviceIdHash`, timestamp, severity, cờ EmergencyStop và reporter. Khi `emergencyStop=true`, thiết bị bị khóa. Chỉ owner có thể xóa trạng thái EmergencyStop; event hash trùng lặp bị từ chối.

## Giới hạn

Đây là prototype nghiên cứu, chưa phải hệ thống safety-certified. Blockchain không nằm trong vòng điều khiển dừng thời gian thực; quyết định dừng cục bộ phải được xử lý fail-safe ở gateway/thiết bị. Bản hiện tại chưa điều khiển relay hoặc E-Stop vật lý.

Xem `Report_NhomXX.pdf` để đọc báo cáo kỹ thuật chính thức.
