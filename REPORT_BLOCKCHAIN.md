# Nội dung báo cáo kỹ thuật — phần HRC Safety Log

## 1. Bài toán và mục tiêu

Trong vùng làm việc chung người–robot, một sự kiện nguy hiểm cần được phát hiện nhanh và có thể truy nguyên sau sự cố. Hệ thống của đề tài sử dụng hai cảm biến siêu âm trên ESP32 để đo khoảng cách trái/phải, một gateway Python để trích xuất đặc trưng và phát hiện mẫu bất thường, và blockchain permissioned/local để lưu bằng chứng toàn vẹn của nhật ký.

Mục tiêu blockchain không phải lưu toàn bộ dữ liệu cảm biến. Dữ liệu thô có thể lớn và có thông tin vận hành; hệ thống chỉ đưa lên chain mã băm của sự kiện, mã băm thiết bị, thời gian, mức độ nghiêm trọng, cờ EmergencyStop và địa chỉ reporter. File CSV/JSON off-chain giữ dữ liệu chi tiết để phân tích. Bất kỳ thay đổi nào đối với bản ghi chi tiết sau khi ghi đều làm hash sự kiện không còn khớp.

## 2. Kiến trúc và luồng dữ liệu

```text
HC-SR04 trái/phải
        │  GPIO + Serial
        ▼
ESP32 firmware ──> gateway Python ──> feature engineering
                                      │
                                      ├─ hard safety thresholds (fail-safe demo)
                                      ├─ Isolation Forest anomaly score
                                      └─ event_id = SHA-256(canonical event)
                                                    │
                           off-chain raw log ◄─────┼─────► Web3 transaction
                                                              │
                                                              ▼
                                                HRCSafetyLog.sol
                                      recordEvent(hash, device, time, severity, stop)
                                                              │
                                      SafetyEventRecorded + DeviceAccessChanged
```

Nguyên tắc quan trọng là blockchain không nằm trên vòng điều khiển thời gian thực. Gateway phải quyết định dừng theo ngưỡng cục bộ trước; transaction blockchain là bằng chứng kiểm toán và cơ chế đồng bộ trạng thái, không được dùng làm điều kiện duy nhất để bảo vệ người. Trong bản demo, `<= 30 cm` tạo `EMERGENCY_STOP`, `<= 60 cm` tạo `WARNING`; các ngưỡng này là tham số thí nghiệm, chưa phải khoảng cách bảo vệ đã được chứng nhận.

## 3. AI và dữ liệu

Mỗi bản ghi có `left_cm`, `right_cm`, `min_distance_cm`, chênh lệch hai cảm biến và tốc độ thay đổi khoảng cách. Notebook dùng các mẫu `SAFE` để fit Isolation Forest. Các nhãn `APPROACHING`, `DANGER`, `RETREATING` dùng để đánh giá phát hiện lệch chuẩn, không được mô tả là mô hình nhận dạng người hoàn chỉnh. Với dữ liệu cảm biến siêu âm hiện tại, mô hình chỉ chứng minh khả năng phát hiện hành vi đo bất thường trong phạm vi thí nghiệm.

## 4. Thiết kế Smart Contract

`HRCSafetyLog.sol` có owner và danh sách reporter. Reporter được cấp quyền mới được gọi `recordEvent`. Mỗi sự kiện có `eventHash` duy nhất nên cùng một event không thể ghi lặp. Contract lưu `deviceIdHash`, timestamp, enum severity, cờ `emergencyStop` và địa chỉ reporter. Khi cờ dừng là true, contract đặt đồng thời `emergencyStopByDevice[deviceIdHash]` và `deviceLocked[deviceIdHash]` thành true, rồi phát các event Solidity để frontend hoặc hệ thống giám sát truy vết.

`eventHash` được tạo từ chuỗi canonical gồm device ID, timestamp, hai khoảng cách và severity. Gateway dùng `sha256` để tạo mã định danh sự kiện và Web3 dùng `keccak(text=event_id)` làm `bytes32` trên chain. `deviceIdHash` cũng được băm, do đó contract không cần lưu định danh dạng rõ. Người có transaction hash có thể kiểm tra timestamp, severity, reporter và các event phát ra; còn dữ liệu cảm biến chi tiết được đối chiếu bằng cách băm lại bản ghi gốc.

Hàm `clearEmergencyStop` chỉ owner gọi được. Đây là điểm kiểm soát quyền: hệ thống không tự mở khóa chỉ vì khoảng cách đã tăng. Quyết định reset phải có người có thẩm quyền và có thể mở rộng thành quy trình hai người ký trong phiên bản nâng cao. Quyền reporter là allowlist, giảm nguy cơ một thiết bị lạ gửi log giả.

## 5. Vì sao dùng hash on-chain

Ghi toàn bộ chuỗi cảm biến lên blockchain gây tốn gas, khó bảo vệ dữ liệu và không cần thiết cho mục tiêu bất biến. Hash on-chain tạo cam kết ngắn gọn: cùng một dữ liệu đầu vào luôn cho cùng một hash; sửa một giá trị làm hash thay đổi. Blockchain cung cấp thứ tự transaction, thời gian block và chữ ký tài khoản gửi, nhờ đó hỗ trợ điều tra sau sự cố. Cần nói rõ giới hạn: hash chứng minh dữ liệu đã cam kết không bị sửa kể từ lúc ghi, nhưng không tự chứng minh cảm biến ban đầu đo đúng hay reporter là thiết bị vật lý đáng tin cậy.

## 6. Kịch bản kiểm thử và tiêu chí đạt

Kịch bản SAFE phải tạo severity SAFE, `emergency_stop=false`, không khóa thiết bị. Kịch bản khoảng cách dưới 30 cm phải tạo severity EMERGENCY, `emergency_stop=true`, transaction thành công và `deviceLocked=true`. Gửi lại cùng event hash phải bị revert `event already recorded`. Tài khoản không thuộc reporter phải bị từ chối. Sau khi owner gọi clear, trạng thái dừng và khóa trở về false. Các kiểm thử này nằm trong `blockchain/test/HRCSafetyLog.js`; phần gateway có thể replay các CSV hiện có để tái lập demo.

## 7. Hạn chế và hướng phát triển

HC-SR04 có giới hạn về góc đo, vật liệu và nhiễu; hai cảm biến không đủ để mô tả đầy đủ vùng an toàn quanh robot. Bản demo chưa điều khiển cơ cấu dừng thật và chưa phải hệ thống safety-certified. Hướng phát triển gồm cảm biến lực/ToF hoặc safety scanner, đồng bộ thời gian tin cậy, ký số firmware, gateway dự phòng, mạng blockchain permissioned, lưu Merkle root theo batch, và đánh giá theo quy trình an toàn chức năng phù hợp.
