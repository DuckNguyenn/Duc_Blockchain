# HRC Safety Log — Hộp đen an toàn và định danh cho robot hợp tác

Đề tài triển khai một pipeline 3 tầng: ESP32 + hai HC-SR04 thu thập khoảng cách; Python tạo đặc trưng và phát hiện bất thường; Smart Contract ghi hash nhật ký và kích hoạt trạng thái EmergencyStop/khóa thiết bị khi vùng nguy hiểm bị xâm nhập.

## 1. Cấu trúc Repository

```text
.
├── README.md
├── REPORT_BLOCKCHAIN.md
├── requirements.txt
├── .env.example
├── iot_code/ultrasonic_esp32.ino   # bản nộp theo đúng rubric
├── firmware/ultrasonic_esp32/       # wiring notes + working copy
├── data/raw/                        # CSV đo thật đã có
├── data/processed/                  # metrics/model phụ trợ sinh ra
├── notebooks/01_train_anomaly_detection.ipynb
├── ai/feature_engineering.py        # đặc trưng dùng chung
├── ai/train_model.py                # train Isolation Forest
├── gateway/pipeline.py              # replay CSV + quyết định an toàn
├── gateway/serial_reader.py         # đọc đúng format Serial hiện tại
├── gateway/blockchain_client.py     # adapter Web3
├── contracts/HRCSafetyLog.sol       # Smart Contract
└── blockchain/                      # Hardhat deploy/demo/test + ABI
```

Tên file đáp ứng quy định nộp bài: `README.md` hướng dẫn chạy; `contracts/` mã Smart Contract; `ai/` mã và model phụ trợ; `iot_code` tương đương `firmware/`; báo cáo chính thức có thể xuất thành `Report_NhomXX.pdf` sau khi hoàn thiện nội dung trong `REPORT_BLOCKCHAIN.md`.

## 2. Chuẩn bị môi trường

```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
cd blockchain
npm install
cd ..
```

## 3. Train AI

Có thể chạy notebook trong Jupyter hoặc chạy script:

```bash
python ai/train_model.py --data-dir data/raw --model-path ai/model.joblib --metrics-path data/processed/metrics.json
```

Mô hình Isolation Forest học các mẫu `SAFE` và đánh dấu mẫu lệch khỏi vùng bình thường. Quyết định an toàn không phụ thuộc hoàn toàn vào mô hình: ngưỡng khoảng cách `<= 30 cm` là `EMERGENCY`, `<= 60 cm` là `WARNING`. Đây là thiết kế fail-safe phù hợp cho demo; không tuyên bố hệ thống là thiết bị an toàn công nghiệp được chứng nhận ISO/TS 15066.

## 4. Demo pipeline không cần blockchain

```bash
python -m gateway.pipeline --csv data/raw/son_dungyen_30_DANGER.csv --limit 10
```

Mỗi dòng JSON cho biết khoảng cách, severity, confidence, event_id và hành động. Dùng một file SAFE và một file DANGER để quay video chứng minh hai trạng thái.

## 5. Demo blockchain local

Terminal 1:

```bash
cd blockchain
npm run node
```

Terminal 2:

```bash
cd blockchain
npm run compile
npm run deploy -- --network localhost
```

Copy địa chỉ contract được in ra vào `.env` cùng private key của account Hardhat đầu tiên. Sau đó chạy:

```bash
npm run demo -- --network localhost
cd ..
python -m gateway.pipeline --csv data/raw/son_dungyen_30_DANGER.csv --limit 3 --write-chain
```

`npm run demo` là đường chạy kiểm tra nhanh: deploy contract tạm thời, ghi event DANGER + EmergencyStop, rồi đọc lại trạng thái `deviceLocked`. Để gateway ghi chain, cần điền `CONTRACT_ADDRESS`, `RPC_URL`, `PRIVATE_KEY` trong `.env`.

## 6. Đọc dữ liệu trực tiếp từ ESP32

Firmware hiện tại phát:

```text
distance_cm,left=42.7cm,right=38.1cm
```

Chạy gateway:

```bash
python -m gateway.serial_reader --port COM5 --device-id HRC-ESP32-01
```

Đổi `COM5` thành cổng thực tế. HC-SR04 ECHO phải qua cầu phân áp 5 V xuống 3.3 V; không nối ECHO 5 V trực tiếp vào GPIO ESP32. Trạng thái EmergencyStop ở bản demo được ghi vào blockchain; để ngắt cơ cấu thật cần nối thêm relay/MOSFET hoặc ngõ vào điều khiển và chứng minh cơ chế đó riêng trong phần IoT.

## 7. Luồng trình diễn đề xuất

Khởi động Hardhat node, deploy contract, chạy gateway ở chế độ replay. Cho file SAFE để chứng minh chỉ ghi log bình thường; tiếp tục chạy file DANGER để chứng minh gateway tạo `EMERGENCY_STOP`, transaction phát event `SafetyEventRecorded`, và contract đặt `emergencyStopByDevice=true`, `deviceLocked=true`. Trình bày transaction hash và đọc lại event từ explorer/local console.

## 8. Phân công thành viên gợi ý

Một thành viên phụ trách firmware và mạch; một thành viên phụ trách thu thập/làm sạch dữ liệu và notebook; một thành viên phụ trách Solidity/Hardhat; một thành viên phụ trách gateway, kiểm thử và báo cáo. Mỗi thành viên phải giải thích được toàn bộ pipeline khi phản biện.
