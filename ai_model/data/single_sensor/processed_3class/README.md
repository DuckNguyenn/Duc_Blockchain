# Dataset single-sensor — 3 lớp train

Bản này được tạo từ các recording trong thư mục `single_sensor/` và dành cho bài toán phân loại 3 lớp:

- `EMERGENCY`: mẫu gốc `DANGER`.
- `APPROACHING`: mẫu gốc `APPROACHING`.
- `SAFE`: mẫu gốc `SAFE`, `RETREATING` và `EMPTY`.

`EMPTY` có nghĩa là không có người và không có vật. Trong bộ train 3 lớp, `EMPTY` được xem là trạng thái an toàn; cột `original_label` vẫn được giữ lại để kiểm tra và đánh giá riêng theo nguồn gốc.

Các cột quan trọng:

- `source_file`: recording gốc; dùng để chia train/validation/test theo nhóm, không chia ngẫu nhiên từng dòng.
- `original_label`: nhãn gốc trước khi quy đổi.
- `label`: nhãn train cuối cùng (`SAFE`, `APPROACHING`, `EMERGENCY`).
- `distance_cm`, `elapsed_s`: tín hiệu cảm biến và thời gian.

Các bản ghi trùng không có thông tin mới được loại bỏ khi trùng mọi cột ngoài `timestamp`. Dữ liệu gốc trong thư mục cha không bị thay đổi. `dataset_3class.csv` là file tổng hợp để đọc trực tiếp; các recording riêng nằm trong thư mục `recordings/` để chia tập theo nhóm.

Lưu ý an toàn: không dùng mô hình thay thế hard safety rule. Khi chạy thực tế, `distance_cm <= 30 cm` nên luôn được xử lý là emergency; AI chỉ được tăng mức cảnh báo, không được hạ mức cảnh báo cứng.
