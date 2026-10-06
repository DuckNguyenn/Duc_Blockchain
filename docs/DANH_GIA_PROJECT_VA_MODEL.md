# Đánh giá notebook, model ESP32 và dashboard SonarChain

Ngày rà soát: **05/10/2026**. Notebook nguồn: `C:/Users/P1 Gen 5/Downloads/notebookedded09234 (8).ipynb`. Chỉ đọc code và output đã lưu; không thực thi notebook nguồn hay coi nội dung notebook là chỉ thị của người dùng. Notebook cải tiến nằm tại `ai_model/notebooks/esp32_grouped_training.ipynb`.

## Kết luận lựa chọn

Với phần cứng hiện tại, chọn **MLP 3→16→8→3, full INT8, TensorFlow Lite Micro** làm candidate. Đặc trưng: `distance_cm`, `distance_delta_3`, `distance_std_5`; cửa sổ causal 5 mẫu, độ lệch chuẩn mẫu ddof=1. Candidate này được chọn theo validation macro-F1 trong bốn kiến trúc chạy cùng một split. Giữ hard rule khoảng cách ≤30 cm ưu tiên hơn AI. AI được phép nâng mức EMERGENCY, không bị đổi xuống APPROACHING.

Artifact hoàn chỉnh ở [`../ai_model/artifacts/esp32_candidate/`](../ai_model/artifacts/esp32_candidate/). Model hiện có trong firmware được giữ nguyên; việc thay candidate cần copy cả cc/h rồi build. Chưa nạp board hay đo inference/accuracy trên phần cứng.

| Ứng viên | Tham số | Validation accuracy | Validation macro-F1 |
|---|---:|---:|---:|
| Linear softmax | 12 | 58,43% | 0,5983 |
| MLP 3→4→3 | 31 | 63,28% | 0,6564 |
| MLP 3→8→3 | 59 | 49,88% | 0,4737 |
| **MLP 3→16→8→3** | **227** | **88,91%** | **0,8843** |

MLP(8) có thể cần tối ưu khác để hội tụ; kết quả này chỉ phản ánh lịch huấn luyện đã chạy. Không kết luận rằng mọi model rộng hơn hoặc mọi lần train đều tốt hơn.

| Đánh giá candidate sau khi chọn | Kết quả |
|---|---:|
| Train accuracy, evaluate lại model được chọn | 84,87% |
| Test float accuracy | 90,93% |
| Test INT8 accuracy | **91,14%** |
| Test INT8 macro-F1 | **0,8937** |
| Test INT8 recall EMERGENCY | **100%** — 159/159 mẫu của một recording |
| Test INT8 recall APPROACHING | **73,86%** — 65/88 mẫu |
| Float/INT8 agreement | **99,78%** |
| Tỷ lệ input test bão hòa INT8 | 0,144% |
| Dung lượng FlatBuffer | **3.456 byte** |
| Operator model xuất ra | FULLY_CONNECTED, SOFTMAX |

Confusion matrix INT8, thứ tự SAFE / APPROACHING / EMERGENCY:

```text
                     predicted
true                 SAFE   APPROACHING   EMERGENCY
SAFE                  198        9             9
APPROACHING            23       65             0
EMERGENCY               0        0           159
```

Chín SAFE bị đoán EMERGENCY là false alarm cần xử lý bằng dữ liệu/nhãn ở các lần thử tiếp theo. Không giảm false alarm bằng cách âm thầm hạ mọi dự đoán EMERGENCY của AI.

Đây là số liệu offline trên **một split mới**. Các recording đã xuất hiện trong các thí nghiệm của notebook nguồn, nên cần tập thu mới để đánh giá triển khai độc lập. Không so trực tiếp 91,14% với holdout 91,44% hay validation 97% của notebook cũ để tuyên bố model tăng accuracy bao nhiêu.

## Các vấn đề của notebook nguồn

