# Báo cáo tính chất blockchain và kịch bản demo HRC Safety Log

Ngày kiểm chứng: 30/09/2026

## 1. Kết luận ngắn

Project đã thể hiện đúng một mô hình **blockchain làm lớp bằng chứng/audit**, không phải bộ điều khiển E-Stop thời gian thực. Dữ liệu đo chi tiết và evidence JSON nằm off-chain; blockchain lưu commitment và metadata tối thiểu để có thể kiểm tra rằng một evidence đã được ghi bởi reporter hợp lệ tại một thời điểm cụ thể.

Các tính chất blockchain thể hiện rõ nhất là: tính bất biến của bản ghi sau khi transaction được xác nhận; khả năng kiểm chứng độc lập bằng transaction/event/state; chống ghi trùng commitment; phân quyền người ghi; tính minh bạch của sender, timestamp và event log; và khả năng phối hợp nhiều vai trò qua workflow permit/handoff.

Không nên trình bày rằng blockchain chứng minh cảm biến đo đúng, chứng minh motor đã dừng, hoặc tự động khôi phục E-Stop. Những điều đó không được blockchain bảo đảm trong implementation hiện tại.

## 2. Tính chất blockchain được thể hiện trong project

### 2.1. Integrity và tamper-evidence

Gateway tạo evidence envelope `sonarchain.evidence.v1`, serialize bằng canonical JSON (`sort_keys`, separator cố định), rồi tạo SHA-256 `evidence_hash`. File được lưu tại `data/evidence_outbox/<evidence_hash>.json`. Nếu sửa distance, severity, timestamp hoặc trường evidence khác, `EvidenceOutbox.verify()` sẽ phát hiện hash không khớp.

Khi ghi chain, `HRCSafetyLog.recordEvidence()` nhận `evidenceHash`, `deviceIdHash`, `measuredAt`, `severity`, `emergencyStop` và `evidenceSchema`; raw distance, confidence, model và policy vẫn nằm off-chain. Sau khi block được xác nhận, người kiểm tra có thể băm lại evidence gốc và đối chiếu với digest đã phát trong transaction/event.

Cách diễn đạt khi demo: “Blockchain không lưu file cảm biến; blockchain lưu dấu vân tay của file. Nếu file bị thay đổi sau đó, digest không còn khớp commitment đã ghi.”

### 2.2. Immutability và audit trail

Một transaction đã được mined không bị gateway sửa tại chỗ. `SafetyEvidenceRecorded` phát ra `evidenceHash`, device hash, schema, severity, emergency flag, measured timestamp, recorded timestamp và reporter. `SafetyEvent` cũng lưu reporter và thời điểm ghi.

Có hai thời gian cần nói rõ: `measuredAt` là lúc đo do evidence cung cấp; `recordedAt` là block timestamp lúc contract ghi nhận. Vì vậy blockchain chứng minh thời điểm commitment được ghi, không tự chứng minh đồng hồ cảm biến chính xác.

### 2.3. Chống duplicate và idempotency

Contract dùng `evidenceExists` và `eventExists`; cùng evidence/event hash lần thứ hai bị từ chối. Outbox cũng enqueue idempotent: cùng digest trả về cùng một file thay vì tạo bản ghi khác. Đây là minh họa cho đặc tính “một commitment đã xác nhận không ghi lại như một sự kiện mới”.

### 2.4. Phân quyền và trách nhiệm

`HRCSafetyLog` cho phép owner cấp/revoke reporter bằng `setReporter`. Chỉ owner hoặc reporter được ghi evidence. Contract lưu `reporter = msg.sender`, nên có thể truy nguyên ví nào chịu trách nhiệm submit.

`WorkPermitHandoff` thể hiện thêm phân quyền supervisor/gateway, vòng đời `PENDING -> APPROVED -> ACTIVE -> COMPLETED`, và participant được phép xác nhận handoff. Đây là audit workflow, không phải thay thế policy an toàn ngoài đời.

### 2.5. On-chain state machine cho E-Stop

Khi evidence có `emergencyStop=true`, contract bật `emergencyStopByDevice[device]` và `deviceLocked[device]`. Event SAFE sau đó không tự gỡ latch. Chỉ owner gọi `clearEmergencyStop()` mới gỡ trạng thái on-chain.

Đây là trạng thái logic/audit trên chain. Nó không cấp tín hiệu điện cho relay, không dừng motor và không thay thế local E-Stop tại ESP32/gateway. Local fail-safe phải dừng trước khi chờ RPC hoặc block confirmation.

### 2.6. Minh bạch và kiểm chứng độc lập

Người xem có thể dùng Hardhat test, script, dashboard hoặc RPC explorer để kiểm tra transaction receipt, event log, `getEvent()`, `evidenceExists`, `deviceLocked` và permit state. Không cần tin output in ra bởi gateway nếu có transaction hash và evidence file để đối chiếu.

## 3. Những gì blockchain KHÔNG chứng minh

