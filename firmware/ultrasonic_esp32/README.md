# Firmware ESP32: HC-SR04 + buzzer + nút silence

Firmware dành cho **ESP32 DevKit v1**, một cảm biến **HC-SR04**, một **active buzzer** và một nút nhấn thường mở. Khi khoảng cách `<= 30 cm`, còi bật. Nhấn nút sẽ tắt còi tạm thời; khi vật cản ra khỏi vùng nguy hiểm (`> 60 cm`), hệ thống tự re-arm cho lần cảnh báo kế tiếp.

> Đây là mạch cảnh báo/prototype, không phải E-stop safety-rated. Nút trong mạch này chỉ là nút **silence/acknowledge** cho còi; không được dùng làm mạch dừng an toàn duy nhất cho người hoặc máy.

## Sơ đồ chân

| Thiết bị | Chân | Nối tới | Ghi chú |
|---|---|---|---|
| HC-SR04 | VCC | VIN/5V ESP32 | Cảm biến dùng 5 V |
| HC-SR04 | GND | GND ESP32 | Chung mass |
| HC-SR04 | TRIG | GPIO5 | Tín hiệu 3.3 V từ ESP32 |
| HC-SR04 | ECHO | R1 = 1 kΩ → nút chia áp | Không nối trực tiếp vào ESP32 |
| Nút chia áp | Nút giữa R1/R2 | GPIO18 | R2 = 2 kΩ từ nút này xuống GND |
| Buzzer driver | GPIO23 → Rb = 1 kΩ → base NPN | 2N2222/BC547 | Không kéo buzzer công suất trực tiếp bằng GPIO |
| Buzzer | Cực + | VIN/5V | Với active buzzer loại phù hợp nguồn |
| Buzzer | Cực − | Collector NPN | Emitter NPN nối GND |
| Nút nhấn | Một chân | GPIO27 | Dùng `INPUT_PULLUP` |
| Nút nhấn | Chân còn lại | GND | Nhấn = LOW |

### Cầu phân áp ECHO

Dùng **R1 = 1 kΩ** từ chân `ECHO` của HC-SR04 đến nút tín hiệu, và **R2 = 2 kΩ** từ nút tín hiệu xuống `GND`. Điện áp tại GPIO18 xấp xỉ `5 V × 2/(1+2) = 3.33 V`.

**Không được đưa ECHO 5 V trực tiếp vào bất kỳ GPIO nào của ESP32.**

## Hành vi

- `distance <= 30 cm`: trạng thái `EMERGENCY`, buzzer bật.
- `30 cm < distance <= 60 cm`: trạng thái `WARNING`, buzzer không bắt buộc bật.
- `distance > 60 cm`: trạng thái `SAFE`, reset trạng thái silence để sẵn sàng cho cảnh báo mới.
- Timeout ECHO: trạng thái `SENSOR_FAULT`, buzzer bật theo hướng fail-safe.
- Nhấn nút GPIO27: silence còi hiện tại. Còi sẽ không bật lại cho đến khi có một lần đo `SAFE`.

Firmware gửi JSON qua Serial ở `115200 baud`, ví dụ:

```text
{"device_id":"ESP32-HRC-01","sensor_id":"HC-SR04","timestamp_ms":1234,"distance_cm":24.7,"state":"EMERGENCY","emergency_stop":true,"buzzer_on":true,"buzzer_silenced":false,"seq":12}
```

## Nạp firmware

Mở `ultrasonic_esp32.ino` bằng Arduino IDE, chọn board **ESP32 Dev Module**, chọn đúng cổng COM và nạp. Mở Serial Monitor ở **115200 baud**.

Sơ đồ dạng SVG nằm tại `wiring_diagram.svg`.
