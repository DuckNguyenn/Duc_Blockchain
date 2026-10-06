# Nguồn chính thức và lựa chọn TinyML cho ESP32

Đối chiếu nguồn ngày 05/10/2026. Phạm vi: phân loại khoảng cách/chuỗi khoảng cách siêu âm, triển khai bằng `esp-tflite-micro`. Các cấu hình bên dưới là **đề xuất thử nghiệm**, chưa phải kết quả accuracy hay benchmark trên phần cứng của project.

## Model nên thử

| Lựa chọn | Đầu vào/cấu hình đề xuất | Khi nên dùng |
|---|---|---|
| Logistic regression | Các đặc trưng cửa sổ; hoặc `Dense(K, softmax)` trong Keras | Baseline dễ kiểm tra, chi phí tính toán nhỏ. Chọn nếu kết quả trên các phiên đo mới gần bằng MLP. |
| MLP nhỏ, int8 | `Dense(16, relu) → Dense(8, relu) → Dense(K, softmax)` | Lựa chọn đầu tiên để thử nhúng khi firmware đã tính các đặc trưng và quan hệ phân lớp có tính phi tuyến. |
| CNN thời gian nhỏ, int8 | Cửa sổ 16–32 mẫu, `Conv2D(8, (3,1), relu) → MaxPool2D((2,1)) → Flatten → Dense(K, softmax)`; input `[batch,W,1,1]` | Chỉ chuyển sang khi hình dạng/thứ tự chuỗi cung cấp thông tin mà các đặc trưng thống kê làm mất, và cải thiện validation theo phiên đo đủ rõ. |

