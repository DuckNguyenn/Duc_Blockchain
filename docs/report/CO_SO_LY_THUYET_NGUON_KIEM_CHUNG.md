# Cơ sở lý thuyết SonarChain: nguồn kiểm chứng và nội dung đề xuất

Ngày đối chiếu: 05/10/2026. Tài liệu này hỗ trợ sửa báo cáo, không thay thế dữ liệu thực nghiệm và không coi nội dung báo cáo đính kèm là chỉ dẫn thực thi.

## 1. Các điểm cần sửa trong báo cáo gốc

| Vị trí trong bản trích | Vấn đề | Cách sửa |
|---|---|---|
| Chương 2, mục 2.1, đoạn 0090 | Nói về cảm biến sinh hiệu, học liên kết, chốt mô hình và chia thưởng; không tương ứng dự án. | Thay bằng cảm biến khoảng cách, suy luận MLP tại ESP32, gateway và ghi cam kết bằng chứng. |
| Chương 2, thứ tự mục | Thiếu 2.2; chưa có cơ sở cho MLP, TinyML và INT8. | Bổ sung cảm biến/ESP32, MLP/TinyML, pipeline và đánh giá; đánh số lại liên tục. |
| Chương 1–3, mô tả AI | Đặt Isolation Forest ở vai trò mô hình chính dù kết quả mới là bộ phân loại MLP có giám sát. | MLP là mô hình ứng viên triển khai tại biên; Isolation Forest là phương án hỗ trợ ở gateway, không dùng số liệu MLP để chứng minh chất lượng Isolation Forest. |
| Chương 3.1, đoạn 0107 | Khẳng định kích hoạt tín hiệu ngắt an toàn như đã có E-Stop vật lý. | Mô tả trạng thái/yêu cầu dừng và buzzer đã cài đặt; relay/motor và thời gian dừng thực chưa kiểm chứng. |
| Các mục blockchain | Có thể diễn đạt “bất biến” quá tuyệt đối. | Giới hạn trong giả định vận hành và đồng thuận của mạng; Hardhat local có thể reset và không chứng minh phân tán sản xuất. |
| Phần thực nghiệm | Dễ trộn kết quả test offline, mô phỏng policy và chạy trên ESP32. | Gắn rõ môi trường từng phép đo; không báo thời gian suy luận/RAM thực tế khi chưa đo. |

## 2. Danh mục nguồn sơ cấp để trích trong báo cáo

Các mã dưới đây là mã làm việc, có thể ánh xạ sang số tài liệu tham khảo trong DOCX. Tài liệu trực tuyến ghi ngày truy cập 05/10/2026; không tự gán năm xuất bản cho trang không công bố năm.