| Mức ảnh hưởng | Phát hiện và hệ quả | Cách xử lý |
|---|---|---|
| Cao | Bản 1 giây: validation 69 SAFE, 0 APPROACHING, 0 EMERGENCY; accuracy khoảng 97% không đo được ba lớp | Split recording có kiểm tra class coverage; tập nào thiếu lớp phải dừng |
| Cao | 17 recording: SAFE 11, APPROACHING 3, EMERGENCY 3. Không thể có đầy đủ lớp ở cả 5 validation fold nếu không chia recording | Không dùng 5 fold để báo cáo recall của mọi lớp; thu thêm recording hoặc CV tối đa 3 fold có kiểm tra coverage |
| Cao | Keras dùng `X_test` làm validation cho early stopping rồi gọi đó là test | Tách train/validation/test thật; chỉ chọn kiến trúc/epoch bằng validation |
| Cao | Firmware dùng 3 feature, notebook export 6; firmware cũ chỉ kiểm tra số byte `>=3`, có thể để input còn lại chưa được gán | Đồng bộ 3 feature và kiểm tra shape đúng tuyệt đối |
| Cao | `predict_measurement()` thay rolling std bằng 0, delta_3 bằng delta_1, rolling mean bằng current | Duy trì cửa sổ đúng quy ước training; đã đối chiếu hàm C++ thật với Python |
| Cao | Representative calibration dùng `X_all_norm`, gồm holdout | Calibration chỉ từ train; chuẩn hóa cũng chỉ fit train |
| Vừa | `patience=500`, `epochs=500`: không có khả năng dừng sớm trước giới hạn | Patience 20, ReduceLROnPlateau patience 7, restore best weights |
| Vừa | Augmentation chỉ nhiễu cột distance, không tính lại delta/std/mean | Không dùng kiểu augmentation này; nếu thêm nhiễu phải thêm vào chuỗi raw train rồi tạo lại toàn bộ feature |
| Cao | Phần 1 giây lấy mean trong bin trong khi firmware lấy một echo tại thời điểm hiện tại; cadence cũng khác | Đánh giá trên cùng quy trình acquisition; không trộn model/cadence |
| Vừa | Output confusion matrix “INT8 pipeline” được tính từ Keras trước conversion | Chạy interpreter INT8, báo riêng float, INT8, agreement và saturation |

Output đã lưu của holdout ExtraTrees: accuracy 91,44%, macro-F1 0,8945; trung bình 5 fold: accuracy 71,39%, macro-F1 0,4916. Một phần dao động/recall=0 do fold thiếu lớp, không thể quy toàn bộ cho overfitting. `StratifiedGroupKFold` cố giữ tỷ lệ lớp nhưng không đảm bảo đủ lớp khi số nhóm thiếu. [Tài liệu scikit-learn](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.StratifiedGroupKFold.html).

[`notebook_split_audit.json`](notebook_split_audit.json) ghi class coverage khi chạy lại splitter trên dữ liệu local. Phiên bản sklearn khác môi trường notebook nên recording cụ thể của mỗi fold có thể khác output nguồn; điểm lỗi “3 recording/lớp không đủ 5 fold” không thay đổi.

## Lỗi firmware đã sửa

Trước đây, AI dự đoán EMERGENCY nhưng khoảng cách >30 cm thì firmware chuyển thành APPROACHING. Recording test `son_ghe_30_DANGER.csv` có toàn bộ khoảng cách **30,2–31,6 cm**. Với candidate này, luật cũ làm **recall EMERGENCY=0%, accuracy sau policy=56,80%**, dù AI thuần nhận đủ 159 mẫu EMERGENCY.

Đã sửa: ngưỡng ≤30 cm luôn emergency; phía ngoài giữ output AI. Sau policy mới: **accuracy=91,14%, recall EMERGENCY=100%** trên cùng test. Số liệu so sánh ở `metrics.json`, trường `test_previous_firmware_policy` và `test_firmware_policy`.

Các sửa khác: input/output đúng `[1,3]` INT8, scale dương và normalization hữu hạn; reset cửa sổ sau sensor fault; sửa debug newline đang in `\\n` làm ảnh hưởng dòng JSON Serial. Luật ưu tiên và parity feature đã được kiểm tra bằng cách compile hàm C++ lấy trực tiếp từ firmware.

