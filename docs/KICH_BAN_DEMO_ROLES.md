# Kịch bản demo SonarChain theo role

Bản lời thoại để trình bày trước người xem: [Lời thoại thuyết trình và demo SonarChain](KICH_BAN_THUYET_TRINH_DEMO.md).

## Quy tắc cần trình bày

- EMERGENCY tự kích hoạt E-STOP ngay khi nhận mẫu, không chờ MetaMask hoặc giao dịch blockchain.
- E-STOP giữ khóa khi mẫu tiếp theo trở lại SAFE. Chỉ Supervisor được gỡ sau khi kiểm tra vùng an toàn.
- Nhật ký trên dashboard và `HRCSafetyLog` chỉ ghi EMERGENCY. SAFE/WARNING vẫn cập nhật khoảng cách trực tiếp; dữ liệu telemetry/evidence của gateway vẫn lưu ngoài chain.
- Owner quản lý quyền. Owner **không tự có quyền gỡ E-STOP**; muốn gỡ phải được cấp Supervisor tại `HRCSafetyLog`.
- Với ESP32, dashboard gỡ khóa giám sát và trạng thái logic trên chain. Firmware/cơ cấu dừng vật lý phải được kiểm tra/reset riêng tại thiết bị; dashboard hiện chưa có kênh gửi lệnh xuống ESP32.

## Chuẩn bị tài khoản

Script dùng sáu signer đầu tiên của Hardhat. Tên Account trong MetaMask có thể khác; đối chiếu địa chỉ mà script in ra.

| Signer | Role | Quyền trong demo |
| --- | --- | --- |
| 0 | Owner | Deploy, cấp/thu hồi Reporter và Supervisor ở Safety; Supervisor và Gateway ở Permit |
| 1 | Reporter | Ghi EMERGENCY lên `HRCSafetyLog`; không gỡ E-STOP |
| 2 | Supervisor | Gỡ E-STOP; duyệt permit |
| 3 | Gateway | Ghi zone entry sau khi permit được duyệt |
| 4 | Worker / Requester | Tạo permit, xác nhận handoff, đóng permit của mình |
| 5 | Outsider | Theo dõi; không được ghi safety, gỡ khóa hoặc handoff của người khác |

Supervisor là quyền riêng trong **hai contract**. Nút **Cấp role → Supervisor** trên dashboard yêu cầu hai xác nhận: Safety trước, Permit sau. Nhập cả hai địa chỉ và dùng owner của cả hai. Thu hồi cũng cập nhật cả hai contract. Nếu chỉ một giao dịch thành công, giao diện báo contract đã cập nhật và yêu cầu thử lại để đồng bộ.

Khi demo ESP32 với `--write-chain`, dùng khóa của Reporter riêng cho Serial gateway. Owner và Supervisor dùng các ví riêng trong MetaMask để không tranh nonce với gateway. Nếu đang dùng khóa Owner cho gateway, dừng gateway trước khi Owner cấp Reporter rồi đổi khóa gateway sang Reporter.

## Demo tự động

Từ thư mục gốc:

```powershell
cd contracts
npm.cmd run demo:roles:check
```

Lệnh chạy toàn bộ kịch bản trên mạng Hardhat tạm thời, không cần MetaMask hoặc node riêng. Các dòng `PASS` xác nhận cả thao tác thành công lẫn thao tác trái quyền bị contract từ chối. Địa chỉ trên mạng tạm thời không dùng được cho dashboard sau khi lệnh kết thúc.

Để chuẩn bị contract và role cho demo bằng giao diện, mở hai terminal:

```powershell
# Terminal 1 — giữ node chạy
cd contracts
npm.cmd run node
```

```powershell
# Terminal 2 — deploy mới, cấp role và chạy kiểm chứng trên node local
cd contracts
npm.cmd run demo:roles
```

Script in `contract`, `permitContract` và địa chỉ từng role; kết thúc với role đã cấp và device CLEAR. Script đã tạo hai bản ghi EMERGENCY để kiểm chứng. Nhật ký mô phỏng trên dashboard chỉ chứa mẫu tạo trong phiên giao diện hiện tại, không tự tải lịch sử contract.

Mở terminal khác tại thư mục gốc:

```powershell
.\.venv\Scripts\python.exe -m http.server 8080 -d web3
```

Mở <http://localhost:8080>, kết nối MetaMask với RPC `http://127.0.0.1:8545`, chain ID `31337`, rồi nhập hai địa chỉ vừa in. Dùng các tài khoản local của node cho các vai trò tương ứng. Nếu đã deploy bản cũ, cần deploy lại vì bản mới có `setSupervisor`/`supervisors` và quyền gỡ E-STOP mới; không dùng địa chỉ contract cũ.

## Cảnh 1 — Owner phân quyền (1 phút)

1. Chuyển ví Owner, nhập cả hai địa chỉ contract.
2. Trong **Ví & vai trò**, chọn ví Reporter → **Reporter · ghi EMERGENCY** → **Cấp role**.
3. Chọn ví Supervisor → **Supervisor · gỡ E-STOP / duyệt permit** → **Cấp role**; xác nhận hai giao dịch.
4. Chọn ví Gateway → **Gateway · ghi zone entry** → **Cấp role**.
5. Nếu đã chạy `demo:roles`, các quyền này đã được cấp; có thể trình bày panel và chuyển ngay sang cảnh tiếp theo.

