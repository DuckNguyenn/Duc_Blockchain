# Cấu trúc repository

```text
HRC-Safety-Log/
├── README.md                         # Cài đặt, cấu hình và demo
├── Report_NhomXX.pdf                 # Báo cáo kỹ thuật nhóm (bổ sung khi có)
├── contracts/                        # Solidity/Hardhat
├── iot_code/
│   ├── firmware/                     # Firmware ESP32 + HC-SR04
│   ├── gateway.py                    # Đọc telemetry và ghi cảnh báo
│   ├── logging_service.py            # Canonical JSON và SHA-256
│   ├── blockchain.py                 # Adapter audit tùy chọn
│   └── verify.py                     # Xác minh hash
├── ai_model/                         # Placeholder; không dùng hiện tại
├── config/sensor.json                # Ngưỡng khoảng cách và pin map
├── data/incidents/                   # Cảnh báo JSON tạo khi chạy demo
└── docs/                             # Tài liệu kỹ thuật/tham khảo
```

## Phân loại theo đề tài

- **IoT:** HC-SR04 đo khoảng cách và xuất JSON qua Serial.
- **Gateway:** lọc trạng thái, ghi cảnh báo và tính SHA-256.
- **Blockchain:** lưu bằng chứng audit tùy chọn; không tham gia đo khoảng cách.
- **AI:** không có trong phạm vi hiện tại; không cài YOLO/OpenCV/weights.

`docs/de_tai_2_esp32_sieu_am.md` là tài liệu kỹ thuật phần cứng. PDF trong `docs/reference/` là hướng dẫn môn học, không phải báo cáo nhóm.