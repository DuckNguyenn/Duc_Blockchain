# Cách chạy SonarChain — phiên bản đã rà soát ngày 05/10/2026

Luồng chính hiện tại là **một HC-SR04 → ESP32/ESP-IDF/TFLite Micro → USB Serial → Python gateway → SQLite/evidence → API → dashboard**. Blockchain là phần audit tùy chọn. Các notebook IsolationForest, Arduino và tài liệu hai cảm biến thuộc các phiên bản trước; không dùng chúng để export model cho firmware TinyML hiện tại.

## 1. Cài môi trường

Chạy PowerShell từ thư mục project:

```powershell
Set-Location 'C:\Users\P1 Gen 5\Downloads\Blockchain'
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Nếu đã có `.venv`, bỏ lệnh tạo môi trường. Các lệnh dưới đây dùng trực tiếp Python của môi trường nên không cần `Activate.ps1`. TensorFlow được kiểm tra bằng Python 3.12 trên máy này; chỉ cần cài khi huấn luyện/export:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-tinyml.txt
```

Cài Node.js/npm nếu chưa có. Dùng `npm.cmd` để tránh PowerShell chặn file `npm.ps1`:

```powershell
Set-Location contracts
npm.cmd ci
npm.cmd run compile
Set-Location ..
```

ESP-IDF 5.5.4 và esp-tflite-micro 1.4.1 được dùng để kiểm tra firmware. MetaMask chỉ cần cho các giao dịch qua dashboard.

## 2. Chạy dashboard mô phỏng, không cần ESP32

```powershell
.\.venv\Scripts\python.exe -m http.server 8080 --directory web3
```

Mở **http://localhost:8080**, chọn **Mô phỏng**, nhấn **Mẫu mô phỏng tiếp theo**. Chuỗi cố định: 86,4 → 48,2 → 24,6 → 76,5 cm. Mẫu gần kích hoạt yêu cầu E-STOP mô phỏng; sau mẫu SAFE, dùng nút gỡ mô phỏng. Mỗi mẫu xuất hiện trong event stream. Số giao dịch xác nhận chỉ tăng khi có transaction thành công.

Không cần ví để mô phỏng. Chuyển sang nguồn ESP32 sẽ tắt nút tạo mẫu giả. Khóa trên chain được hiển thị và gỡ riêng; nó không điều khiển ESP32.

## 3. Huấn luyện và chọn model nhúng

Notebook mới: [`ai_model/notebooks/esp32_grouped_training.ipynb`](ai_model/notebooks/esp32_grouped_training.ipynb). Notebook độc lập có thể chạy trên Kaggle cùng `dataset_3class.csv`, không cần upload toàn bộ code project. Nếu tìm thấy nhiều dataset, chỉ định đúng `DATASET_PATH`.

Hoặc chạy từ thư mục gốc:

```powershell
.\.venv\Scripts\python.exe -m ai_model.train_keras_tflite --check-data
.\.venv\Scripts\python.exe -m ai_model.train_keras_tflite --epochs 150
```

Script dùng 3 feature đúng firmware: `distance_cm`, `distance_delta_3`, `distance_std_5`. Tách recording trước khi tạo feature. Train/validation/test đều đủ SAFE, APPROACHING, EMERGENCY. Scaler và representative dataset chỉ lấy train. Bốn ứng viên: linear softmax, Dense(4), Dense(8), Dense(16)→Dense(8). Chọn theo validation macro-F1, dùng test sau khi chọn; không đổi seed để tìm điểm cao.

Artifact ở `ai_model/artifacts/esp32_candidate/`:

| File | Công dụng |
|---|---|
| `model_data.cc`, `model_data.h` | Model INT8 và mean/scale cho C++ |
| `ultrasonic_safety_int8.tflite` | Model để đánh giá bằng interpreter |
| `model_metadata.json` | Input/output, feature order, quantization, thời gian lấy mẫu |
| `metrics.json`, `history.json` | Metric từng ứng viên, float/INT8 và learning curves |
| `split_manifest.json` | Các recording thuộc từng tập |
| `parity_vectors.json` | Input/output cố định để đối chiếu thiết bị |

