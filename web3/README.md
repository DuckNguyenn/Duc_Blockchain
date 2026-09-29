# SonarChain Web3 dashboard

Dashboard chạy mô phỏng dữ liệu hai cảm biến HC-SR04, kết nối MetaMask và gọi `HRCSafetyLog.recordEvent`.

Dashboard cũng có MVP **Work Permit & Human–Robot Handoff**. Contract `WorkPermitHandoff` quản lý vòng đời `PENDING → APPROVED → ACTIVE → COMPLETED`: requester tạo permit, supervisor approve, gateway ghi nhận zone entry từ telemetry, worker xác nhận handoff và đóng permit.

## Chạy local

Từ thư mục gốc repository:

```powershell
py -m http.server 8080 -d web3
```

Mở <http://localhost:8080>. Chạy Hardhat local theo `contracts/README.md`, deploy hai contract, nhập địa chỉ `HRCSafetyLog` và `WorkPermitHandoff` (dòng `permitContract=`), rồi kết nối MetaMask với chain `31337`.

Trong panel **Work permit & robot handoff**:

1. Nhập worker address (hoặc để trống dùng ví hiện tại), zone và task.
2. Nhấn **Tạo permit**.
3. Nhấn **Approve** bằng tài khoản supervisor/owner.
4. Chạy mô phỏng rồi nhấn **Ghi zone entry**.
5. Nhấn **Xác nhận handoff**.
6. Nhấn **Đóng permit** khi hoàn tất.

Dashboard chỉ ghi hash event, hash thiết bị, severity, permit/task/zone hash và cờ EmergencyStop. Raw telemetry vẫn ở gateway/off-chain; blockchain không nằm trong vòng điều khiển dừng thời gian thực.
