# Lời thoại thuyết trình và demo SonarChain

**Thời lượng:** khoảng 8–10 phút, gồm thời gian chuyển ví và chờ giao dịch.

**Cách dùng:** đọc phần **Lời thoại**, làm theo phần **Thao tác**. Luồng chính dùng mô phỏng để kiểm soát thứ tự mẫu; có phần thay thế bằng ESP32 thật ở cuối. Một người có thể vừa nói vừa thao tác, hoặc một người thuyết trình và một người điều khiển demo.

## Chuẩn bị trước khi trình bày

Mở dashboard tại <http://localhost:8080>. MetaMask dùng Hardhat local, RPC `http://127.0.0.1:8545`, chain ID `31337`.

Nếu chưa chuẩn bị contract và role, giữ một terminal chạy node:

```bat
cd /d "C:\Users\P1 Gen 5\Downloads\Blockchain\contracts"
npm.cmd run node
```

Trong terminal CMD khác, chạy:

```bat
cd /d "C:\Users\P1 Gen 5\Downloads\Blockchain\contracts"
npm.cmd run demo:roles
```

Lệnh này deploy contract, cấp role và kiểm chứng các thao tác. Nhập giá trị `contract` vừa in vào ô **HRCSafetyLog**, `permitContract` vào ô **WorkPermitHandoff**. Dùng địa chỉ role trong kết quả của lần chạy đó; địa chỉ contract thay đổi theo lần deploy. Script kết thúc với role được cấp và device CLEAR.

Nếu chưa mở web server:

```bat
cd /d "C:\Users\P1 Gen 5\Downloads\Blockchain"
.\.venv\Scripts\python.exe -m http.server 8080 -d web3
```

Chuẩn bị các ví trong MetaMask:

| Vai trò | Tài khoản của script demo | Dùng để |
| --- | --- | --- |
| Owner | Signer 0 | Cấp và thu hồi quyền |
| Reporter | Signer 1 | Ghi EMERGENCY lên Safety contract |
| Supervisor | Signer 2 | Gỡ E-STOP và duyệt permit |
| Gateway | Signer 3 | Ghi zone entry |
| Worker | Signer 4 | Tạo permit, xác nhận handoff và đóng permit |
| Outsider | Signer 5 | Minh họa tài khoản chưa được cấp quyền |

Nếu dùng các ví đã cấu hình riêng, đối chiếu quyền thực tế thay vì dựa vào tên Account trong MetaMask. Supervisor cần được cấp ở cả Safety và Permit. Owner không tự có quyền gỡ E-STOP trong Safety.

Trước khi bắt đầu, chọn **Mô phỏng · không có phần cứng**, kết nối Reporter, nhập đủ hai contract. Bắt đầu với một phiên mô phỏng mới để thứ tự mẫu là **86.4 → 48.2 → 24.6 → 76.5 cm**. Sau khi tạo permit, giữ nguyên tab để giữ permit ID của phiên.

## Cảnh 1 — Giới thiệu bài toán, khoảng 45 giây

**Thao tác:** mở phần tổng quan; chỉ vào sơ đồ Worker–Robot và thẻ khoảng cách.

**Lời thoại:**

> “Em xin trình bày SonarChain, một prototype giám sát an toàn cho vùng cộng tác giữa người và robot.
>
> Hệ thống nhận khoảng cách từ cảm biến siêu âm HC-SR04, đánh giá trạng thái an toàn và phát yêu cầu dừng khẩn cấp khi có EMERGENCY. Đồng thời, hệ thống lưu bằng chứng sự kiện để phục vụ đối chiếu sau này.
>
> Trong phần demo, em sẽ trình bày ba điểm: EMERGENCY tự kích hoạt E-STOP; chỉ Supervisor được gỡ khóa; và blockchain lưu bằng chứng EMERGENCY cùng các bước phân quyền, cấp phép làm việc.”

## Cảnh 2 — Giải thích luồng xử lý, khoảng 45 giây

