# SonarChain Web3 dashboard

Dashboard theo dõi một HC-SR04, có nguồn mô phỏng hoặc gateway thật. Mô phỏng dùng `recordEvent`; dữ liệu gateway dùng commitment SHA-256 và `recordEvidence`. Nhật ký chỉ ghi EMERGENCY; SAFE/WARNING/SENSOR_FAULT vẫn cập nhật telemetry và dữ liệu gateway lưu ngoài chain. EMERGENCY tự bật E-STOP và giữ khóa đến khi Supervisor kiểm tra/gỡ tại vùng SAFE.

Dashboard cũng có MVP **Work Permit & Human–Robot Handoff**. Contract `WorkPermitHandoff` quản lý vòng đời `PENDING → APPROVED → ACTIVE → COMPLETED`: requester tạo permit, supervisor approve, gateway ghi nhận zone entry từ telemetry, worker xác nhận handoff và đóng permit.

## Chạy local

Từ thư mục gốc repository:

```powershell
py -m http.server 8080 -d web3
```

Mở <http://localhost:8080>. Chọn nguồn dữ liệu. Để xem ESP32 thật, chạy Serial gateway và API port 8000 cùng database. Xem `../HUONG_DAN_CHAY_PROJECT.md` để chạy đủ các terminal.

Nguồn được lưu khi tải lại trang; chọn ESP32 thì nhãn phải là `GATEWAY · LIVE` khi có mẫu mới và nút mô phỏng bị khóa. Với `--write-chain`, gateway lưu mẫu vào SQLite trước, gửi EMERGENCY trên một luồng riêng và cập nhật trạng thái khi receipt xác nhận. Dashboard tải lại lịch sử EMERGENCY mỗi 5 giây để nhận tx của event cũ trong lúc khoảng cách mới vẫn cập nhật.

ethers được đóng gói tại `vendor/`; mô phỏng không cần CDN. Mẫu quá 5 giây/API offline không hiển thị SAFE. Nút kích hoạt thủ công chỉ dùng mô phỏng. Chỉ ví có `supervisors(account)=true` trong HRCSafetyLog được gỡ khóa; Owner phải được cấp Supervisor nếu muốn gỡ. Với gateway, nút gỡ xác nhận khóa giám sát/on-chain, không gửi lệnh xuống ESP32.

Chạy Hardhat local theo `contracts/README.md`, deploy hai contract, nhập địa chỉ `HRCSafetyLog` và `WorkPermitHandoff` (dòng `permitContract=`), rồi kết nối MetaMask với chain `31337`. Dashboard đọc mạng ví và kiểm tra owner/Reporter trước khi bật nút ghi safety event.

Khi cấp/thu hồi Supervisor, nhập cả hai contract và xác nhận hai giao dịch để đồng bộ quyền gỡ E-STOP (Safety) và duyệt permit (Permit). Contract HRCSafetyLog cũ cần deploy lại. Xem [kịch bản demo các role](../docs/KICH_BAN_DEMO_ROLES.md), hoặc chạy `npm.cmd run demo:roles:check` trong `contracts` để kiểm chứng tự động.

Trong panel **Work permit & robot handoff**:

1. Nhập worker address (hoặc để trống dùng ví hiện tại), zone và task.
2. Nhấn **Tạo permit**.
3. Nhấn **Approve** bằng tài khoản supervisor/owner.
4. Chạy mô phỏng rồi nhấn **Ghi zone entry**.
5. Nhấn **Xác nhận handoff**.
6. Nhấn **Đóng permit** khi hoàn tất.

Dashboard chỉ ghi hash event, hash thiết bị, severity, permit/task/zone hash và cờ EmergencyStop. Raw telemetry vẫn ở gateway/off-chain; blockchain không nằm trong vòng điều khiển dừng thời gian thực.
