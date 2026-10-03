# Hướng dẫn chạy SonarChain HRC Safety Log

Tài liệu này hướng dẫn hai cách demo project:

1. **Demo mô phỏng**: không cần ESP32 hoặc HC-SR04; có thể chạy dashboard và replay dữ liệu CSV.
2. **Demo phần cứng thật**: ESP32 đọc HC-SR04, xuất telemetry qua USB Serial, Python gateway xử lý và tạo evidence.

Project là prototype nghiên cứu. Blockchain chỉ là lớp audit/evidence và workflow; nó không thay thế E-Stop vật lý, không trực tiếp điều khiển motor/relay và không chứng minh cảm biến đo chính xác.

---

## 1. Kiến trúc demo

```text
MÔ PHỎNG
CSV / nút dashboard
        ↓
Python gateway hoặc dashboard
        ↓
Evidence JSON + SHA-256
        ↓
HRCSafetyLog trên Hardhat Local
        ↓
Dashboard + MetaMask
```

```text
PHẦN CỨNG THẬT
HC-SR04 → ESP32 → USB Serial → Python gateway
                                  ↓
                         Evidence outbox
                                  ↓
                         HRCSafetyLog
```

Nếu dùng MQTT thay cho USB Serial:

```text
ESP32/Wi-Fi publisher → Mosquitto → MQTT subscriber
                                      ↓
                              Python safety pipeline
                                      ↓
                              Evidence + blockchain
```

---

## 2. Yêu cầu cài đặt

Cài các phần mềm sau trên Windows:

- Node.js LTS và npm.
- Python 3.10 trở lên.
- Arduino IDE và ESP32 board package nếu chạy phần cứng.
- MetaMask nếu muốn ký transaction trên dashboard.
- Docker Desktop nếu muốn chạy MQTT broker bằng Docker.
- Driver USB của board ESP32 nếu Windows chưa tự nhận cổng COM.

Mở Command Prompt hoặc PowerShell. Nếu PowerShell chặn lệnh `npm`, dùng `npm.cmd`.

Kiểm tra cài đặt:

```cmd
node --version
npm.cmd --version
python --version
```

Cài thư viện Python từ thư mục project:

```cmd
cd /d "C:\Users\P1 Gen 5\Downloads\Blockchain"
python -m pip install -r requirements.txt
```

Nếu máy dùng lệnh `py` thay cho `python`, có thể thay toàn bộ `python` bằng `py`.

---

## 3. Demo nhanh chỉ với dashboard

Cách này dùng để trình bày giao diện và ngưỡng an toàn, chưa ghi transaction lên blockchain.

Mở terminal:

```cmd
cd /d "C:\Users\P1 Gen 5\Downloads\Blockchain"
python -m http.server 8080 --directory web3
```

Mở trình duyệt tại:

```text
http://localhost:8080
```

Trong dashboard:

1. Nhấn **Chạy mô phỏng**.
2. Dashboard chọn ngẫu nhiên một khoảng cách như `86.4`, `48.2`, `24.6` hoặc `76.5 cm`.
3. Ngưỡng được áp dụng như sau:
   - Lớn hơn `60 cm`: `SAFE`.
   - Từ `31 cm` đến `60 cm`: `WARNING`.
   - Nhỏ hơn hoặc bằng `30 cm`: `EMERGENCY`.
4. Khi có `EMERGENCY`, dashboard bật trạng thái E-STOP mô phỏng.
5. Quan sát **Safety event stream**. Event chưa ghi blockchain sẽ có nhãn `local proof`.

Ở chế độ này, chưa cần MetaMask, Hardhat hoặc contract.

---

## 4. Chạy blockchain local bằng Hardhat

Đây là phần nên chạy trước cả demo mô phỏng ghi on-chain và demo phần cứng.

### 4.1. Cài và compile smart contract

Mở Terminal 1:

```cmd
cd /d "C:\Users\P1 Gen 5\Downloads\Blockchain\contracts"
npm.cmd install
npm.cmd run compile
```