**Thao tác:** chỉ vào **Khoảng cách cảm biến**, **Nhật ký EMERGENCY**, rồi **Evidence layer**.

**Lời thoại:**

> “Luồng xử lý gồm ESP32, gateway và blockchain. ESP32 thực hiện logic tại thiết bị; gateway nhận telemetry và lưu dữ liệu ngoài chain; smart contract lưu cam kết bằng chứng và kiểm tra quyền của tài khoản.
>
> Việc phát yêu cầu E-STOP diễn ra cục bộ khi nhận EMERGENCY, không chờ ký giao dịch MetaMask. Giao dịch blockchain được thực hiện sau để lưu bằng chứng.
>
> Vì vậy, trạng thái E-STOP giám sát và khóa trên chain có thể khác nhau. Bản demo mô phỏng thể hiện khóa logic trên giao diện; reset phần cứng ESP32 là thao tác riêng tại thiết bị.”

## Cảnh 3 — Giới thiệu các role, khoảng 45 giây

**Thao tác:** kéo đến **Ví & vai trò**; chỉ các lựa chọn Reporter, Supervisor và Gateway. Nếu đã cấp role bằng script, chỉ trình bày, không cần cấp lại.

**Lời thoại:**

> “Owner là tài khoản quản trị, có quyền cấp hoặc thu hồi role. Reporter được ghi bằng chứng EMERGENCY, còn Supervisor được gỡ E-STOP và duyệt work permit.
>
> Gateway được ghi nhận zone entry. Worker là người tạo công việc và xác nhận bàn giao. Tài khoản chưa được cấp quyền vẫn xem được dashboard nhưng không được thực hiện các thao tác đặc quyền.
>
> Dự án có hai contract: HRCSafetyLog cho nhật ký an toàn và E-STOP; WorkPermitHandoff cho permit. Cấp Supervisor trên giao diện gồm hai giao dịch, mỗi giao dịch cập nhật một contract.”

## Cảnh 4 — SAFE, WARNING và EMERGENCY off-chain, khoảng 90 giây

**Thao tác:** giữ ví Reporter; chọn nguồn mô phỏng. Bấm **Mẫu mô phỏng tiếp theo** ba lần, dừng lại giữa các lần để giải thích.

| Lần bấm | Khoảng cách | Điều cần chỉ trên màn hình |
| --- | --- | --- |
| 1 | 86.4 cm | SAFE; chưa có dòng nhật ký EMERGENCY |
| 2 | 48.2 cm | WARNING; nhật ký vẫn không thêm dòng |
| 3 | 24.6 cm | EMERGENCY; E-STOP ACTIVE; Worker LOCKED; nhật ký thêm một EMERGENCY |

**Lời thoại khi SAFE:**

> “Ở mẫu đầu tiên, khoảng cách là 86,4 cm, lớn hơn ngưỡng 60 cm, nên trạng thái là SAFE.”

**Lời thoại khi WARNING:**

> “Khi khoảng cách giảm xuống 48,2 cm, hệ thống chuyển sang WARNING. Khoảng cách vẫn cập nhật trực tiếp, nhưng nhật ký EMERGENCY chưa thêm bản ghi. Nhật ký này chỉ tập trung vào tình huống khẩn cấp.”

**Lời thoại khi EMERGENCY:**

> “Ở 24,6 cm, mẫu hợp lệ đã đi vào vùng EMERGENCY, từ 30 cm trở xuống. E-STOP lập tức chuyển ACTIVE và vùng làm việc chuyển LOCKED.
>
> Em chưa bấm ghi lên chain và chưa ký MetaMask. Điều này minh họa việc kích hoạt E-STOP không phụ thuộc vào giao dịch blockchain.”

**Điểm dừng:** chỉ số giao dịch của phiên vẫn là 0; E-STOP đã ACTIVE. Không bấm nút kích hoạt thủ công trong cảnh này.

## Cảnh 5 — Reporter ghi bằng chứng, Supervisor gỡ khóa, khoảng 2 phút