Blockchain chỉ chứng minh một digest/metadata đã được ghi vào ledger bởi account được phép và transaction đã xác nhận. Nó không chứng minh cảm biến HC-SR04 đo đúng, firmware không bị thay đổi, device identity là thật, mô hình AI phân loại đúng, gateway không bị compromise trước khi băm, hay motor đã dừng.

`recordZoneEntry(permitId, telemetryEventHash)` hiện kiểm tra hash khác rỗng nhưng chưa truy vấn chéo để chứng minh hash đó tồn tại trong `HRCSafetyLog`. Vì vậy không được nói rằng WorkPermit đã xác thực SafetyLog commitment liên kết. Đây là khoảng trống thiết kế còn lại.

## 4. Kết quả kiểm chứng mã nguồn

Solidity test chạy trên artifact/compiler cache hiện có: **10 passing** gồm HRCSafetyLog, SafetyLog legacy và WorkPermitHandoff.

Python test hiện tại: **11 tests, 1 error**. Lỗi nằm ở `iot_code/gateway/__init__.py`: `ALERT_STATES` chỉ gồm `WARNING` và `SENSOR_FAULT`, nhưng test `test_emergency_telemetry_is_logged_as_emergency_stop` gửi `EMERGENCY` và không tạo file. Đây là lỗi hành vi còn tồn tại, không nên che giấu khi demo. Luồng mới `iot_code.gateway.pipeline.classify()` vẫn tạo `EMERGENCY` khi distance <= 30 cm.

Trong môi trường kiểm chứng này, deploy node local không hoàn tất vì Hardhat cần tải compiler 0.8.24 qua mạng bị proxy chặn. Vì vậy kết quả 10 passing dùng artifact đã compile sẵn; khi demo trên máy có npm/network đầy đủ, chạy lại `npm.cmd run compile` và `npm.cmd test`.

Ngoài ra, lệnh `--retry-outbox` hiện vẫn yêu cầu `--csv` vì `pipeline.main()` kiểm tra `if not args.csv` trước khi xử lý retry. Do đó lệnh retry được ghi trong README chưa chạy được nếu không truyền thêm CSV. Đây là điểm cần sửa trước khi trình diễn retry thực tế; không nên nói rằng retry CLI đã được kiểm chứng end-to-end.

## 5. Demo local đề nghị (không cần ESP32)

### Bước A — chạy test

Mở PowerShell:

```powershell
cd "C:\Users\P1 Gen 5\Downloads\Blockchain\contracts"
npm.cmd install
npm.cmd run compile
npm.cmd test
```

Kết quả mong đợi là 10 passing.

### Bước B — chạy local blockchain và deploy

Terminal 1:

```powershell
cd "C:\Users\P1 Gen 5\Downloads\Blockchain\contracts"
npm.cmd run node
```

Giữ cửa sổ này mở. RPC là `http://127.0.0.1:8545`, chain ID `31337`.

Terminal 2:

```powershell
cd "C:\Users\P1 Gen 5\Downloads\Blockchain\contracts"
npm.cmd run deploy
```

Ghi lại ba dòng output. Dùng `contract=` cho `HRCSafetyLog`; dùng `permitContract=` cho `WorkPermitHandoff`; không dùng `legacySafetyLog=` cho luồng evidence mới.

Chạy demo emergency:

```powershell
npm.cmd run demo
```

Kết quả cần chỉ ra `severity: 2`, `emergencyStop: true` và `deviceLocked: true`. Giải thích rằng event này đang dùng compatibility `recordEvent`; demo evidence v1 đầy đủ nên dùng pipeline ở bước D hoặc test contract evidence.

### Bước C — dashboard và permit/handoff

Terminal 3:

```powershell
cd "C:\Users\P1 Gen 5\Downloads\Blockchain"
py -m http.server 8080 -d web3
```

Trong MetaMask thêm Hardhat Local (`http://127.0.0.1:8545`, chain 31337), import Account #0 từ private key mà Hardhat node in ra (chỉ local). Mở `http://localhost:8080`, kết nối ví, nhập hai địa chỉ deploy, chạy mô phỏng và ghi event.

Để demo permit: tạo permit bằng requester, approve bằng supervisor/owner, ghi zone entry bằng gateway, xác nhận handoff bằng worker, rồi complete permit. Trên màn hình cần chỉ ra trạng thái thay đổi và event transaction. Nhấn mạnh dashboard hiện gọi `recordEvent` compatibility chứ chưa phải UI evidence envelope v1.

### Bước D — demo evidence, hash và outbox

Từ thư mục gốc:

```powershell
cd "C:\Users\P1 Gen 5\Downloads\Blockchain"
python -m unittest tests.test_evidence -v
python -m iot_code.gateway.pipeline `
  --csv ai_model/data/raw/son_dungyen_30_DANGER.csv `
  --limit 1 `
  --evidence-dir data/evidence_outbox
