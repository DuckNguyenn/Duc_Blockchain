# HRC Safety Log — Hộp đen an toàn và định danh cho robot hợp tác

HRC Safety Log là prototype cho pipeline 3 tầng: ESP32 + hai HC-SR04 thu thập khoảng cách; Python gateway tạo đặc trưng và phát hiện bất thường; Smart Contract ghi hash nhật ký, phát event kiểm toán và đặt trạng thái EmergencyStop/khóa thiết bị khi vùng nguy hiểm bị xâm nhập.

Repository này đã được hợp nhất với prototype ESP32/gateway có sẵn. Các module cũ trong `iot_code/`, `contracts/` và `tests/` được giữ lại; pipeline HRC đầy đủ mới nằm ở `ai/`, `gateway/`, `contracts/HRCSafetyLog.sol` và `blockchain/`.

## Cấu trúc chính

```text
README.md / REPORT_BLOCKCHAIN.md
ai/                               # feature engineering + train Isolation Forest
notebooks/01_train_anomaly_detection.ipynb
data/raw/                         # CSV đo thực tế
firmware/ultrasonic_esp32/       # firmware + wiring notes
.iot_code/                        # bản firmware nộp và prototype cũ
gateway/                          # replay CSV, Serial reader, Web3 adapter
contracts/HRCSafetyLog.sol       # Smart Contract HRC mới
blockchain/                       # Hardhat deploy/demo/test/ABI
contracts/contracts/SafetyLog.sol # contract prototype cũ được giữ lại
config/                           # cấu hình prototype cũ
REPORT_BLOCKCHAIN.md              # nội dung dùng để viết báo cáo
```

## Cài đặt

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
cd blockchain
npm install
cd ..
```

Prototype cũ có thể chạy độc lập theo tài liệu trong `iot_code/README.md`; pipeline mới dùng các lệnh bên dưới.

## Train AI

```powershell
python ai/train_model.py --data-dir data/raw --model-path ai/model.joblib --metrics-path data/processed/metrics.json
```

Notebook tương ứng là `notebooks/01_train_anomaly_detection.ipynb`. Isolation Forest học vùng hoạt động `SAFE`; các nhãn còn lại dùng để đánh giá. Quyết định nguy hiểm không phụ thuộc hoàn toàn vào AI: `<= 30 cm` là `EMERGENCY`, `<= 60 cm` là `WARNING`. Đây là ngưỡng thí nghiệm, không phải khoảng cách bảo vệ đã được chứng nhận ISO/TS 15066.

## Replay dữ liệu và đọc ESP32

```powershell
python -m gateway.pipeline --csv data/raw/son_dungyen_30_DANGER.csv --limit 10
python -m gateway.serial_reader --port COM5 --device-id HRC-ESP32-01
```

Firmware mới phát:

```text
distance_cm,left=42.7cm,right=38.1cm
```

ECHO HC-SR04 là 5 V và phải qua cầu phân áp xuống 3.3 V trước khi nối ESP32.

## Blockchain local

Terminal 1:

```powershell
cd blockchain
npm run node
```

Terminal 2:

```powershell
cd blockchain
npm run compile
npm run deploy -- --network localhost
npm run test
```

Copy địa chỉ contract và private key account Hardhat vào `.env`, sau đó:

```powershell
cd ..
python -m gateway.pipeline --csv data/raw/son_dungyen_30_DANGER.csv --limit 3 --write-chain
```

`HRCSafetyLog.sol` lưu `eventHash`, `deviceIdHash`, timestamp, severity, cờ EmergencyStop và reporter. Khi `emergencyStop=true`, contract đặt `emergencyStopByDevice=true` và `deviceLocked=true`. Hash on-chain là bằng chứng toàn vẹn; dữ liệu cảm biến chi tiết vẫn được giữ off-chain.

## Tài liệu báo cáo

Đọc `REPORT_BLOCKCHAIN.md` để lấy phần mô tả bài toán, kiến trúc, lý do dùng hash, thiết kế quyền reporter, kịch bản kiểm thử, giới hạn và hướng phát triển. Khi hoàn thiện, xuất tài liệu thành `Report_NhomXX.pdf` theo quy định môn học.

## Giới hạn an toàn

Đây là prototype nghiên cứu. Blockchain không được đặt trên vòng điều khiển dừng thời gian thực; dừng cục bộ phải được xử lý fail-safe ở gateway/thiết bị. Bản hiện tại chưa điều khiển relay/E-Stop vật lý và chưa phải hệ thống safety-certified.