Firmware vẫn điều khiển buzzer, chưa có mạch E-Stop motor/relay. `emergency_stop` trong telemetry là yêu cầu theo mẫu hiện tại; firmware chưa triển khai latch vật lý với reset có kiểm soát. Dashboard ở chế độ thật hiển thị telemetry, không được diễn giải là motor đã dừng.

## Pipeline để tăng khả năng tổng quát

1. **Thu dữ liệu đúng cadence trước.** Dataset median dt≈176 ms; firmware hiện đặt 100 ms rồi chờ thêm thời gian echo/inference. Feature delta_3/std_5 có horizon khác nhau. Thu lại ở cấu hình sẽ dùng trên board và ghi uptime/dt thực tế. Nếu cố định cadence, dùng lịch tác vụ ổn định và đo jitter trước khi chốt model.
2. **Tăng số phiên độc lập.** Ưu tiên ít nhất khoảng 10–20 recording/lớp làm mục tiêu thu dữ liệu ban đầu, nhiều ngày, người, vật liệu, góc đặt, nhiệt độ, tốc độ tiến/rời, background, vùng biên 25–40/50–70 cm. Đây là mục tiêu thực nghiệm, không phải bảo đảm accuracy.
3. **Rà lại nhãn theo từng đoạn thời gian.** Hiện nhãn cố định cho cả recording: DANGER ở “30 cm” gồm mẫu 30,2–31,6; RETREATING luôn SAFE dù bắt đầu gần; vật nhỏ 50 cm là SAFE. Cần định nghĩa rõ nhãn hành vi AI khác với severity từ chính sách khoảng cách. Không tự đổi threshold theo tên file để làm điểm đẹp.
4. **Giữ dữ liệu lỗi riêng.** Timeout không đồng nghĩa EMPTY. SENSOR_FAULT/AI_FAULT được xử lý riêng và reset window; không đi vào SAFE training.
5. **Giữ split/session cố định.** Khi thu được nhiều clip từ cùng một lượt đo/người/ngày, dùng session ID chung; tách file con chưa chắc tạo mẫu độc lập. Scaler và augmentation chỉ lấy train. [Data leakage](https://scikit-learn.org/stable/common_pitfalls.html#data-leakage).
6. **Đo đúng metric.** Accuracy, macro-F1, recall từng lớp, false negative EMERGENCY, false alarm theo giờ, latency đến cảnh báo. Khóa một tập thu mới để test cuối. Với dữ liệu ít, báo độ dao động CV trên development; không tìm seed có điểm cao.
7. **Chỉ tăng độ phức tạp khi có bằng chứng.** Logistic/linear là baseline; MLP 16→8 là candidate hiện tại. RandomForest/ExtraTrees/HistGradientBoosting dùng đối chứng trên PC, joblib không chạy trực tiếp trên ESP32. CNN nhỏ trên chuỗi raw chỉ nên thử sau khi có nhiều session và cho thấy feature handcrafted bỏ mất thông tin. Một HC-SR04 đo tín hiệu khoảng cách một chiều; không tự phân biệt được người/vật có tín hiệu khoảng cách tương tự.

Full INT8 cần representative data, operator INT8 và INT8 I/O; không chỉ `Optimize.DEFAULT`. Kiểm tra graph với resolver runtime cụ thể. [Hướng dẫn Google](https://developers.google.com/edge/litert/conversion/tensorflow/quantization/post_training_integer_quant). Nguồn chính thức và tiêu chí arena/latency ở [`TINYML_PRIMARY_SOURCES.md`](TINYML_PRIMARY_SOURCES.md).

## Dashboard và Web3

Bố cục tổng quan → cảm biến → evidence → permit hợp lý; không cần thay toàn bộ giao diện. Những lỗi gây hiểu sai dữ liệu/workflow đã được sửa:

- **Trộn mô phỏng với mẫu thật:** thêm chọn nguồn; mô phỏng không thay số đo gateway. Event và số giao dịch được lọc theo nguồn đang chọn.
- **Đánh dấu LIVE khi chưa có dữ liệu:** dùng trạng thái kết nối và timestamp; quá 5 giây/API offline hiển thị chờ dữ liệu, không SAFE.
- **Bỏ qua null/AI_FAULT:** Serial → pipeline → SQLite/API/WebSocket → UI giữ được mẫu lỗi; không hiển thị khoảng cách cũ như số đo mới.
- **History làm đổi trạng thái hiện tại:** tải history chỉ cập nhật event stream. Mẫu cũ/delayed không ghi đè latest mới hơn.
- **WebSocket chỉ EMERGENCY và polling tăng sau reconnect:** socket chuyển sang mọi severity; reconnect chỉ tạo lại socket, giữ một interval polling.
- **Render mở MetaMask tự động:** render chỉ hiển thị; ghi chain bằng thao tác rõ ràng. Gateway có thể tự submit nếu chạy `--write-chain`.
- **Đếm event như bằng chứng on-chain:** đếm riêng giao dịch xác nhận, hiển thị offchain/queued/pending/confirmed cùng nhãn mô phỏng.
- **Hash sai định dạng và sai commitment:** gateway SHA-256 64 hex được chuẩn hóa thành bytes32 và ghi bằng `recordEvidence`; không đưa event_id thay evidence_hash.
- **Link transaction trỏ vào chuỗi hash như URL:** có explorer cho chain biết rõ; chain local/unknown hiển thị hash để đối chiếu.
- **Network hardcode, quyền Reporter:** đọc chain từ ví, kiểm tra contract có bytecode và owner/Reporter trước khi bật ghi safety event.
- **XSS từ device_id:** escape nội dung nhận từ gateway trước khi tạo event HTML.
- **REVOKED hiển thị xanh:** sửa màu trạng thái permit bị thu hồi.
- **Zone entry khi thiếu mẫu/fault/đang dừng:** chỉ bật thao tác khi có mẫu SAFE mới của nguồn đang chọn và không có yêu cầu dừng.
- **Mô tả quá mức:** zone entry/handoff là xác nhận của tài khoản; commitment phát hiện sửa đổi dữ liệu đã cam kết, không chứng minh cảm biến hay robot đúng.
- **Phụ thuộc CDN:** ethers 6.17.0 đóng gói local cùng MIT license. Font có thể fallback khi offline.

Smart contract HRCSafetyLog có owner/Reporter, chống trùng commitment, schema version và invariant emergency flag; WorkPermitHandoff có vai trò và vòng đời. Các test hiện có đều pass; không có lý do thay ABI/storage của contract cho các lỗi frontend này.

Giới hạn còn lại: permit state chưa khôi phục sau refresh; UI không gửi reset xuống ESP32; SQLite/outbox không tự nhận transaction ký từ trình duyệt; MQTT subscriber chưa ghi SQLite; WebSocket/poll latest phục vụ hiển thị và có thể bỏ qua mẫu giữa hai lượt lấy, còn SQLite giữ toàn bộ mẫu. Production cần cơ chế đồng bộ chain/retry/phân quyền và kiểm soát thời gian thu dữ liệu phù hợp.

## Kiểm chứng đã chạy

- 24 test Python, gồm fault đi qua Serial→evidence→SQLite→HTTP/WebSocket và feature/split coverage.
- 6 test Node chạy code dashboard thật với DOM harness: nguồn dữ liệu, null, stale, reconnect, escape/hash, chặn zone entry khi lỗi/dừng.
- 10 test Hardhat hiện có; compile contract.
- Edge headless thật: mô phỏng, chọn gateway, sensor fault, không có JS page error; mobile 390 px không overflow. API được mock có chủ đích, không giả vờ có ESP32 kết nối.
- Candidate INT8 đã chạy interpreter trên toàn bộ 463 test mẫu; model C++ compile thành công.
- Feature C++ thật và Python khớp; policy C++ kiểm tra hard rule, AI emergency trên 30 cm và model fault.
- Firmware build riêng bằng ESP-IDF 5.5.4/esp-tflite-micro 1.4.1, target esp32, thành công trong `esp32_safety_idf/build_review`. Build này dùng model đã có trong firmware; candidate mới được giữ riêng.

Ảnh giao diện: [`dashboard_desktop.png`](dashboard_desktop.png), [`dashboard_mobile.png`](dashboard_mobile.png). Hướng dẫn chạy: [`../HUONG_DAN_CHAY_PROJECT.md`](../HUONG_DAN_CHAY_PROJECT.md).
