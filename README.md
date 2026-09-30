# HRC Safety Log / SonarChain

Prototype IoT–AI–Web3 ghi nhận cảnh báo khoảng cách cho không gian làm việc giữa người và robot. Hai cảm biến siêu âm HC-SR04 nối với ESP32 đo khoảng cách; gateway phân loại theo ngưỡng fail-safe; smart contract lưu hash bằng chứng và trạng thái Emergency Stop.

> Đây là prototype nghiên cứu, chưa phải hệ thống safety-certified. Blockchain không nằm trong vòng điều khiển dừng thời gian thực; quyết định dừng cục bộ phải được xử lý fail-safe ở ESP32/gateway.

## Cấu trúc chính

```text
contracts/                 Solidity + Hardhat + ABI + test/deploy scripts
web3/                      SonarChain browser dashboard + MetaMask integration
ai_model/                  Feature engineering, model training, sample CSV data
iot_code/                  ESP32 firmware, gateway, serial reader, Web3 adapter
firmware/ultrasonic_esp32/ Firmware và hướng dẫn đấu nối HC-SR04
data/raw/                  Các bản ghi CSV dùng để replay/train
docs/                      Pipeline và tài liệu đề tài
tests/                     Python gateway tests
```

## Yêu cầu

- Windows 10/11
- Node.js LTS (Node 22 khuyến nghị) và npm
- Python 3.10+
- MetaMask chỉ cần cho dashboard ghi event on-chain
- Arduino IDE + ESP32 nếu chạy cảm biến thật

Trên PowerShell, nếu `npm` bị chặn bởi Execution Policy, dùng `npm.cmd`.

## Chạy nhanh dashboard mô phỏng

Không cần ESP32 hay blockchain:

```powershell
cd "C:\Users\P1 Gen 5\Downloads\Blockchain"
py -m http.server 8080 -d web3
```

Mở <http://localhost:8080> và nhấn **Chạy mô phỏng**.

## Chạy Web3 local đầy đủ

### Terminal 1 — cài, compile và chạy Hardhat node

```powershell
cd "C:\Users\P1 Gen 5\Downloads\Blockchain\contracts"
npm.cmd install
npm.cmd run compile
npm.cmd run node
```

Giữ terminal này mở. RPC là `http://127.0.0.1:8545`, chain ID `31337`.

Nếu thấy `EADDRINUSE`, node đã chạy sẵn; không khởi động thêm node thứ hai.

### Terminal 2 — deploy contract

```powershell
cd "C:\Users\P1 Gen 5\Downloads\Blockchain\contracts"
npm.cmd run deploy
```

Copy địa chỉ sau `contract=`. Ví dụ:

```text
0x5FbDB2315678afecb367f032d93F642f64180aa3
```

### MetaMask

Thêm network thủ công:

```text
Name: Hardhat Local
RPC: http://127.0.0.1:8545
Chain ID: 31337
Currency: ETH
```

Import `Account #0` (deployer) bằng private key được Hardhat in ra. Các key này chỉ dùng trên local và không được dùng trên mạng thật.

### Terminal 3 — mở dashboard

```powershell
cd "C:\Users\P1 Gen 5\Downloads\Blockchain"
py -m http.server 8080 -d web3
```

Trong dashboard: **Kết nối ví** → nhập contract address → **Chạy mô phỏng** → **Ghi event hiện tại lên chain** → xác nhận giao dịch trong MetaMask.

Dashboard chỉ ghi `eventHash`, `deviceIdHash`, severity và `emergencyStop`; raw telemetry vẫn ở off-chain.

Ranh giới chi tiết và các khoảng trống đã rà soát nằm ở [docs/BLOCKCHAIN_BOUNDARY_AUDIT.md](docs/BLOCKCHAIN_BOUNDARY_AUDIT.md). Luồng mới dùng evidence envelope v1 + outbox off-chain, sau đó ghi digest/schema/thời điểm/mức độ/flag lên `HRCSafetyLog`; raw telemetry, confidence, model và policy version vẫn ở off-chain.

### Work Permit & Human–Robot Handoff

`WorkPermitHandoff` bổ sung workflow nghiệp vụ cho HRC: requester tạo permit cho worker/task/zone, supervisor approve, gateway ghi nhận worker đã vào zone dựa trên telemetry, worker xác nhận robot bàn giao task, rồi đóng permit. Sau `npm.cmd run deploy`, dùng dòng `permitContract=` làm địa chỉ contract trong panel **Work permit & robot handoff** của dashboard.

## Test smart contract

Khi không cần node riêng, Hardhat test dùng network in-memory:

```powershell
cd contracts
npm.cmd test
```

Demo sau khi node local chạy:

```powershell
npm.cmd run demo
```

## Replay CSV qua gateway

```powershell
cd "C:\Users\P1 Gen 5\Downloads\Blockchain"
python -m iot_code.gateway.pipeline `
  --csv ai_model/data/raw/son_dungyen_30_DANGER.csv `
  --limit 10
```

Để ghi lên chain, tạo `.env` từ `.env.example`, điền `RPC_URL`, `CONTRACT_ADDRESS` và private key local, rồi thêm `--write-chain`.

## AI model

```powershell
python -m pip install -r requirements.txt
python ai_model/train_model.py `
  --data-dir ai_model/data/raw `
  --model-path ai_model/model.joblib `
  --metrics-path ai_model/metrics.json
```

Ngưỡng fail-safe mặc định là `WARNING` khi khoảng cách ≤ 60 cm và `EMERGENCY` khi ≤ 30 cm. AI chỉ bổ sung phát hiện bất thường, không được phép vô hiệu hóa ngưỡng an toàn.

## ESP32 + HC-SR04

Nạp `firmware/ultrasonic_esp32/ultrasonic_esp32.ino` bằng Arduino IDE. Bản mạch một cảm biến dùng TRIG GPIO5, ECHO GPIO18 (qua cầu phân áp 1 kΩ/2 kΩ), buzzer driver GPIO23 và nút silence GPIO27. HC-SR04 thường chạy 5 V; không nối ECHO trực tiếp vào ESP32. Xem `firmware/ultrasonic_esp32/wiring_diagram.svg` để đấu dây.

Đọc Serial:

```powershell
python -m iot_code.gateway.serial_reader --port COM5 --device-id HRC-ESP32-01
```

Thay `COM5` bằng cổng COM thực tế.

## Reset local chain

Dừng node bằng `Ctrl+C`, chạy lại `npm.cmd run node`, rồi deploy lại. Blockchain local reset sẽ làm contract address và toàn bộ transaction cũ mất hiệu lực.

## Bảo mật và giới hạn

- Không commit `.env`, private key thật, `node_modules`, Hardhat artifacts/cache hoặc model sinh tự động.
- Private key Hardhat trong log chỉ là key public dành cho local testing.
- Smart contract là audit/evidence layer; không điều khiển relay, motor hay E-Stop vật lý.

Xem thêm `contracts/README.md`, `web3/README.md`, `iot_code/README.md`, `docs/pipeline.md` và `REPORT_BLOCKCHAIN.md`.
