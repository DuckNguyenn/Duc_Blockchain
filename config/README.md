# Configuration

`config/sensor.json` chứa `device_id`, `sensor_id`, ngưỡng `alert_distance_cm`, chu kỳ đo và pin `TRIG/ECHO`. Firmware hiện biên dịch các giá trị tương ứng trong file `.ino`; khi đổi phần cứng, cập nhật cả hai nơi và đo kiểm lại.