Kết quả lần chạy này: MLP **3→16→8→3**, 227 tham số, 3.456 byte; validation accuracy **88,91%**, test INT8 accuracy **91,14%**, macro-F1 **0,8937**, recall EMERGENCY **100%**. Đây là kết quả offline trên một split, không phải độ chính xác đã đo trên board.

**Chu kỳ lấy mẫu:** median dataset là khoảng **176 ms**, firmware đang đặt **100 ms** cộng thời gian đo/inference. Vì delta/std phụ thuộc cửa sổ theo số mẫu, cần thu thêm dữ liệu ở đúng cadence firmware trước khi kết luận accuracy thực tế. Không dùng phần giảm mẫu 1 giây của notebook cũ để nạp firmware 100 ms.

## 4. Build/nạp ESP32

Mở **ESP-IDF terminal**, vào `esp32_safety_idf`. Pin: TRIG GPIO5, ECHO GPIO18 qua chuyển mức 5 V→3,3 V, buzzer GPIO23, nút silence GPIO27→GND. Không dùng pin map GPIO2/hai cảm biến từ README cũ.

Để dùng candidate, copy **cùng lúc** hai file sau; nên sao lưu model đang dùng trước:

```powershell
Copy-Item ai_model/artifacts/esp32_candidate/model_data.cc esp32_safety_idf/main/model/model_data.cc
Copy-Item ai_model/artifacts/esp32_candidate/model_data.h esp32_safety_idf/main/model/model_data.h
```

Hai lệnh copy trên chạy từ thư mục gốc. Sau đó, trong ESP-IDF terminal:

```powershell
Set-Location esp32_safety_idf
idf.py build
idf.py -p COM5 flash monitor
```

Thay COM5 bằng cổng thực tế. Thoát monitor bằng **Ctrl+]** trước khi mở Serial gateway. Nếu board là ESP32-S3/C3, cần đổi target và kiểm tra pin/toolchain tương ứng; cấu hình đã kiểm tra ở đây là `esp32`.

Firmware kiểm tra input `[1,3]`, output `[1,3]`, kiểu INT8 và scale hợp lệ. Hard rule `distance <=30 cm → EMERGENCY` luôn ưu tiên; AI được phép nâng lên EMERGENCY ở phía ngoài. Mẫu lỗi xóa history. Buzzer silence chỉ tắt âm; chưa có relay/motor E-Stop hay cơ chế reset latch vật lý.

Đối chiếu các vector export trên board, đo thời gian `Invoke()` và arena thực tế trước khi sử dụng. Build thành công không thay thế các phép đo này.

## 5. ESP32 → gateway → dashboard thật

Ba terminal đều mở từ thư mục gốc project.

**Terminal 1 — Serial:**

```powershell
.\.venv\Scripts\python.exe -m iot_code.gateway.serial_reader --port COM5 --baud 115200 --database data/telemetry.db
```

**Terminal 2 — API:**

```powershell
.\.venv\Scripts\python.exe -m iot_code.gateway.api --host 127.0.0.1 --port 8000 --database data/telemetry.db
```

**Terminal 3 — dashboard:**

```powershell
.\.venv\Scripts\python.exe -m http.server 8080 --directory web3
```

Mở http://localhost:8080, chọn **ESP32 · gateway thật**. Đúng dữ liệu sẽ hiển thị `GATEWAY · LIVE`. Mẫu quá 5 giây hoặc API mất kết nối hiển thị chờ dữ liệu. `null`/timeout/AI_FAULT được ghi và hiển thị, không giữ khoảng cách SAFE cũ. APPROACHING trên ESP32 được gateway chuyển thành WARNING; raw JSON vẫn nằm trong `raw_payload` của SQLite.