### 5A. Ghi bằng chứng EMERGENCY

**Thao tác:** bằng ví Reporter, bấm **Ghi EMERGENCY chưa gửi lên chain**, xác nhận MetaMask, chờ giao dịch hoàn tất.

**Lời thoại:**

> “Bây giờ Reporter ghi bằng chứng của sự kiện EMERGENCY lên chain. Contract kiểm tra quyền Reporter và chống ghi trùng cam kết.
>
> Khi giao dịch được xác nhận, dòng sự kiện có transaction hash và số giao dịch tăng. Với nguồn ESP32, gateway giữ bản ghi chi tiết ngoài chain và dùng SHA-256 để tạo cam kết. Cam kết giúp đối chiếu dữ liệu có thay đổi sau khi ghi nhận hay không.”

### 5B. Supervisor cũng phải chờ vùng SAFE

**Thao tác:** khi vẫn ở 24.6 cm, chuyển MetaMask sang Supervisor. Chỉ nút **Supervisor · gỡ sau kiểm tra** đang bị khóa.

**Lời thoại:**

> “Dù đang dùng Supervisor, em chưa gỡ được trên dashboard vì khoảng cách vẫn ở vùng EMERGENCY. Giao diện yêu cầu mẫu SAFE và kiểm tra vùng làm việc trước khi gỡ.”

### 5C. SAFE không tự gỡ E-STOP

**Thao tác:** bấm mẫu mô phỏng lần thứ tư để chuyển sang **76.5 cm**. Chỉ cảm biến SAFE nhưng E-STOP vẫn ACTIVE. Có thể chuyển nhanh sang Reporter để cho thấy Reporter vẫn không gỡ được, rồi trở lại Supervisor.

**Lời thoại:**

> “Khoảng cách hiện đã trở lại SAFE, nhưng khóa E-STOP vẫn giữ nguyên. Hệ thống cần một thao tác gỡ có chủ đích từ Supervisor.
>
> Reporter có quyền báo cáo sự kiện, nhưng không có quyền gỡ dừng khẩn cấp. Owner cũng cần được cấp Supervisor ở Safety contract nếu muốn thực hiện thao tác này.”

### 5D. Gỡ bằng Supervisor

**Thao tác:** bằng Supervisor, bấm **Supervisor · gỡ sau kiểm tra**; xác nhận giao dịch vì sự kiện đã ghi chain. Chờ E-STOP về READY và trạng thái vùng về SAFE.

**Lời thoại:**

> “Sau khi kiểm tra vùng làm việc, Supervisor gỡ khóa. Trạng thái giám sát trở lại SAFE, nhưng bản ghi EMERGENCY và transaction hash vẫn được giữ để phục vụ kiểm tra sau này.”

**Kết quả cần có:** khóa được gỡ, bản ghi cũ vẫn còn. Nếu chưa ghi EMERGENCY lên chain, Supervisor dùng cùng nút để gỡ khóa giám sát sau khi SAFE; nút **gỡ khóa trên chain** chỉ dùng cho khóa đã ghi blockchain.

## Cảnh 6 — Demo công việc theo role, khoảng 2 phút

**Thao tác và lời thoại:** làm theo thứ tự, giữ nguyên tab.

| Role đang kết nối | Thao tác | Lời thoại | Kết quả |
| --- | --- | --- | --- |
| Worker | Nhập ví Worker; zone `ASSEMBLY-A`; task `HANDOFF-001`; bấm **Tạo permit** | “Worker khai báo người thực hiện, vùng và nhiệm vụ để đề nghị cấp phép làm việc.” | PENDING |
| Supervisor | Bấm **Approve** | “Supervisor xem xét và phê duyệt permit.” | APPROVED |
| Gateway | Bảo đảm mẫu đang SAFE và đã gỡ E-STOP; bấm **Ghi zone entry** | “Gateway ghi nhận zone entry bằng hash của mẫu telemetry hiện tại. Dashboard chặn thao tác này nếu còn E-STOP hoặc mẫu chưa SAFE.” | ACTIVE |
| Worker | Bấm **Xác nhận handoff**, xác nhận MetaMask | “Worker ghi xác nhận bàn giao giữa các bên tham gia.” | Handoff được ghi nhận |
| Worker | Bấm **Đóng permit**, xác nhận MetaMask | “Khi công việc hoàn tất, Worker đóng permit.” | COMPLETED |

