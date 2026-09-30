# SonarChain — nhật ký an toàn HRC

Hệ thống ghi nhận sự kiện khoảng cách trong vùng cộng tác người–robot và bằng chứng phục vụ kiểm toán.

## Language

**Telemetry**:
Một mẫu khoảng cách của cảm biến HC-SR04 cùng thông tin nhận diện nguồn và thời điểm đo.
_Avoid_: Transaction, bằng chứng on-chain

**Safety event**:
Kết quả đánh giá một mẫu telemetry theo chính sách an toàn, bao gồm mức nghiêm trọng và yêu cầu dừng khẩn cấp.
_Avoid_: Solidity event, giao dịch

**Off-chain evidence**:
Bản ghi chi tiết về telemetry và quyết định an toàn, được giữ ngoài blockchain để đối chiếu hoặc phân tích.
_Avoid_: Chỉ một mã băm, bằng chứng đã được xác thực on-chain

**Evidence commitment**:
Dấu cam kết cho một bản ghi off-chain xác định; dùng để phát hiện thay đổi kể từ khi cam kết được ghi nhận.
_Avoid_: Chứng nhận rằng cảm biến đo đúng, chứng nhận an toàn

**On-chain record**:
Bản ghi bằng chứng hoặc thay đổi quyền/workflow được blockchain chấp nhận theo quy tắc của smart contract.
_Avoid_: Dữ liệu thô, lệnh điều khiển robot

**Local E-Stop latch**:
Trạng thái yêu cầu dừng khẩn cấp tại hệ thống cục bộ, không tự mất đi chỉ vì có một mẫu khoảng cách an toàn hơn.
_Avoid_: Transaction E-Stop, motor đã dừng

**On-chain E-Stop state**:
Trạng thái logic trên blockchain ghi nhận yêu cầu dừng hoặc việc gỡ trạng thái đó; không chứng minh cơ cấu vật lý đã dừng.
_Avoid_: Local E-Stop latch, dừng robot trực tiếp

**Reporter**:
Tài khoản được phép đưa safety event lên sổ nhật ký blockchain.
_Avoid_: Worker, mọi tài khoản MetaMask

**Supervisor**:
Người có quyền phê duyệt hoặc thu hồi work permit.
_Avoid_: Reporter, owner của mọi contract

**Gateway**:
Thành phần tiếp nhận telemetry và tham gia ghi nhận sự kiện/vào vùng; tài khoản của nó có quyền riêng theo từng sổ nhật ký.
_Avoid_: Supervisor, cảm biến

**Work permit**:
Quyền làm việc có thời hạn cho worker, nhiệm vụ và vùng xác định.
_Avoid_: Chứng nhận khu vực an toàn, tài khoản worker

**Handoff**:
Xác nhận của bên tham gia rằng nhiệm vụ người–robot đã được bàn giao.
_Avoid_: Lệnh motor, phép đo khoảng cách
