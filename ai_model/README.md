# AI nhúng ESP32

Luồng chính là classifier supervised 3 lớp SAFE/APPROACHING/EMERGENCY cho một HC-SR04.

```powershell
python -m pip install -r requirements-tinyml.txt
python -m ai_model.train_keras_tflite --check-data
python -m ai_model.train_keras_tflite --epochs 150
```

Chạy từ thư mục gốc. Dataset: `data/single_sensor/processed_3class/dataset_3class.csv` bên trong thư mục `ai_model/`. Feature order: distance_cm, distance_delta_3, distance_std_5. `tinyml_pipeline.py` tách recording và bảo đảm train/validation/test đều đủ lớp; scaler/calibration chỉ lấy train.

Notebook độc lập: `notebooks/esp32_grouped_training.ipynb`. Candidate tại `artifacts/esp32_candidate/`; copy cc/h cùng nhau vào `esp32_safety_idf/main/model/` khi cần build model mới.

Kết quả đã chạy: MLP 3→16→8→3 (227 tham số, 3.456 byte), validation accuracy 88,91%, test INT8 91,14%, macro-F1 0,8937. Không đồng nghĩa accuracy trên board; kiểm tra cadence 176 ms của dataset so với cấu hình 100 ms firmware và thu thêm session.

`feature_engineering.py` và `train_model.py` là luồng IsolationForest/gateway trước đây với 2 feature; không dùng để export artifact TinyML. Xem `../docs/DANH_GIA_PROJECT_VA_MODEL.md` và `../HUONG_DAN_CHAY_PROJECT.md`.
