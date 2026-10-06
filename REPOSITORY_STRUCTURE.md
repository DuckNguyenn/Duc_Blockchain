# Cấu trúc đang dùng

```text
README.md
HUONG_DAN_CHAY_PROJECT.md         # Cài đặt, mô phỏng, hardware, chain, train
ai_model/
  tinyml_pipeline.py             # 3 causal features, recording splits
  train_keras_tflite.py           # Keras → INT8 → C++
  notebooks/esp32_grouped_training.ipynb
  data/single_sensor/processed_3class/
  artifacts/esp32_candidate/     # Model mới giữ riêng khỏi model firmware
esp32_safety_idf/
  main/main.cpp                  # Firmware HC-SR04 + TFLite Micro
  main/model/                    # Model đang được firmware build dùng
  build_review/                  # Build kiểm tra; không commit
iot_code/gateway/
  serial_reader.py
  pipeline.py
  storage.py
  api.py
  blockchain_client.py
contracts/contracts/
  HRCSafetyLog.sol
  WorkPermitHandoff.sol
web3/
  index.html / app.js / styles.css / controls.css
  vendor/                        # ethers + MIT license
docs/
  DANH_GIA_PROJECT_VA_MODEL.md
  TINYML_PRIMARY_SOURCES.md
tests/
tools/
data/telemetry.db                # Runtime SQLite; không commit
data/evidence_outbox/            # Runtime evidence; không commit
```

Repo cũng giữ firmware Arduino, IsolationForest, notebook Kaggle và báo cáo cũ. Luồng hiện hành trong `HUONG_DAN_CHAY_PROJECT.md` dùng một HC-SR04/ESP-IDF/USB Serial; MQTT là tùy chọn và chưa đồng bộ SQLite như Serial.