```

Mở file JSON vừa tạo. Chỉ cho khán giả thấy `schema`, `evidence_hash`, `measured_at`, `severity`, `emergency_stop` và các trường off-chain. Sao chép file, đổi `distance_cm` hoặc `severity`, chạy test `EvidenceOutbox.verify()`/`python -m unittest tests.test_evidence -v` để chứng minh tamper bị phát hiện. Không re-hash lại file đã sửa rồi gọi đó là bằng chứng cũ: digest mới chỉ chứng minh file mới tự nhất quán, không khớp commitment cũ.

Để ghi chain bằng pipeline, tạo `.env` từ `.env.example`, điền RPC local, địa chỉ `contract=` và private key Account #0 của Hardhat:

```powershell
python -m iot_code.gateway.pipeline `
  --csv ai_model/data/raw/son_dungyen_30_DANGER.csv `
  --limit 1 `
  --write-chain `
  --evidence-dir data/evidence_outbox
```

Kết quả đúng có `submission_status: confirmed` và `tx_hash`. Sau đó dùng receipt/event hoặc `getEvent(bytes32)` để đối chiếu `evidenceHash`, severity, flag và reporter.

## 6. Demo ESP32 thật

### Phần cứng

Dùng ESP32 DevKit, HC-SR04, nguồn 5 V và chung GND. Firmware chính trong `firmware/ultrasonic_esp32/ultrasonic_esp32.ino`/`iot_code/ultrasonic_esp32.ino` dùng TRIG GPIO25 và ECHO GPIO26; đường ECHO HC-SR04 5 V bắt buộc qua cầu phân áp xuống 3.3 V. Không nối ECHO 5 V trực tiếp vào GPIO ESP32. Kiểm tra đúng file firmware vì repository còn các bản tương thích cũ với sơ đồ chân khác.

Nạp bằng Arduino IDE, chọn ESP32 Dev Module, chọn COM đúng và mở Serial Monitor ở 115200 baud. Đưa tay/vật cản vào vùng đo: khoảng cách > 60 cm là SAFE; <= 60 cm là WARNING; <= 30 cm là EMERGENCY trong pipeline mới.

### Luồng demo an toàn

Đầu tiên chạy ESP32 và kiểm tra JSON serial dạng `{"device_id":"ESP32-HRC-01",...}`. Chạy parser off-chain:

```powershell
cd "C:\Users\P1 Gen 5\Downloads\Blockchain"
python -m iot_code.gateway.serial_reader --port COM5 --device-id HRC-ESP32-01
```

Thay `COM5` bằng COM thật. Lệnh này đọc và phân loại off-chain; bản serial reader hiện chưa tự nối outbox + `recordEvidence`, nên không trình bày lệnh này như full on-chain path. Để demo full chain đáng tin cậy, dùng CSV pipeline ở bước D hoặc cần nối serial reader vào `process_row(..., evidence_outbox=...)` và bật client chain trong một thay đổi code riêng.

Kịch bản nói trực tiếp: “Local safety decision và E-Stop cục bộ xảy ra trước blockchain. Gateway chỉ tạo evidence và submit commitment sau đó. Nếu RPC mất, evidence phải còn trong outbox để retry; motor không được chờ blockchain mới dừng.”

Không thử nghiệm bằng cách đưa người hoặc tay vào vùng nguy hiểm của robot. Chỉ dùng vật cản nhẹ và test bench, giữ mạch công suất/motor ở trạng thái an toàn.

## 7. Trình tự thuyết trình 5 phút

1. Nêu vấn đề: telemetry chi tiết cần lưu ngoài chain, nhưng cần audit trail khó sửa.
2. Cho xem một evidence JSON và SHA-256.
3. Cho xem `recordEvidence` chỉ nhận digest/device/timestamp/severity/flag/schema.
4. Ghi một event EMERGENCY, mở `getEvent`/event log và chỉ ra reporter + recordedAt + device lock.
5. Ghi SAFE tiếp theo và chỉ ra latch vẫn true; owner phải gọi clear.
6. Sửa file evidence và cho verify fail.
7. Tạo permit, approve, zone entry, handoff, complete để minh họa blockchain state machine.
8. Kết luận ranh giới: blockchain = integrity/audit/coordination; ESP32/gateway = real-time safety.

## 8. Các việc nên sửa trước khi demo chính thức

Sửa `ALERT_STATES` của package `iot_code.gateway` để bao gồm `EMERGENCY` và đặt `emergency_stop` đúng theo state; sửa thứ tự kiểm tra CLI để `--retry-outbox` chạy không cần `--csv`; nối serial reader vào evidence outbox + blockchain client nếu muốn tuyên bố demo ESP32 end-to-end; và cập nhật dashboard để gọi `recordEvidence` thay vì compatibility `recordEvent` nếu cần chứng minh đúng boundary v1. Sau mỗi thay đổi phải chạy lại cả Solidity và Python tests.
