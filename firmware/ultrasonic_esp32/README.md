# Firmware ESP32 cho 2 cảm biến HC-SR04

Firmware `ultrasonic_esp32.ino` dành cho ESP32 DevKit 30-pin và đọc tuần tự hai HC-SR04. Kết quả được gửi qua Serial ở tốc độ 115200 baud.

## Xác định chân theo sơ đồ

| Thiết bị | Chân module | ESP32 | Ghi chú |
|---|---|---:|---|
| HC-SR04 trái | TRIG | GPIO5 | Tín hiệu từ ESP32 |
| HC-SR04 trái | ECHO | GPIO2 | Bắt buộc qua cầu phân áp 1 kΩ/2 kΩ; đây là chân boot-strap |
| HC-SR04 phải | TRIG | GPIO18 | Tín hiệu từ ESP32 |
| HC-SR04 phải | ECHO | GPIO4 | Bắt buộc qua cầu phân áp 1 kΩ/2 kΩ |
| Cả hai cảm biến | VCC | VIN/5V | HC-SR04 cần nguồn 5 V |
| Cả hai cảm biến | GND | GND | Chung mass với ESP32 |

Theo ảnh, dây tín hiệu của cảm biến trái là TRIG → GPIO5 và ECHO → GPIO2; cảm biến phải là TRIG → GPIO18 và ECHO → GPIO4. Dây đen là GND và dây đỏ là VIN. Hai điện trở 1 kΩ/2 kΩ ở mỗi đường ECHO hạ mức 5 V xuống khoảng 3,33 V cho ESP32.

Không được nối ECHO 5 V trực tiếp vào GPIO ESP32. GPIO2 là chân boot-strap; nếu ESP32 không khởi động khi cắm cảm biến, hãy chuyển dây ECHO trái sang một GPIO input khác (ví dụ GPIO34) và sửa hằng số trong firmware. Khi dùng đúng sơ đồ hiện tại, đầu ra cầu phân áp không được kéo GPIO2 lên mức HIGH trong lúc reset.

## Nạp và chạy

Mở thư mục này trong Arduino IDE, chọn board **ESP32 Dev Module**, chọn đúng cổng COM, sau đó nạp file `.ino`. Mở Serial Monitor ở **115200 baud**.

Dữ liệu mẫu:

```text
distance_cm,left=42.7cm,right=38.1cm
distance_cm,left=timeout,right=37.9cm
```

Firmware đo hai cảm biến tuần tự và chờ 60 ms giữa hai lần phát để hạn chế nhiễu âm/crosstalk. `timeout` nghĩa là không nhận được xung ECHO trong khoảng 30 ms.
