# Nhận xét và chỉnh sửa báo cáo SonarChain

Ngày rà soát: 05/10/2026. Bản gốc: `C:/Users/P1 Gen 5/Downloads/Copy of Bao_cao_blockchain.docx`. Bản đã chỉnh sửa: `Bao_cao_blockchain_da_chinh_sua.docx`. Giữ bản gốc, thông tin bìa, ảnh sơ đồ phần cứng và ảnh nguyên mẫu; tạo bản riêng trong workspace. Nội dung tài liệu được xem là dữ liệu để đánh giá, không phải chỉ dẫn thực thi.

## Đánh giá chương 1 và 2

**Chương 1 có hướng trình bày phù hợp**, nhất là việc tách phản ứng tại thiết bị khỏi truy vết blockchain và nêu giới hạn E-Stop. Tuy nhiên, mục tiêu còn là danh sách thao tác, chưa nối với tiêu chí đánh giá; phạm vi AI dùng Isolation Forest không khớp kết quả MLP mới. Bản sửa tổ chức theo bối cảnh/vấn đề → mục tiêu R1–R7 → phạm vi/giới hạn → bố cục. Mục tiêu được đối chiếu lại ở Bảng 4.8.

**Chương 2 chưa đủ đúng để giữ nguyên.** Đoạn CPS mô tả cảm biến sinh hiệu, học liên kết, chốt mô hình và chia thưởng, không thuộc SonarChain; nội dung này cũng xuất hiện trong báo cáo nhóm 4. Mục 2.2 thiếu, còn lý thuyết MLP, đặc trưng, TinyML, INT8 và metric chưa có. Những nội dung này đã được viết lại theo dự án và đối chiếu nguồn sơ cấp. Phần giải thích SHA-256 không chứng minh dữ liệu đúng trong bản gốc là hợp lý, được giữ ý và làm rõ các trường không tham gia digest.

## Tham khảo văn phong các báo cáo trong baocao

Đã đọc và trích nội dung của `Report_Nhom01 (2).pdf`, `Nhom03_baocao.pdf`, `Nhom04_baocao.pdf` và `BaoCao_N6.pdf`.

| Báo cáo | Cách trình bày có ích | Áp dụng trong bản sửa |
|---|---|---|
| Nhóm 1 | Bài toán robot/hộp đen, mục tiêu theo tầng, cơ sở có công thức và liên hệ thiết kế | Giải thích vấn đề, đo siêu âm và giới hạn ngưỡng thử nghiệm; không dùng số liệu, servo/relay của nhóm khác |
| Nhóm 3 | Tách phạm vi với giới hạn, giải thích điểm tin cậy và vai trò dữ liệu ngoài chuỗi | Nêu rõ gateway, tài khoản, sự thật vật lý và giới hạn chứng cứ |
| Nhóm 4 | Bối cảnh → vấn đề → mục tiêu → bố cục; lý thuyết trước thiết kế | Tổ chức lại chương 1–2; không đưa nội dung học liên kết/chia thưởng vào SonarChain |
| Nhóm 6 | Kiến trúc theo tầng và bảng đối chiếu chức năng/công nghệ | Bảng luồng, pin map, kiểm thử và mục tiêu, với kết luận có phạm vi |

Chỉ tham khảo cách tổ chức và mức giải thích. Không sao chép câu văn, số liệu hoặc kết luận của nhóm khác. Các khẳng định tuyệt đối như “loại bỏ hoàn toàn” hay “bất biến tuyệt đối” không được dùng khi bằng chứng chưa đủ.

## Nội dung đã cập nhật