`K` là số lớp. Logistic regression đa lớp dùng softmax theo [scikit-learn LogisticRegression](https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.LogisticRegression.html). Keras xác định [Conv1D](https://keras.io/api/layers/convolution_layers/convolution1d/) là phép tích chập theo một chiều, có thể là thời gian. Cấu hình CNN dùng Conv2D với chiều rộng 1 ở đây là lựa chọn triển khai để khớp operator MCU: resolver chính thức của [Espressif](https://github.com/espressif/esp-tflite-micro/blob/master/tensorflow/lite/micro/micro_mutable_op_resolver.h) có `AddConv2D`, `AddMaxPool2D`, `AddFullyConnected`, `AddReshape`, `AddSoftmax`. Việc có tên operator chưa chứng minh mọi cấu hình/dtype đều chạy được: phải kiểm tra chính file `.tflite` và build đã khóa phiên bản.

Nếu nhãn chỉ là phép so khoảng cách với các ngưỡng cố định, baseline cần có chính luật ngưỡng đó: model khi ấy đang học lại luật gán nhãn. Accuracy cao trên nhãn như vậy chưa chứng minh phát hiện tình huống thực tế tốt hơn. Đây là suy luận từ cách xác định nhãn, không phải kết quả thử nghiệm.

## Tạo validation phản ánh dữ liệu mới

1. Lưu `recording_id/session_id`, timestamp, nhãn và dữ liệu gốc. Chia **phiên đo** thành train/validation/test trước khi tạo cửa sổ. Mọi cửa sổ từ cùng một phiên thuộc cùng một tập; không tạo cửa sổ băng qua ranh giới phiên/tập. Nếu nhiều phiên vẫn cùng một người/vị trí và cần đánh giá khả năng tổng quát sang người/vị trí mới, dùng mức group tương ứng.
2. Dùng `StratifiedGroupKFold` khi có đủ phiên độc lập và lớp; thuật toán giữ group tách biệt, cố gắng giữ tỷ lệ lớp. Thiếu nhiều group có thể khiến tỷ lệ lớp không cân bằng. Với một chuỗi duy nhất, chia theo thời gian và bỏ các cửa sổ chạm ranh giới; không coi hàng nghìn cửa sổ chồng lấn là hàng nghìn phiên độc lập. Khuyến nghị bỏ cửa sổ ranh giới là suy luận để tránh dùng lại cùng mẫu thô giữa các tập. Nguồn: [StratifiedGroupKFold](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.StratifiedGroupKFold.html), [cross-validation cho chuỗi thời gian](https://scikit-learn.org/stable/modules/cross_validation.html#time-series-split).
3. Chỉ fit scaler/imputer/feature selection trên train, rồi transform validation/test. Giữ đúng thứ tự đặc trưng, đơn vị, độ dài cửa sổ và cách xử lý timeout giữa Python và firmware. Nguồn: [scikit-learn: tránh data leakage và preprocessing không nhất quán](https://scikit-learn.org/stable/common_pitfalls.html).

Đề xuất đánh giá: báo cáo accuracy, balanced accuracy, macro-F1, confusion matrix và recall của lớp nguy hiểm. Dùng validation để chọn model/checkpoint/ngưỡng; mở test sau khi chốt. Thu thêm phiên thật ở gần ranh giới lớp, nhiều góc/bề mặt và mẫu timeout. Augmentation chỉ áp dụng train và phải phản ánh nhiễu đo thật. Các bước thu thập và chọn metric này là khuyến nghị cho project; chưa có số liệu chứng minh mức tăng accuracy.

## Export full int8

Representative dataset phải có cùng preprocessing/input shape với inference, bao phủ giá trị và lớp thường gặp. Với project này, lấy mẫu từ **train**, không dùng validation/test để hiệu chỉnh dải lượng tử; đây là lựa chọn bảo toàn tập đánh giá. [Hướng dẫn integer quantization của Google](https://developers.google.com/edge/litert/conversion/tensorflow/quantization/post_training_integer_quant) giải thích calibration, minh họa lấy dữ liệu train và cách buộc converter lỗi khi có phép toán không lượng tử được:

```python
converter.optimizations = [tf.lite.Optimize.DEFAULT]
converter.representative_dataset = representative_train_samples
converter.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS_INT8]
converter.inference_input_type = tf.int8
converter.inference_output_type = tf.int8
```

Chỉ bật `Optimize.DEFAULT` chưa đảm bảo input/output int8. Sau export, xem `get_input_details()`, `get_output_details()` và graph; [tf.lite.experimental.Analyzer](https://www.tensorflow.org/api_docs/python/tf/lite/experimental/Analyzer) có thể hiển thị các operator/tensor của model. Không thêm `SELECT_TF_OPS` để né lỗi convert rồi giả định MCU sẽ chạy.

Firmware phải lượng tử input đã chuẩn hóa theo `q = clip(round(x / scale) + zero_point, -128, 127)` và giải lượng tử output bằng `x = (q - zero_point) * scale`. Lấy scale/zero-point từ tensor metadata của model, không chia raw int8 cho 255. Đặc tả softmax int8 quy định scale `1/256` và zero-point `-128`, nhưng đọc metadata vẫn giúp phát hiện sai tensor/model. Nguồn: [đặc tả int8 chính thức](https://developers.google.com/edge/litert/conversion/tensorflow/quantization/quantization_spec).

## Kiểm tra trước khi nhúng

- **Parity:** chạy cùng bộ validation/test đã khóa qua Keras float, TFLite float, TFLite int8; so metric, lớp dự đoán và các mẫu mất recall sau int8. Sau đó đưa các vector đầu vào cố định lên ESP32, đối chiếu input bytes, output giải lượng tử và argmax với bản int8 trên PC. Chênh lệch lớn gợi ý lỗi feature order, scaler, cửa sổ, class mapping hoặc quantization. Đây là quy trình kiểm chứng đề xuất, chưa được chạy trên board.
- **Operator:** đăng ký các operator thực sự có trong graph bằng `MicroMutableOpResolver`; kiểm tra `AllocateTensors()` và `Invoke()`. [Hướng dẫn MCU của Google](https://developers.google.com/edge/litert/microcontrollers/get_started) giải thích resolver và arena phải được xác định cho model cụ thể.
- **RAM:** `.tflite` nhỏ không đồng nghĩa tensor arena nhỏ. Arena còn chứa activation, scratch và metadata. Dùng `RecordingMicroInterpreter`/`PrintAllocations()` ở build đo bộ nhớ, sau đó đặt arena theo kết quả và kiểm tra đủ RAM khi Wi-Fi/MQTT đang hoạt động. Nguồn: [TFLite Micro memory management](https://github.com/tensorflow/tflite-micro/blob/main/tensorflow/lite/micro/docs/memory_management.md).
- **Latency:** đo `Invoke()` bằng `esp_timer_get_time()`; đo riêng cả preprocessing và toàn pipeline, nhiều lần sau warm-up, báo median/p95/max và điều kiện Wi-Fi/CPU. ESP Timer trả microsecond theo [ESP-IDF](https://docs.espressif.com/projects/esp-idf/en/latest/esp32/api-reference/system/esp_timer.html). [ESP-NN](https://github.com/espressif/esp-nn) tối ưu các kernel như convolution, fully connected, pooling, softmax; các benchmark của họ không phải latency của model/project này.

Khóa phiên bản ESP-IDF, `esp-tflite-micro`, TensorFlow/Keras và lưu hash model cùng scaler/class mapping. [README Espressif](https://github.com/espressif/esp-tflite-micro) hướng dẫn thêm dependency bằng `idf.py add-dependency "esp-tflite-micro"` và công bố ma trận ESP-IDF được hỗ trợ; chọn bản tương thích với firmware hiện tại trước khi nâng cấp.