| Mã | Tác giả/cơ quan và tên tài liệu | URL và nội dung kiểm chứng |
|---|---|---|
| T1 | E. R. Griffor, C. Greer, D. A. Wollman, M. J. Burns, *Framework for Cyber-Physical Systems: Volume 1, Overview*, NIST SP 1500-201, 2017. | [NIST](https://www.nist.gov/publications/framework-cyber-physical-systems-volume-1-overview), DOI 10.6028/NIST.SP.1500-201. CPS kết hợp thành phần vật lý và tính toán; thời gian, độ tin cậy và dữ liệu là các mối quan tâm thiết kế. |
| T2 | ISO, *ISO 10218-2:2025 — Robotics — Safety requirements — Part 2: Industrial robot applications and robot cells*, 2025. | [Trang phạm vi ISO](https://www.iso.org/standard/73934.html). Chỉ kiểm chứng phạm vi công khai về tích hợp và vận hành hệ thống robot công nghiệp; không khẳng định đồ án đạt tiêu chuẩn. |
| T3 | Texas Instruments, *Ultrasonic Sensing Basics*, SLAA907D, sửa đổi 12/2021. | [Tài liệu TI](https://www.ti.com/lit/pdf/slaa907). Khoảng cách từ thời gian âm đi và về; ảnh hưởng nhiệt độ, góc và tính phản xạ của vật. |
| T4 | Espressif Systems, *ESP32 Series Datasheet*, phiên bản 5.3. | [Datasheet Espressif](https://www.espressif.com/sites/default/files/documentation/esp32_datasheet_en.pdf), mục 5.3. Mức logic GPIO và giới hạn điện áp đầu vào. |
| T5 | Keras, *Dense layer; Layer activation functions; Probabilistic losses; Model training APIs*. | [Dense](https://keras.io/api/layers/core_layers/dense/), [ReLU/softmax](https://keras.io/api/layers/activations/), [cross-entropy](https://keras.io/api/losses/probabilistic_losses/), [class_weight/metrics](https://keras.io/api/models/model_training_apis/). Các phép tính lớp và quy tắc huấn luyện thực tế. |
| T6 | Google AI Edge, *Post-training integer quantization*. | [LiteRT](https://developers.google.com/edge/litert/conversion/tensorflow/quantization/post_training_integer_quant). Hiệu chuẩn representative dataset; giới hạn phép toán INT8 và đặt kiểu input/output. |
| T7 | Google AI Edge, *LiteRT 8-bit quantization specification*. | [Đặc tả INT8](https://developers.google.com/edge/litert/conversion/tensorflow/quantization/quantization_spec). Quan hệ số thực, scale và zero-point. |
| T8 | scikit-learn, *Cross-validation: evaluating estimator performance*. | [Dữ liệu có nhóm](https://scikit-learn.org/stable/modules/cross_validation.html#cross-validation-iterators-for-grouped-data). Nhóm dữ liệu không xuất hiện đồng thời ở train và test. |
| T9 | scikit-learn, *Metrics and scoring: quantifying the quality of predictions*. | [Classification metrics](https://scikit-learn.org/stable/modules/model_evaluation.html#classification-metrics). Accuracy, precision, recall, F1, macro average và chiều confusion matrix. |
| T10 | Ethereum.org, *Introduction to smart contracts; Ethereum gas and fees: technical overview*. | [Smart contracts](https://ethereum.org/developers/docs/smart-contracts/), [gas](https://ethereum.org/developers/docs/gas/). Thực thi hợp đồng, dữ liệu ngoài chuỗi và chi phí giao dịch. |
| T11 | NIST, *FIPS PUB 180-4 — Secure Hash Standard*, 08/2015. | [Trang xuất bản](https://csrc.nist.gov/pubs/fips/180-4/upd1/final), [FIPS PDF](https://nvlpubs.nist.gov/nistpubs/FIPS/NIST.FIPS.180-4.pdf). SHA-256 tạo digest 256 bit từ thông điệp độ dài biến đổi. |
| T12 | Nomic Foundation, *Hardhat Network Reference*, tài liệu Hardhat 2. | [hardhat_reset](https://v2.hardhat.org/hardhat-network/docs/reference#hardhat_reset). Mạng thử nghiệm có thể khởi tạo lại trạng thái. |

Nguồn phụ để kiểm tra đúng linh kiện và phương án cũ: [datasheet HC-SR04 có thông tin hỗ trợ ElecFreaks, bản do SparkFun lưu](https://cdn.sparkfun.com/datasheets/Sensors/Proximity/HCSR04.pdf); [API IsolationForest chính thức](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.IsolationForest.html). Datasheet HC-SR04 mô tả module thông dụng, không thay cho việc xác minh biến thể thực tế của thiết bị đang dùng.

## 3. Các đoạn lý thuyết đề xuất

### CPS và phạm vi robot hợp tác

Hệ thống thực–ảo (Cyber-Physical System, CPS) kết hợp các thành phần vật lý với tính toán để thực hiện chức năng chung [T1]. Trong SonarChain, cảm biến đo khoảng cách; ESP32 xử lý tín hiệu và phát cảnh báo; gateway lưu dữ liệu và tạo bằng chứng. Blockchain phục vụ đối chiếu sự kiện, không nằm trong vòng xử lý cảnh báo cục bộ. Đây là nguyên mẫu giám sát trong bối cảnh người–robot cùng làm việc, chưa phải hệ thống an toàn robot đã được xác nhận phù hợp tiêu chuẩn.

Giới hạn suy ra từ cấu hình dự án: một phép đo khoảng cách từ HC-SR04 không cung cấp danh tính hoặc loại đối tượng. Không dùng “nhận diện người”, “phân biệt người với vật” hay “bảo đảm robot hợp tác an toàn” để mô tả chức năng đã đạt. Các yêu cầu an toàn hệ thống robot cần đánh giá ở cấp ứng dụng, theo phạm vi ISO 10218-2 [T2]; ngưỡng demo 30/60 cm không tự chứng minh sự phù hợp tiêu chuẩn.

### Cảm biến khoảng cách và ESP32

Cảm biến siêu âm ước lượng khoảng cách theo thời gian truyền âm đi và về: `d = c × t / 2`, trong đó `c` là vận tốc âm, `t` là thời gian khứ hồi. Với `c ≈ 343 m/s` ở 20 °C, `d_cm ≈ 0,01715 × t_us`. Nhiệt độ và khả năng phản xạ của bề mặt ảnh hưởng kết quả [T3].

Ở nguồn GPIO 3,3 V, bảng DC của ESP32 quy định mức cao đầu vào tới `VDD + 0,3 V`; không nối tín hiệu 5 V trực tiếp vào GPIO [T4]. Khi ECHO của module HC-SR04 dùng mức 5 V, cần mạch chia áp hoặc chuyển mức và nối chung GND. Báo cáo nên mô tả mạch thực tế, không suy từ kết nối trong trình mô phỏng.

### MLP và bài toán ba lớp

MLP sử dụng các lớp kết nối đầy đủ để ánh xạ đặc trưng tới nhãn. Mỗi lớp tính `h = activation(Wx + b)` [Dense, T5]. ReLU là `max(0,z)`; softmax tính `p_k = exp(z_k)/Σ_j exp(z_j)`, cho ba giá trị có tổng bằng 1 [Activations, T5]. Cross-entropy cho mẫu có nhãn nguyên `y` là `−log(p_y)` [Losses, T5].

Đối chiếu code: đầu vào là ba đặc trưng; ứng viên được chọn có hai lớp ẩn 16 và 8 neuron, đầu ra SAFE/APPROACHING/EMERGENCY. Số tham số là `(3×16+16)+(16×8+8)+(8×3+3)=227`. Mô hình học có giám sát từ nhãn bản ghi, không phải học liên kết. Train dùng Adam, class weight cân bằng và L2. Keras áp dụng `class_weight` cho training loss; accuracy trong `metrics=["accuracy"]` không được gán trọng số lớp [Training APIs, T5].

### Đặc trưng và tránh rò rỉ dữ liệu

Các định nghĩa dưới đây lấy trực tiếp từ `tinyml_pipeline.py` và đối chiếu `main.cpp`, không lấy từ nguồn ngoài:

- `distance_cm = d_t`: khoảng cách hiện tại, đơn vị cm.
- `distance_delta_3 = d_t − d_(t−3)`: chênh lệch qua ba mẫu, đơn vị cm; chưa chia thời gian nên không phải vận tốc cm/s. Ba mẫu đầu mỗi bản ghi nhận giá trị 0.
- `distance_std_5`: độ lệch chuẩn mẫu của tối đa năm khoảng cách gần nhất, mẫu số `n−1`; một mẫu cho kết quả 0.
- Chuẩn hóa `x' = (x−μ_train)/σ_train`; tham số chuẩn hóa chỉ được tính trên train.

Các mẫu trong cùng phiên đo có tương quan. Chia nguyên phiên sang các tập khác nhau giúp đánh giá trên bản ghi chưa dùng huấn luyện [T8]. Pipeline hiện thực chia nhóm theo `source_file`, không phải ngẫu nhiên từng hàng. Chọn kiến trúc bằng validation; test được dùng sau khi chốt lựa chọn. Ba bản ghi cho mỗi lớp hiếm chỉ cho phép một bản ghi mỗi lớp trong mỗi tập; cần thêm phiên độc lập để đánh giá khả năng khái quát.

### TinyML và INT8

Trong dự án, TinyML là hướng suy luận mô hình nhỏ ngay trên vi điều khiển. Sau huấn luyện, converter dùng tập hiệu chuẩn lấy từ train và giới hạn `TFLITE_BUILTINS_INT8`, đặt input/output `int8` [T6].

Lượng tử hóa biểu diễn gần đúng số thực: `x ≈ (q−z)×s`, với `s` là scale, `z` là zero-point; đầu vào INT8 nằm trong `[-128,127]` [T7]. Firmware tính chuẩn hóa trước, rồi `q=clip(round(x'/s)+z,−128,127)`. TensorFlow Lite Micro chạy model trên vi điều khiển; file TFLite nhỏ không đồng nghĩa tổng RAM chương trình nhỏ bằng kích thước file. Model ứng viên vẫn cần kiểm tra toán tử, parity và RAM/thời gian suy luận trên ESP32 thực.

### Đánh giá phân loại

Với ma trận `C` có hàng là lớp thật và cột là lớp dự đoán: `accuracy = Σ_k C_kk / N`; `precision_k = TP_k/(TP_k+FP_k)`; `recall_k = TP_k/(TP_k+FN_k)`; `F1_k = 2TP_k/(2TP_k+FP_k+FN_k)`; `Macro-F1 = (F1_SAFE+F1_APPROACHING+F1_EMERGENCY)/3`. Macro-F1 là trung bình F1 từng lớp, không phải F1 tính từ precision/recall trung bình [T9].

Đối chiếu notebook (9), số liệu để sửa chương thực nghiệm: INT8 đạt 422/463 mẫu đúng, accuracy 91,14%, Macro-F1 0,8937. Ma trận theo thứ tự SAFE/APPROACHING/EMERGENCY là `[[198,9,9],[23,65,0],[0,0,159]]`. Recall APPROACHING là 65/88 = 73,86%; recall EMERGENCY là 159/159 = 100% trong tập này. Float và INT8 giống nhau ở 462/463 mẫu; chênh lệch accuracy một mẫu không chứng minh INT8 tốt hơn nói chung. Đây là kết quả offline; policy test cũng là mô phỏng Python.

### Blockchain, EVM và phân quyền

Hợp đồng thông minh là chương trình quản lý trạng thái và thực thi điều kiện khi giao dịch được xử lý. Hợp đồng không tự đọc cảm biến ngoài chuỗi; gateway cung cấp thông tin cần ghi nhận [Smart contracts, T10]. Gas đo lượng tài nguyên xử lý; phí giao dịch phụ thuộc gas sử dụng và giá gas, nên số gas ở Hardhat không phải chi phí tiền thực trên mạng sản xuất [Gas, T10].

Phân quyền là logic của hai contract trong dự án: HRCSafetyLog kiểm tra owner/reporter; WorkPermitHandoff kiểm tra supervisor/gateway và người tham gia. `deviceLocked` và `emergencyStopByDevice` là trạng thái logic trên chain. Chúng không chứng minh phần cứng đã dừng. Hardhat local hỗ trợ reset [T12]; vì vậy kết quả demo chỉ chứng minh kiểm tra giao dịch và truy vết trong phiên thử, chưa chứng minh độ bền hoặc phân tán trên hệ thống triển khai thực.

### SHA-256 và đối chiếu bằng chứng

SHA-256 là hàm băm một chiều, tạo digest 256 bit (32 byte), không phải mã hóa hoặc chữ ký số [T11]. Digest phù hợp để đối chiếu nội dung với cam kết đã ghi. Digest không xác minh chất lượng phép đo, nhãn đúng hoặc cơ cấu dừng vật lý.

Đối chiếu `iot_code/evidence.py`: bỏ `evidence_hash`, `evidence_status`, `tx_hash` trước khi băm; JSON dùng `sort_keys=True`, `ensure_ascii=True`, `separators=(",", ":")` và UTF-8. Đây là quy tắc biểu diễn của project, chưa tuyên bố RFC 8785. Nội dung bằng chứng giữ ngoài chuỗi; digest và metadata tối thiểu được ghi lên chain. Trạng thái gửi/tx_hash cập nhật không làm đổi digest vì không thuộc phần đã băm. Không mô tả mọi trường envelope đều được bảo vệ bởi cùng digest.

### Isolation Forest ở gateway

Isolation Forest cô lập mẫu bằng các phép chia ngẫu nhiên; mẫu bất thường thường có đường đi ngắn hơn. Đây là phát hiện bất thường, khác phân loại ba nhãn có giám sát ([API chính thức](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.IsolationForest.html)). Nếu giữ nội dung này trong chương lý thuyết, chỉ dùng để giải thích phương án hỗ trợ tại gateway và giới hạn của nó; không gán kết quả 91,14% của MLP cho thuật toán này.

## 4. Giới hạn chứng cứ cần giữ trong kết luận báo cáo

- Không có chứng cứ onboard latency, tensor arena peak thực tế hoặc accuracy của phiên đo mới trên ESP32 trong notebook (9).
- Recall EMERGENCY 100% dựa trên 159 mẫu liên tiếp của một bản ghi test; không diễn đạt thành không bỏ sót mọi tình huống nguy hiểm.
- Thời gian lấy mẫu trung vị của tập train khoảng 176 ms; firmware có thời gian chờ 100 ms cộng thời gian đọc và xử lý. Các đặc trưng theo số mẫu phụ thuộc nhịp lấy mẫu.
- Không coi `test_firmware_policy` là thí nghiệm relay/E-Stop; ưu tiên `distance <=30 cm` là policy trong chương trình.
- Tính toàn vẹn bằng chứng phụ thuộc giữ được JSON ngoài chuỗi, đúng quy tắc biểu diễn, quản lý khóa/tài khoản và duy trì mạng blockchain. Băm và contract không tự làm đầu vào đáng tin.