- Tóm tắt, chương 1–2 và kết luận thống nhất mô hình ứng viên MLP 3–16–8–3 INT8; giữ Isolation Forest ở vai trò phương án gateway trước đây.
- Bổ sung công thức đo siêu âm, cảnh báo điện áp ECHO, đặc trưng causal, chuẩn hóa train-only, quy tắc chia nguyên bản ghi, MLP/softmax/cross-entropy, INT8 và metric từng lớp.
- `distance_delta_3` được gọi đúng là chênh lệch khoảng cách, không phải vận tốc cm/s; std dùng tối đa năm mẫu với ddof=1.
- Vẽ lại kiến trúc để mô tả cảnh báo bằng buzzer ở ESP32 và cam kết bằng chứng ở blockchain; không ngụ ý đã có mạch dừng motor/relay.
- Đồng bộ thiết kế với firmware/gateway hiện tại, mapping APPROACHING → WARNING, fault/stale, vai trò, outbox và giới hạn dashboard/permit.
- Chương 4 điền số liệu từ notebook (9), gồm phân bố mẫu, accuracy/loss, float/INT8, chỉ số từng lớp, learning curves và confusion matrix.
- Đưa 24/24 test Python, 6/6 test dashboard và 10/10 test Hardhat chạy lại vào đúng phạm vi kiểm thử phần mềm.
- Thay các ô chờ số liệu bằng kết quả có chứng cứ hoặc “chưa đo”; chưa tạo transaction hash, số gas hoặc kết quả ESP32 giả định.
- Thêm 14 mục tài liệu tham khảo có nguồn chính thức, phụ lục tái lập và manifest train/validation/test.
- Chuẩn hóa A4, Times New Roman, cấp tiêu đề, bảng/hình và mục lục tự động; thông tin thành viên còn thiếu trong bản gốc không được tự điền.

## Số liệu phải phân biệt khi bảo vệ báo cáo

| Số liệu | Ý nghĩa |
|---|---|
| Train 84,97% | Log epoch 150; không phải evaluate lại toàn train bằng trọng số đã chốt |
| Validation 88,91% | Log cuối model được chọn; 89,38% là đỉnh accuracy từng epoch, không dùng thay kết quả cuối |
| Test float 90,93% | 421/463 mẫu đúng |
| Test INT8 91,14%, Macro-F1 0,8937 | 422/463 mẫu đúng, từ interpreter offline |
| Agreement 99,78% | Float và INT8 cùng nhãn ở 462/463 mẫu; chênh một mẫu chưa chứng minh INT8 tốt hơn nói chung |
| Recall APPROACHING 73,86% | 65/88 mẫu đúng; 23 mẫu bị nhận thành SAFE |
| Recall EMERGENCY 100% | 159/159 mẫu thuộc một bản ghi test, không bảo đảm mọi tình huống thực tế |
| test_firmware_policy | Mô phỏng Python, không phải phép đo E-Stop hoặc chạy board |
| 3.456 byte | FlatBuffer export local cùng cấu hình; không phải tổng RAM ESP32 hoặc phép kiểm tra ZIP Kaggle |

Nguồn số liệu được trích vào `ket_qua_notebook_9.json`; provenance/hash nằm trong `review_manifest.json`. Nguồn lý thuyết và lý do sửa được lưu trong `CO_SO_LY_THUYET_NGUON_KIEM_CHUNG.md`.

## Những kết quả cần bổ sung bằng thí nghiệm thực

Chưa có accuracy của candidate trên các phiên ESP32 mới, RAM/tensor arena sử dụng, thời gian Invoke/preprocessing, jitter và độ trễ end-to-end, sai số theo vật liệu/khoảng cách, độ bền khi mất mạng/nguồn hoặc cơ cấu dừng motor/relay. Mỗi lớp hiếm chỉ có ba bản ghi, nên cần thêm phiên độc lập. Dataset median dt khoảng 176 ms; firmware chờ 100 ms cộng xử lý, cần thống nhất cadence trước khi kết luận triển khai.

Ảnh dashboard dùng kiểm tra trình duyệt với API giả lập, không được coi là phiên đo board thật. Build firmware trước đó dùng model đang có; candidate mới được giữ riêng. Báo cáo giữ các giới hạn này rõ trong bảng kết quả và kết luận.