Lời dẫn: “Owner quản trị quyền. Quyền báo cáo, gỡ dừng khẩn cấp và xác nhận vào vùng được cấp cho từng vai trò.”

## Cảnh 2 — EMERGENCY tự bật E-STOP, log chỉ có EMERGENCY (2 phút)

Chọn nguồn **Mô phỏng**, đổi sang Reporter. Ở phiên mới, bấm **Mẫu mô phỏng tiếp theo** theo thứ tự:

| Lần bấm | Khoảng cách | Telemetry | E-STOP | Nhật ký |
| --- | --- | --- | --- | --- |
| 1 | 86.4 cm | SAFE | READY | 0 EMERGENCY |
| 2 | 48.2 cm | WARNING | READY | 0 EMERGENCY |
| 3 | 24.6 cm | EMERGENCY | ACTIVE tự động | 1 EMERGENCY |
| 4 | 76.5 cm | SAFE | Vẫn ACTIVE | Vẫn 1 EMERGENCY |

Ở lần 3, chưa cần ký giao dịch vẫn thấy E-STOP ACTIVE. Bấm **Ghi EMERGENCY chưa gửi lên chain** bằng Reporter, xác nhận MetaMask; bản ghi có tx và đếm on-chain tăng. Ở lần 4, các nút gỡ vẫn bị khóa với Reporter.

Lời dẫn: “EMERGENCY tự kích hoạt dừng. Trở lại SAFE không tự khởi động lại; log chỉ lưu tình huống khẩn cấp.”

## Cảnh 3 — Chỉ Supervisor gỡ khóa (1 phút)

1. Khi khoảng cách còn 24.6 cm, đổi sang Supervisor: nút gỡ vẫn bị khóa vì chưa SAFE.
2. Chuyển mẫu sang 76.5 cm; nút **Supervisor · gỡ sau kiểm tra** được bật.
3. Kiểm tra vùng làm việc rồi bấm nút gỡ. Nếu EMERGENCY đã ghi chain, xác nhận giao dịch gỡ của Supervisor.
4. E-STOP chuyển READY, trạng thái vùng trở lại SAFE. Bản ghi EMERGENCY và tx vẫn còn trong nhật ký.
5. Có thể đổi sang Owner, Reporter hoặc Worker trước bước 3 để cho thấy các ví này không có nút gỡ được bật.

Dashboard còn chặn gỡ nếu mẫu gateway quá 5 giây, mất kết nối, SENSOR_FAULT, WARNING hoặc thiết bị vẫn báo yêu cầu dừng. Nếu có EMERGENCY mới trong khi giao dịch gỡ đang chờ, khóa giám sát vẫn giữ lại.

Contract xác minh **quyền Supervisor**, không tự đọc khoảng cách ngoài chain; điều kiện SAFE được dashboard kiểm tra và Supervisor chịu trách nhiệm kiểm tra hiện trường.

## Cảnh 4 — Worker → Supervisor → Gateway → Worker (2 phút)

Giữ nguyên tab để không mất permit ID của phiên. Bảo đảm đã gỡ E-STOP và có mẫu SAFE; nhật ký EMERGENCY không cần có bản ghi SAFE để thực hiện zone entry.

1. **Worker**: nhập ví Worker, zone `ASSEMBLY-A`, task `HANDOFF-001`; bấm **Tạo permit** → PENDING.
2. **Supervisor**: bấm **Approve** → APPROVED.
3. **Gateway**: bấm **Ghi zone entry** → ACTIVE; dashboard dùng hash của mẫu SAFE hiện tại.
4. **Worker**: bấm **Xác nhận handoff**, rồi **Đóng permit** → COMPLETED.

Lời dẫn: “Worker đề xuất công việc, Supervisor phê duyệt, Gateway ghi bằng chứng vào vùng, Worker xác nhận bàn giao và hoàn tất.”

## Cảnh 5 — Thu hồi quyền (1 phút)

1. Tạo EMERGENCY mới và chuyển lại SAFE; E-STOP vẫn ACTIVE.
2. **Owner** chọn địa chỉ Supervisor → **Thu hồi**; xác nhận hai giao dịch.
3. Chuyển về **Supervisor** đã bị thu hồi: nút gỡ bị khóa. Contract cũng từ chối với `not supervisor` nếu gọi trực tiếp.
4. Owner cấp lại Supervisor; chuyển về Supervisor và gỡ sau khi kiểm tra.

Script tự động còn kiểm tra: Outsider không tự cấp role/ghi EMERGENCY, Reporter không ghi zone entry, Gateway không entry trước approve, Worker không approve và Outsider không handoff.

## Tiêu chí demo đạt

- Chưa có giao dịch vẫn tự bật E-STOP khi EMERGENCY.
- SAFE/WARNING không tạo dòng trong nhật ký.
- SAFE không tự gỡ khóa; Reporter/Worker/Owner không có Supervisor không gỡ được.
- Supervisor gỡ được khi vùng SAFE, log cũ vẫn còn.
- Thu hồi Supervisor chặn quyền gỡ; work permit đi đúng PENDING → APPROVED → ACTIVE → COMPLETED.