Nếu compile báo lỗi không tải được Solidity compiler do mạng/proxy, thử dùng môi trường đã có cache compiler hoặc kiểm tra kết nối mạng. Không dùng contract address cũ nếu đã reset node.

### 4.2. Chạy Hardhat node

Vẫn ở Terminal 1:

```cmd
npm.cmd run node
```

Giữ terminal này mở. Hardhat in ra danh sách account và private key local.

Thông tin mạng:

```text
RPC URL: http://127.0.0.1:8545
Chain ID: 31337
Network: Hardhat Local
```

Nếu thấy `EADDRINUSE`, có thể Hardhat node đã chạy. Không mở thêm node thứ hai.

### 4.3. Deploy contract

Mở Terminal 2:

```cmd
cd /d "C:\Users\P1 Gen 5\Downloads\Blockchain\contracts"
npm.cmd run deploy
```

Kết quả có dạng:

```text
deployer=0xf39Fd...
contract=0x...
permitContract=0x...
legacySafetyLog=0x...
```

Lưu lại hai địa chỉ:

```text
contract=       → HRCSafetyLog
permitContract= → WorkPermitHandoff
```

Không dùng địa chỉ `legacySafetyLog` cho luồng mới.

Mỗi lần dừng Hardhat node rồi chạy lại, blockchain local được tạo lại. Khi đó cần deploy lại và dùng địa chỉ contract mới.

---

## 5. Cấu hình MetaMask cho demo local

Trong MetaMask thêm network:

```text
Network name: Hardhat Local
New RPC URL: http://127.0.0.1:8545
Chain ID: 31337
Currency symbol: ETH
```

Import Account #0 bằng private key mà Hardhat in trong Terminal 1. Account #0 là deployer/owner của contract.

Địa chỉ owner mặc định thường là:

```text
0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266
```

Các private key Hardhat chỉ dành cho local test. Tuyệt đối không dùng hoặc gửi tiền thật cho các key này trên Ethereum Mainnet, Sepolia hay mạng công khai.

Có thể import thêm Account #1, #2, #3 để demo phân quyền.

---

## 6. Demo dashboard ghi event lên blockchain

Mở Terminal 3:

```cmd
cd /d "C:\Users\P1 Gen 5\Downloads\Blockchain"
python -m http.server 8080 --directory web3
```

Mở:

```text
http://localhost:8080
```

Trong dashboard:

1. Chọn network `Hardhat Local` trong MetaMask.
2. Kết nối bằng Account #0 hoặc một Reporter đã được cấp quyền.
3. Nhập địa chỉ sau dòng `contract=` vào ô **Contract HRCSafetyLog**.
4. Nhấn **Chạy mô phỏng**.
5. Chọn một event trong event stream.
6. Nhấn **Ghi event hiện tại lên chain**.
7. Xác nhận transaction trong MetaMask.
8. Chờ dashboard hiển thị transaction hash.

Nếu dashboard hiện `not reporter`, tài khoản đang ký chưa có quyền Reporter và cũng không phải owner.

Lưu ý: giao diện hiện tại dùng hàm tương thích `recordEvent(...)`. Gateway evidence v1 dùng digest/schema và lưu raw evidence ở off-chain.

---

## 7. Demo role và Work Permit

Dùng Account #0 owner trong panel **Ví & vai trò** để cấp quyền. Địa chỉ được nhập là tài khoản nhận role; tài khoản đang chọn trong MetaMask là người ký giao dịch.

Ví dụ:

```text
Account #1 → Supervisor
Account #2 → Gateway
Account #3 → Reporter
```

### Cấp Supervisor

```text
Địa chỉ account: 0x70997970C51812dc3A010C7d01b50e0d17dc79C8
Role: Supervisor · approve permit
```

Nhấn **Cấp role** và xác nhận bằng Account #0.

### Cấp Gateway

```text
Địa chỉ account: 0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC
Role: Gateway · ghi zone entry
```

