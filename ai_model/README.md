# AI model

Thư mục này chứa toàn bộ phần AI của HRC Safety Log theo cấu trúc nộp bài.

- `feature_engineering.py`: tạo đặc trưng dùng chung cho huấn luyện và gateway.
- `train_model.py`: huấn luyện Isolation Forest từ các mẫu SAFE và xuất `model.joblib`, `metrics.json`.
- `notebooks/01_train_anomaly_detection.ipynb`: notebook trình bày quy trình train, đánh giá và lưu model.
- `data/raw/`: dữ liệu khoảng cách trái/phải thu từ hai HC-SR04.

Mô hình chỉ phát hiện mẫu đo lệch khỏi vùng hoạt động bình thường. Các ngưỡng khoảng cách trong gateway vẫn là lớp quyết định EmergencyStop độc lập với AI.