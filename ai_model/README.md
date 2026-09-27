# AI model

Phiên bản HRC Safety Log hiện tại **không sử dụng AI, camera hoặc YOLO**. Thư mục này được giữ lại như một placeholder vì cấu trúc bài nộp ban đầu có yêu cầu `/ai_model`; không đặt mã YOLO hay trọng số vào đây nếu nhóm không triển khai AI.

Phần xử lý thực tế nằm trong `iot_code/firmware/` và `iot_code/gateway.py`: đo khoảng cách, ngưỡng, debounce, cảnh báo và SHA-256.