Kiểm tra nhanh:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/health
Invoke-RestMethod http://127.0.0.1:8000/api/telemetry/latest
```

SQLite lưu mọi mẫu; evidence JSON ở `data/evidence_outbox/`. Device ID lấy từ telemetry; firmware hiện phát `ESP32-HRC-01`. `timestamp_ms` của board là uptime, không phải Unix timestamp; gateway dùng thời gian nhận UTC nếu firmware không gửi `measured_at`.

## 6. Blockchain local và MetaMask

**Terminal 4**, từ `contracts/`:

```powershell
Set-Location 'C:\Users\P1 Gen 5\Downloads\Blockchain\contracts'
npm.cmd run node
```

**Terminal 5**, từ `contracts/`:

```powershell
Set-Location 'C:\Users\P1 Gen 5\Downloads\Blockchain\contracts'
npm.cmd run deploy
```

Lấy `contract=` cho HRCSafetyLog và `permitContract=` cho WorkPermitHandoff. MetaMask: RPC **http://127.0.0.1:8545**, chain ID **31337**, tên Hardhat Local. Import một account dev do Hardhat in ra. Nhập hai contract trên dashboard và kết nối ví. Nếu restart node, deploy lại và kiểm tra contract trên mạng ví đang dùng.

Chọn một cách submit EMERGENCY:

- **Gateway tự submit:** cấu hình env và thêm `--write-chain` như bên dưới. Dashboard dùng để quan sát.
- **Dashboard submit thủ công:** gateway chạy không `--write-chain`; nhập contract, dùng owner/Reporter, nhấn **Ghi EMERGENCY chưa gửi lên chain** và xác nhận MetaMask. Gateway commitment được chuẩn hóa SHA-256 thành bytes32, gọi `recordEvidence`.

Không dùng hai cách submit cho cùng commitment. Contract chống trùng; nếu dashboard gửi thủ công, database/outbox chưa tự cập nhật transaction từ trình duyệt. Giữ transaction hash để đối chiếu. Event mô phỏng dùng `recordEvent` và được gắn nhãn mô phỏng.

EMERGENCY vẫn tự phát yêu cầu E-STOP khi chạy off-chain. Để đọc COM5 mà không cần private key hoặc gửi giao dịch, dùng:

```bat
.\.venv\Scripts\python.exe -m iot_code.gateway.serial_reader --port COM5
```

Trên dashboard, chọn **ESP32 · gateway thật**. E-STOP giám sát ở banner được kích hoạt từ telemetry; trạng thái **Khóa trên chain** chỉ đổi khi có giao dịch. Supervisor dùng nút **gỡ sau kiểm tra** khi có mẫu SAFE mới; nút **gỡ khóa trên chain** chỉ dành cho khóa đã ghi blockchain.

Serial gateway tự ghi chain dùng biến môi trường trong **PowerShell**. Trong terminal gateway, chạy từ thư mục gốc và nhập giá trị thật khi PowerShell hỏi:

```powershell
Set-Location 'C:\Users\P1 Gen 5\Downloads\Blockchain'
$env:RPC_URL='http://127.0.0.1:8545'
$env:CONTRACT_ADDRESS=(Read-Host 'Dan dia chi sau contract= trong output deploy').Trim()
$env:PRIVATE_KEY=(Read-Host 'Dan Private Key cua Account #0 (Owner) trong terminal Hardhat').Trim()
.\.venv\Scripts\python.exe -m iot_code.gateway.serial_reader --port COM5 --write-chain
```

`CONTRACT_ADDRESS` có dạng `0x` + 40 ký tự hex; lấy giá trị sau `contract=`, không lấy `permitContract=` hay địa chỉ ví. Dòng **Private Key** của Account #0 là khóa Owner/deployer mặc định; cũng có thể dùng tài khoản đã được cấp Reporter. Không nhập nguyên câu mô tả như `private key account Hardhat local`. Biến `$env:` chỉ áp dụng trong terminal đang chạy gateway và các tiến trình con của nó; giữ terminal Hardhat node mở. Thoát `idf.py monitor`/Serial Monitor trước khi gateway mở `COM5`.

Nếu cửa sổ là **CMD** (`C:\...>`), dùng cú pháp `set`:

```bat
set "RPC_URL=http://127.0.0.1:8545"
set "CONTRACT_ADDRESS=DIA_CHI_HRCSAFETYLOG_VUA_DEPLOY"
set "PRIVATE_KEY=PRIVATE_KEY_THAT_CUA_REPORTER_HOAC_OWNER"
.\.venv\Scripts\python.exe -m iot_code.gateway.serial_reader --port COM5 --write-chain
```

Thay các giá trị mẫu trước khi chạy. Private key là `0x` + **64 ký tự hex**, lấy từ dòng **Private Key** của tài khoản trong terminal Hardhat. Dòng **Account** là địa chỉ ví (`0x` + 40 ký tự), không dùng làm private key. Tài khoản gửi giao dịch cần Reporter ở HRCSafetyLog hoặc là Owner; Supervisor không mặc nhiên có quyền ghi log.

Nên dùng **Reporter riêng cho Serial gateway** (ví dụ Account #1), còn Owner và Supervisor thao tác qua MetaMask. Dừng gateway trước khi dùng Owner cấp Reporter, rồi đặt `PRIVATE_KEY` của Reporter trong terminal gateway và chạy lại. Hai chương trình cùng ký bằng một ví có thể chọn trùng nonce, kể cả khi gateway đọc nonce `pending`.

Chỉ EMERGENCY lên chain; SAFE/WARNING/SENSOR_FAULT off-chain. Gateway lưu mọi mẫu vào SQLite ngay, gửi giao dịch trên luồng riêng để chờ receipt không làm đứng telemetry/E-STOP giám sát. Sau xác nhận, terminal in thêm `submission_status: confirmed` kèm `tx_hash`; dashboard cập nhật số on-chain và lịch sử EMERGENCY trong tối đa khoảng 5 giây. RPC lỗi giữ evidence pending. Retry sau khi RPC hoạt động:

```powershell
.\.venv\Scripts\python.exe -m iot_code.gateway.pipeline --retry-outbox --write-chain
```

Supervisor của HRCSafetyLog có thể **gỡ khóa trên chain** bằng nút riêng. Việc này không gửi lệnh xuống ESP32 và không chứng minh robot đã dừng.

Nếu ô chọn là ESP32 mà nhãn vẫn `MÔ PHỎNG`, hoặc khoảng cách giữ ở `86.4`, nhấn **Ctrl+F5** để nạp `app.js` mới rồi chọn lại **ESP32 · gateway thật**. Nhãn đúng là `GATEWAY · LIVE`, nút mô phỏng bị khóa. Sau khi cập nhật mã gateway/API, dừng hai terminal đó bằng Ctrl+C rồi chạy lại cùng database; không cần khởi động lại Hardhat hay deploy contract cho sửa lỗi đồng bộ này.

### Lỗi MetaMask `Nonce too low`

Ví dụ `Expected nonce to be 2587 but got 2586`: nonce đã được dùng bởi một giao dịch khác. Khi gateway dùng khóa Owner và MetaMask cũng mở Owner, hai nơi có thể tranh nonce.

1. Dừng Serial gateway bằng Ctrl+C và kiểm tra MetaMask đang ở mạng Hardhat local (`31337`, RPC `http://127.0.0.1:8545`).
2. Trên MetaMask Extension: **Settings → Developer tools → Delete activity and nonce data**, rồi tải lại dashboard bằng Ctrl+F5. Việc này xóa lịch sử/nonce cục bộ của mạng đang chọn. Xem [hướng dẫn MetaMask](https://support.metamask.io/configure/accounts/how-to-clear-your-account-activity-reset-account).
3. Dùng Owner cấp role **Reporter** cho một tài khoản riêng (Account #1 của Hardhat). Dùng khóa Reporter cho `PRIVATE_KEY` của gateway; Owner/Supervisor ký thao tác web bằng ví của mình.
4. Nếu node đã khởi động lại, kiểm tra địa chỉ contract của lần deploy hiện tại, rồi cấp lại role nếu contract được deploy mới. Địa chỉ cũ có thể không còn code; lấy `contract=` và `permitContract=` từ terminal deploy.

Không cố định nonce theo số trong thông báo: nó có thể đổi ngay khi gateway gửi thêm giao dịch. Gateway đọc nonce `pending`, nhưng việc tách ví mới tránh tranh nonce với MetaMask.

## 7. Work permit

Owner cấp Supervisor/Gateway bằng panel role. Requester tạo permit, Supervisor approve, Gateway ghi zone entry, worker/requester xác nhận handoff rồi đóng permit. Cần tạo một telemetry event của nguồn đang chọn trước khi ghi zone entry. Quyền và thời hạn được contract kiểm tra; đổi account MetaMask theo vai trò cần dùng.

Zone entry/handoff là lời xác nhận của tài khoản, không phải chứng nhận vị trí người hay chuyển động robot. Permit đang theo phiên trình duyệt; refresh trang chưa khôi phục permit đã tạo.

## 8. Replay CSV và MQTT tùy chọn

Replay CLI để kiểm tra evidence, không thay thế luồng SQLite/Serial:

```powershell
.\.venv\Scripts\python.exe -m iot_code.gateway.pipeline --csv ai_model/data/single_sensor/processed_3class/recordings/son_dungyen_20_DANGER.csv --limit 3 --model ai_model/artifacts/no_legacy_model.joblib
```

Đường model không tồn tại chủ động giữ replay threshold-only; không nạp joblib IsolationForest cũ khi đang đánh giá TinyML. MQTT xem `iot_code/README.md`; firmware ESP-IDF hiện phát Serial, chưa có publisher Wi-Fi. MQTT subscriber hiện lưu outbox, chưa đồng bộ SQLite/API như luồng Serial.

## 9. Kiểm thử

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
node --test tests/dashboard.test.cjs
Set-Location contracts
npm.cmd test
Set-Location ..
.\.venv\Scripts\python.exe -m tools.verify_esp32_candidate
```

Lệnh cuối cần g++ trên PATH và TensorFlow; nó so sánh feature Python với hàm C++ thật của firmware và kiểm tra hard rule. Kiểm tra giao diện bằng Edge headless tùy chọn:

```powershell
.\.venv\Scripts\python.exe -m pip install playwright
.\.venv\Scripts\python.exe tools/check_dashboard_browser.py
```

Ảnh ở `docs/dashboard_desktop.png` và `docs/dashboard_mobile.png`. Báo cáo chi tiết model/notebook/Web3: [`docs/DANH_GIA_PROJECT_VA_MODEL.md`](docs/DANH_GIA_PROJECT_VA_MODEL.md).

## 10. Lỗi thường gặp

- **COM bị chiếm:** đóng Serial Monitor và `idf.py monitor` trước khi chạy gateway.
- **Gateway chờ dữ liệu:** kiểm tra cổng COM, baud 115200, API port 8000 và các tiến trình dùng cùng `data/telemetry.db`.
- **Không có contract/quyền Reporter:** chọn đúng mạng ví, deploy lại nếu node reset, cấp quyền bằng owner.
- **Model không khởi tạo:** kiểm tra input 3 feature, copy đủ cc/h, schema/operator/arena. Model 6 feature của notebook cũ sẽ bị từ chối.
- **Accuracy trên board giảm:** kiểm tra sampling cadence, feature order, std ddof=1, normalization, reset window sau timeout và INT8 saturation; thu thêm session độc lập.