Nhấn **Cấp role** và xác nhận bằng Account #0.

### Cấp Reporter

```text
Địa chỉ account: 0x90F79bf6EB2c4f870365E785982E1f101E93b906
Role: Reporter · ghi safety event
```

Nhấn **Cấp role** và xác nhận bằng Account #0.

### Chạy workflow permit

Trong panel **Work permit & robot handoff**:

1. Nhập **Contract WorkPermitHandoff** bằng địa chỉ sau dòng `permitContract=`.
2. Nhập ví người vận hành, hoặc để trống để dùng ví hiện tại.
3. Nhập:
   ```text
   Zone: ASSEMBLY-A
   Task: HANDOFF-001
   ```
4. Dùng requester/owner nhấn **Tạo permit**.
5. Chuyển MetaMask sang Supervisor, kết nối lại rồi nhấn **Approve**.
6. Chuyển MetaMask sang Gateway, kết nối lại rồi nhấn **Ghi zone entry**.
7. Khi permit ở `ACTIVE`, nhấn **Xác nhận handoff**.
8. Nhấn **Đóng permit**.

Trạng thái kỳ vọng:

```text
PENDING → APPROVED → ACTIVE → COMPLETED
```

Nếu đổi account làm mất `Permit ID` trên giao diện, permit vẫn tồn tại trên chain nhưng bản dashboard hiện tại chưa có chức năng tải permit lại bằng ID. Khi demo nhanh, có thể dùng owner cho toàn bộ workflow vì owner mặc định có quyền Supervisor và Gateway.

---

## 8. Chuẩn bị phần cứng thật

### 8.1. Linh kiện

- ESP32 DevKit.
- HC-SR04.
- Breadboard và dây nối.
- Cáp USB dữ liệu.
- Cầu phân áp cho chân ECHO.
- Có thể thêm buzzer và nút silence theo firmware đầy đủ.

### 8.2. Đấu nối firmware đầy đủ

Firmware chính nằm tại:

```text
firmware/ultrasonic_esp32/ultrasonic_esp32.ino
```

Sơ đồ chân của firmware này:

| Thiết bị | ESP32 |
|---|---:|
| HC-SR04 TRIG | GPIO5 |
| HC-SR04 ECHO | GPIO18, qua cầu phân áp |
| Buzzer driver | GPIO23 |
| Nút silence | GPIO27, nối về GND |
| VCC HC-SR04 | 5 V |
| GND HC-SR04 | GND chung |

**Cảnh báo điện áp:** HC-SR04 thường trả tín hiệu ECHO 5 V. Không nối ECHO 5 V trực tiếp vào GPIO ESP32. Dùng cầu phân áp, ví dụ 1 kΩ/2 kΩ theo sơ đồ của project, và kiểm tra mạch trước khi cấp nguồn.

Firmware tương thích đơn giản nằm tại:

```text
iot_code/ultrasonic_esp32.ino
```

Firmware này dùng:

```text
TRIG = GPIO25
ECHO = GPIO26
```

Không trộn hai sơ đồ chân. Chọn đúng file firmware thì đấu dây theo đúng file đó.

### 8.3. Nạp firmware

Trong Arduino IDE:

1. Cài ESP32 board package.
2. Chọn board phù hợp, thường là `ESP32 Dev Module`.
3. Chọn đúng cổng COM.
4. Mở file `.ino` tương ứng.
5. Chọn baud Serial `115200`.
6. Verify rồi Upload.
7. Mở Serial Monitor ở `115200 baud`.

Khi chạy, ESP32 xuất JSON tương tự:

```json
{"device_id":"ESP32-HRC-01","sensor_id":"HC-SR04","timestamp_ms":12345,"distance_cm":42.7,"state":"WARNING","emergency_stop":false,"buzzer_on":false,"buzzer_silenced":false,"seq":10}
```

Đưa tay hoặc vật thể ra xa/gần cảm biến để thấy `SAFE`, `WARNING` và `EMERGENCY`.