**Lời thoại kết nối:**

> “Luồng công việc là Worker tạo yêu cầu, Supervisor phê duyệt, Gateway ghi nhận vào vùng và Worker xác nhận bàn giao, hoàn tất. Các bản ghi thể hiện lời xác nhận của tài khoản tham gia; việc kiểm tra vị trí và chuyển động thực tế cần thực hiện tại hiện trường.”

## Cảnh 7 — Kết thúc, khoảng 30 giây

**Thao tác:** quay lại tổng quan và nhật ký.

**Lời thoại:**

> “Qua demo, hệ thống đã thể hiện ba hành vi chính. Thứ nhất, EMERGENCY tự kích hoạt E-STOP ngay cả khi chưa ghi chain. Thứ hai, khóa được giữ khi khoảng cách trở lại SAFE và chỉ Supervisor được gỡ. Thứ ba, nhật ký tập trung vào EMERGENCY, còn smart contract kiểm tra quyền và lưu bằng chứng các bước công việc.
>
> Hướng phát triển tiếp theo là bổ sung kênh điều khiển có xác thực giữa Supervisor, gateway và thiết bị, đồng thời kiểm chứng cơ cấu dừng phần cứng. Em xin kết thúc phần demo.”

## Phần thay thế — Demo bằng ESP32 thật

Dùng phần này thay Cảnh 4 nếu muốn trình bày cảm biến thật. Giữ API, web server và gateway chạy cùng database. Các lệnh dưới đây dùng từ thư mục gốc, trong những terminal riêng; chỉ giữ một tiến trình đang đọc COM5.

```bat
.\.venv\Scripts\python.exe -m iot_code.gateway.api
```

```bat
.\.venv\Scripts\python.exe -m iot_code.gateway.serial_reader --port COM5
```

Lệnh Serial trên chạy off-chain, không cần private key. Trên dashboard chọn **ESP32 · gateway thật** và chờ **GATEWAY · LIVE**. Dùng vật mẫu để thay đổi khoảng cách; đọc trạng thái thực tế trên màn hình vì logic tại edge có thể bổ sung cảnh báo ngoài các ngưỡng khoảng cách.

| Thao tác với vật mẫu | Điều cần quan sát | Lời thoại ngắn |
| --- | --- | --- |
| Giữ vật ngoài 60 cm, chờ mẫu SAFE | Khoảng cách cập nhật trực tiếp | “Đây là telemetry thật từ HC-SR04 qua ESP32 và gateway.” |
| Đưa vật vào khoảng 30–60 cm | WARNING | “Hệ thống phát cảnh báo khi vật tiến vào vùng cảnh báo.” |
| Đưa vật vào khoảng hợp lệ 2–30 cm | EMERGENCY và E-STOP ACTIVE | “E-STOP giám sát bật ngay từ mẫu off-chain, không chờ giao dịch.” |
| Đưa vật ra ngoài 60 cm, chờ mẫu SAFE mới | Cảm biến SAFE; E-STOP vẫn ACTIVE | “Vùng đã an toàn hơn, nhưng khóa giám sát vẫn cần Supervisor gỡ.” |
| Dùng Supervisor, bấm **gỡ sau kiểm tra** | Khóa giám sát được gỡ | “Supervisor xác nhận gỡ khóa giám sát. Reset cơ cấu dừng phần cứng được thực hiện riêng tại thiết bị.” |

Nếu muốn tiếp tục Cảnh 5 bằng dữ liệu thật, dùng Reporter bấm ghi EMERGENCY chưa gửi lên chain. Khi gateway đã tự gửi bằng `--write-chain`, kiểm tra trạng thái giao dịch trước khi chọn sự kiện để trình bày.

