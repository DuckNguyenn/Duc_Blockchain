# Notebook huấn luyện cho dataset một cảm biến

Dataset mới dùng schema tối giản:

```text
timestamp,elapsed_s,distance_cm,label,nguoi,kichban,vat
```

Các notebook mới giữ lại các kiến trúc đã dùng với dataset hai cảm biến, nhưng chỉ đọc feature từ `ai_model.feature_engineering.FEATURE_COLUMNS`:

| Notebook | Kiến trúc | Artifact |
|---|---|---|
| `01_single_sensor_isolation_forest.ipynb` | StandardScaler + IsolationForest | `single_sensor_isolation_forest.joblib` |
| `02_single_sensor_extratrees_if.ipynb` | ExtraTrees + IsolationForest + hard thresholds | `single_sensor_extratrees_if.joblib` |
| `03_single_sensor_robust_hybrid.ipynb` | Group split + tuning contamination/confidence/logic | `single_sensor_robust_hybrid.joblib` |
| `04_single_sensor_if_autoencoder.ipynb` | ExtraTrees + IsolationForest + MLP autoencoder | `single_sensor_if_autoencoder.joblib` |

Chạy notebook từ repository root hoặc mở trực tiếp trong Jupyter/Kaggle. Các notebook tự tìm CSV trong `ai_model/data/single_sensor/` khi chạy local; trên Kaggle chúng quét `/kaggle/input` để tìm CSV hoặc ZIP, tự giải nén ZIP vào `/kaggle/working/single_sensor_dataset`, rồi dùng thư mục đó. Artifact được lưu vào `/kaggle/working` trên Kaggle và `ai_model/artifacts/` khi chạy local.

Hard safety policy được giữ nguyên trong mọi kiến trúc:

- `distance_cm <= 30`: `EMERGENCY`, `emergency_stop=True`.
- `30 < distance_cm <= 60`: `WARNING`.
- AI chỉ được quyết định cảnh báo bổ sung ngoài vùng hard threshold; không được hạ mức EMERGENCY.
