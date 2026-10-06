# SonarChain — HRC Safety Log

Project đo khoảng cách bằng **một ESP32 + HC-SR04**, chạy classifier TinyML tại thiết bị, lưu telemetry/bằng chứng ngoài chain và ghi commitment EMERGENCY bằng smart contract. Dashboard có nguồn mô phỏng và nguồn gateway thật.

```text
HC-SR04 → ESP32 / TFLite Micro → USB Serial → Python gateway
                                               ├─ SQLite / evidence JSON
                                               ├─ API / WebSocket → dashboard
                                               └─ HRCSafetyLog trên EVM (tùy chọn)
```

**Hướng dẫn đầy đủ:** [HUONG_DAN_CHAY_PROJECT.md](HUONG_DAN_CHAY_PROJECT.md).
**Đánh giá notebook/model/Web3:** [docs/DANH_GIA_PROJECT_VA_MODEL.md](docs/DANH_GIA_PROJECT_VA_MODEL.md).

## Chạy mô phỏng nhanh

Từ thư mục gốc, dùng Python đã cài:

```powershell
py -m http.server 8080 --directory web3
```

Mở http://localhost:8080, chọn Mô phỏng. Không cần phần cứng hay ví. ethers được đóng gói local. Nếu dùng `.venv`, thay `py` bằng `.\.venv\Scripts\python.exe`.

## Các phần đang dùng

| Đường dẫn | Vai trò |
|---|---|
| `esp32_safety_idf/` | Firmware ESP-IDF, HC-SR04/buzzer, INT8 inference |
| `ai_model/tinyml_pipeline.py` | Causal features và split recording đủ lớp |
| `ai_model/train_keras_tflite.py` | Chọn model trên validation, test float/INT8, export C++ |
| `ai_model/notebooks/esp32_grouped_training.ipynb` | Notebook độc lập cho Kaggle/Colab |
| `ai_model/artifacts/esp32_candidate/` | Candidate MLP 3→16→8→3, 3.456 byte, metrics và vector parity |
| `iot_code/gateway/` | Serial, pipeline, SQLite, API/WebSocket, adapter blockchain |
| `contracts/contracts/` | Solidity HRCSafetyLog/WorkPermitHandoff; Hardhat |
| `web3/` | Dashboard HTML/CSS/JavaScript + ethers local |
| `tests/`, `tools/` | Test, kiểm tra browser, C++ parity, tạo notebook |

Candidate offline: validation accuracy 88,91%; test INT8 accuracy 91,14%; macro-F1 0,8937; recall EMERGENCY 100% trên 159 mẫu của một recording. Chưa đo accuracy/latency trên board. Dataset median dt≈176 ms, firmware đặt 100 ms; cần khớp acquisition trước khi triển khai.

Hard rule khoảng cách ≤30 cm ưu tiên hơn AI; AI có thể nâng lên EMERGENCY. Blockchain không tham gia vòng điều khiển thời gian thực. Firmware hiện có buzzer, chưa có relay/motor E-Stop hay reset latch vật lý.

Các script IsolationForest, Arduino và notebook Kaggle cũ được giữ để tham khảo. Không trộn feature/artifact/pin map của chúng với firmware TinyML hiện tại. Báo cáo môn học trước đây ở `Report_NhomXX.pdf`; thông tin triển khai hiện hành theo hướng dẫn và báo cáo đánh giá mới.