---

## 9. Chạy gateway với ESP32 qua USB Serial

Xác định cổng COM trong Arduino IDE hoặc Device Manager, ví dụ `COM5`.

Mở Terminal:

```cmd
cd /d "C:\Users\P1 Gen 5\Downloads\Blockchain"
python -m iot_code.gateway.serial_reader --port COM5 --baud 115200 --device-id HRC-ESP32-01
```

Thay `COM5` bằng cổng thật.

Gateway sẽ:

1. Đọc từng dòng JSON từ ESP32.
2. Bỏ qua dòng khởi động không phải JSON telemetry.
3. Lấy `distance_cm`.
4. Phân loại theo ngưỡng:
   ```text
   distance <= 30 cm → EMERGENCY
   distance <= 60 cm → WARNING
   distance > 60 cm  → SAFE
   ```
5. In kết quả xử lý ra terminal.

Để kiểm tra bằng phần cứng thật, trình bày theo trình tự:

```text
Đưa vật thể ra xa       → SAFE
Đưa vào khoảng 31–60 cm → WARNING
Đưa vào ≤ 30 cm         → EMERGENCY
Đưa vật thể ra xa lại   → SAFE
```

Trong firmware đầy đủ, `EMERGENCY` hoặc `SENSOR_FAULT` bật buzzer. Đây là cảnh báo cục bộ; không phụ thuộc blockchain.

### Lưu ý về Serial hiện tại

`serial_reader.py` là reader kiểm tra luồng Serial và in kết quả pipeline. Luồng evidence outbox/ghi blockchain hoàn chỉnh hiện được hỗ trợ rõ nhất qua CSV pipeline và MQTT subscriber. Vì vậy có hai cách trình bày phần cứng:

- **Demo hardware + gateway:** chạy `serial_reader.py`, chứng minh ESP32 đo thật và gateway phân loại thật; ghi on-chain bằng dashboard hoặc replay evidence riêng.
- **Demo hardware + blockchain end-to-end:** mở rộng serial reader để truyền kết quả vào `EvidenceOutbox`, sau đó gọi `SafetyLogClient.record_evidence`, hoặc dùng MQTT subscriber nếu ESP32 có Wi-Fi publisher.

Không nên tuyên bố `serial_reader.py` hiện tự động ghi chain nếu chưa bổ sung phần tích hợp đó.

---

## 10. Demo phần cứng kết hợp dashboard

Cách trình bày an toàn và dễ hiểu:

### Terminal 1

```cmd
cd /d "C:\Users\P1 Gen 5\Downloads\Blockchain\contracts"
npm.cmd run node
```

### Terminal 2

```cmd
cd /d "C:\Users\P1 Gen 5\Downloads\Blockchain\contracts"
npm.cmd run deploy
```

Ghi lại `contract=` và `permitContract=`.

### Terminal 3

```cmd
cd /d "C:\Users\P1 Gen 5\Downloads\Blockchain"
python -m iot_code.gateway.serial_reader --port COM5 --baud 115200 --device-id HRC-ESP32-01
```

### Terminal 4

```cmd
cd /d "C:\Users\P1 Gen 5\Downloads\Blockchain"
python -m http.server 8080 --directory web3
```

Trong dashboard:

1. Chuyển MetaMask sang Hardhat Local.
2. Kết nối owner hoặc Reporter.
3. Nhập địa chỉ `HRCSafetyLog`.
4. Cho ESP32 đo một giá trị nguy hiểm.
5. Quan sát terminal gateway in `EMERGENCY`.
6. Quan sát buzzer/cảnh báo cục bộ nếu dùng firmware đầy đủ.
7. Trên dashboard, chạy mô phỏng tương ứng hoặc ghi event bằng nút **Ghi event hiện tại lên chain**.
8. Xác nhận transaction.
9. Giải thích rõ: E-Stop thật xảy ra tại edge; blockchain chỉ ghi bằng chứng của sự kiện.