## Cảnh bổ sung — Thu hồi Supervisor, khoảng 1 phút

1. Tạo EMERGENCY mới, sau đó đưa mẫu về SAFE nhưng giữ E-STOP ACTIVE.
2. Owner chọn ví Supervisor, bấm **Thu hồi**, xác nhận hai giao dịch.
3. Chuyển sang ví Supervisor vừa bị thu hồi; nút gỡ bị khóa.
4. Owner cấp lại Supervisor, rồi Supervisor gỡ sau kiểm tra.

**Lời thoại:**

> “Quyền Supervisor có thể được thu hồi. Tài khoản từng có quyền không tiếp tục gỡ được sau khi bị thu hồi. Việc kiểm tra quyền được thực hiện tại contract, nên chỉ đổi nhãn tài khoản trên giao diện không tạo ra quyền mới.”

## Trả lời câu hỏi thường gặp

**Tại sao off-chain mà E-STOP vẫn bật?**

> “E-STOP giám sát được kích hoạt từ telemetry EMERGENCY. Blockchain lưu bằng chứng sau đó. Quyền Supervisor để gỡ trên dashboard được đọc từ Safety contract.”

**Tại sao EMERGENCY rồi mà nút gỡ còn bị khóa?**

> “Dashboard cần đủ quyền Supervisor và mẫu SAFE mới. Ví chưa có quyền, nhập nhầm contract, mất dữ liệu hoặc khoảng cách còn nguy hiểm đều làm nút gỡ bị khóa.”

**Owner của hai contract có nghĩa là gì?**

> “Mỗi contract có một Owner riêng, là ví deploy contract đó. Script của dự án deploy cả hai bằng cùng một ví. Nút cấp Supervisor cập nhật cả hai nên yêu cầu Owner của cả hai contract.”

**Gateway có tự ghi blockchain không?**

> “Có, khi chạy với `--write-chain` và cấu hình tài khoản có quyền Reporter. Chạy off-chain vẫn đo, phân loại và lưu telemetry. Trong demo này, em dùng Reporter ký thủ công để thấy rõ thời điểm ghi bằng chứng.”

**Blockchain có chứng minh cảm biến đo đúng không?**

> “Cam kết giúp phát hiện thay đổi bản ghi sau khi ghi nhận. Độ đúng của cảm biến và cơ cấu dừng phải được kiểm chứng riêng.”

**Tại sao không lưu SAFE và WARNING trong nhật ký này?**

> “Nhật ký EMERGENCY tập trung vào tình huống khẩn cấp. SAFE và WARNING vẫn cập nhật trực tiếp và dữ liệu gateway vẫn được giữ ngoài chain.”

## Khi thao tác demo chưa cho kết quả mong đợi

| Hiện tượng | Việc cần kiểm tra |
| --- | --- |
| Lỗi đọc quyền hoặc `execution reverted` | Đúng ô HRCSafetyLog/WorkPermitHandoff, đúng mạng ví và contract đang chạy |
| Supervisor không gỡ được | Quyền ở Safety contract; mẫu SAFE mới; không còn yêu cầu dừng; giao dịch trước đã hoàn tất |
| Ghi EMERGENCY bị khóa | Ví Reporter/Owner; địa chỉ Safety; có EMERGENCY chưa có tx ở nguồn đang chọn |
| ESP32 chưa có dữ liệu mới | COM5, Serial gateway, API và database đang dùng |
| Gateway báo private key dài 20 byte | Đã dùng địa chỉ ví; cần dòng Private Key 32 byte khi chạy `--write-chain`, hoặc chạy off-chain không có cờ này |

Nếu cần minh họa kiểm tra contract trong terminal, dùng `npm.cmd run demo:roles:check` tại thư mục `contracts`. Lệnh này chạy trên mạng tạm thời và in kết quả `PASS`; các địa chỉ của lần chạy tạm thời không dùng cho dashboard đang kết nối node local.