---

## 11. Chạy MQTT local tùy chọn

MQTT không bắt buộc cho demo USB Serial. Dùng MQTT khi muốn minh họa đường truyền telemetry qua broker.

### 11.1. Với Docker Desktop

Kiểm tra Docker:

```cmd
docker --version
docker compose version
```

Khởi động broker:

```cmd
cd /d "C:\Users\P1 Gen 5\Downloads\Blockchain"
docker compose -f docker-compose.mqtt.yml up -d
```

Broker mặc định:

```text
MQTT: 127.0.0.1:1883
WebSocket: 127.0.0.1:9001
Topic: hrc/telemetry/#
```

Cài `paho-mqtt` nếu chưa cài:

```cmd
python -m pip install -r requirements.txt
```

Chạy subscriber:

```cmd
python -m iot_code.gateway.mqtt_subscriber --host 127.0.0.1 --port 1883 --topic hrc/telemetry/# --device-id HRC-ESP32-01
```

Mở terminal khác và gửi telemetry giả lập:

```cmd
docker exec hrc-mqtt mosquitto_pub -h 127.0.0.1 -t hrc/telemetry/HRC-ESP32-01 -q 1 -m "{\"device_id\":\"HRC-ESP32-01\",\"timestamp_ms\":1730000000000,\"distance_cm\":24.6}"
```

Kết quả kỳ vọng:

```text
severity = EMERGENCY
emergency_stop = true
submission_status = queued
```

### 11.2. Nếu không có Docker

Có thể cài Mosquitto native trên Windows, sau đó chạy broker và `mosquitto_pub.exe` trực tiếp. Hoặc bỏ qua MQTT và dùng USB Serial cho demo phần cứng.

MQTT trong project hiện cho phép anonymous chỉ để demo local. Không expose broker ra Internet khi chưa có username/password và TLS.

Dừng broker:

```cmd
docker compose -f docker-compose.mqtt.yml down
```

---

## 12. Replay CSV và ghi evidence lên chain

Đây là cách mô phỏng gateway gần với luồng blockchain mới.

Không ghi chain:

```cmd
cd /d "C:\Users\P1 Gen 5\Downloads\Blockchain"
python -m iot_code.gateway.pipeline --csv ai_model/data/raw/son_dungyen_30_DANGER.csv --limit 1 --evidence-dir data/evidence_outbox
```

Evidence được lưu trong:

```text
data/evidence_outbox/
```

Để ghi chain, tạo file `.env` từ `.env.example` và điền:

```text
RPC_URL=http://127.0.0.1:8545
CONTRACT_ADDRESS=<địa chỉ contract= sau deploy>
PRIVATE_KEY=<private key Account #0 local>
```

Sau đó chạy:

```cmd
python -m iot_code.gateway.pipeline --csv ai_model/data/raw/son_dungyen_30_DANGER.csv --limit 1 --write-chain --evidence-dir data/evidence_outbox
```

Luồng này lưu evidence JSON trước, sau đó chỉ gửi commitment/metadata cần thiết lên chain. Raw distance, confidence, model và policy version không được lưu trực tiếp lên blockchain.

Không dùng `PRIVATE_KEY` Hardhat trên mạng thật.

---

## 13. Kiểm tra project trước buổi demo

Chạy Python tests:

```cmd
cd /d "C:\Users\P1 Gen 5\Downloads\Blockchain"
python -m unittest discover -s tests -p "test_*.py" -v
```

Chạy compile check:

```cmd
python -m compileall -q iot_code
```

Chạy Solidity tests:

```cmd
cd /d "C:\Users\P1 Gen 5\Downloads\Blockchain\contracts"
npm.cmd test
```

Kiểm tra dashboard:

```text
http://localhost:8080
```

Kiểm tra trước khi trình bày:

- Hardhat node đang chạy ở chain `31337`.
- Contract address là địa chỉ của lần deploy hiện tại.
- MetaMask không ở Ethereum Mainnet hoặc chain khác.
- Owner được dùng khi cấp role.
- ECHO HC-SR04 đi qua cầu phân áp.
- Cổng COM không bị Arduino Serial Monitor chiếm khi chạy Python reader.
- Không dùng cùng lúc hai chương trình mở cùng một cổng Serial.

---

## 14. Các lỗi thường gặp

### `not owner`

MetaMask đang dùng account không phải deployer. Chuyển sang Account #0 owner rồi cấp role hoặc clear E-Stop.

### `not reporter`

Tài khoản đang ký chưa có Reporter role trên `HRCSafetyLog`.

### `not supervisor`

Tài khoản đang ký chưa có Supervisor role trên `WorkPermitHandoff`.

### `not gateway`

Tài khoản đang ký chưa có Gateway role trên `WorkPermitHandoff`.

### `permit not approved`

Chưa dùng Supervisor nhấn **Approve** nhưng đã nhấn **Ghi zone entry**.

### `permit not started` hoặc `permit expired`

Thời gian hiện tại nằm ngoài khoảng hiệu lực của permit.

### `docker is not recognized`

Docker Desktop chưa cài hoặc chưa có trong PATH. Dùng USB Serial hoặc cài Mosquitto native nếu chỉ cần MQTT local.

### `COM port đang bị sử dụng`

Đóng Arduino Serial Monitor/Serial Plotter và mọi gateway khác trước khi chạy `serial_reader.py`.

### Dashboard báo transaction thất bại sau khi reset Hardhat

Contract address cũ không còn tồn tại trên chain mới. Chạy deploy lại và nhập địa chỉ mới.

### Không thấy dữ liệu ESP32

Kiểm tra cáp USB là cáp dữ liệu, đúng board, đúng COM, baud `115200`, dây GND chung và nguồn cảm biến.

### Khoảng cách luôn là `SENSOR_FAULT`

Kiểm tra TRIG/ECHO, nguồn HC-SR04, GND chung, hướng cảm biến và cầu phân áp ở ECHO. Không nối ECHO 5 V trực tiếp vào ESP32.

---

## 15. Kịch bản thuyết trình ngắn

Có thể trình bày theo thứ tự sau:

1. Mở dashboard và giải thích đây là lớp hiển thị/audit.
2. Cho chạy mô phỏng `SAFE`, `WARNING`, `EMERGENCY`.
3. Giải thích ngưỡng `60 cm` và `30 cm`.
4. Kết nối MetaMask Hardhat Local.
5. Ghi một event lên `HRCSafetyLog` và cho xem transaction hash.
6. Cấp `Supervisor`, `Gateway`, `Reporter` bằng owner.
7. Tạo permit, Supervisor approve, Gateway ghi zone entry.
8. Nếu có phần cứng, cho ESP32 đọc HC-SR04 thật và tạo `WARNING`/`EMERGENCY`.
9. Nhấn mạnh khi blockchain hoặc MQTT hỏng, quyết định dừng cục bộ vẫn phải tồn tại.

Thông điệp kết luận:

> ESP32/HC-SR04 tạo quyết định safety tại edge. Gateway tạo bằng chứng. Blockchain lưu commitment và workflow có thể kiểm chứng. Blockchain không phải là bộ điều khiển E-Stop.

---

## 16. Giới hạn an toàn

- Đây là prototype giáo dục, chưa phải hệ thống safety-certified.
- Không dùng buzzer, dashboard hoặc blockchain làm E-Stop duy nhất cho người và máy móc.
- Không nối tín hiệu 5 V trực tiếp vào GPIO 3.3 V của ESP32.
- Không expose MQTT anonymous ra Internet.
- Không đưa private key thật hoặc tiền thật vào Hardhat.
- Không khẳng định blockchain chứng minh sensor đúng hoặc motor đã dừng.
- Nếu dùng robot/motor thật, phải có thiết kế safety độc lập, E-Stop phần cứng và đánh giá bởi người có chuyên môn.
