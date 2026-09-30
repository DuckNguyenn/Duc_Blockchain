# Rà soát on-chain / off-chain của SonarChain

Ngày rà soát: 2026-09-30. Đây là kết quả kiểm tra mã nguồn hiện có và đề xuất phạm vi implementation/test, **không phải tuyên bố các cải tiến đã được triển khai**.

## Kết luận

Project có các thành phần on-chain và off-chain, nhưng ranh giới chưa nhất quán từ telemetry tới lưu trữ, giao dịch, xác minh và UI. Không nên xem trạng thái blockchain hoặc chữ `LOCKED` trên dashboard là bằng chứng motor đã dừng. Phần cứng hiện chưa có cơ cấu E-Stop vật lý được tích hợp/chứng nhận.

## Hiện trạng dữ liệu và trách nhiệm

| Thành phần | Vị trí hiện tại | Trách nhiệm | Khoảng trống |
|---|---|---|---|
| CSV single-sensor, nhãn, feature, model | Off-chain: `ai_model/` | Huấn luyện và replay | Model metadata/phiên bản chưa được cam kết cùng safety event |
| ESP32 telemetry | Off-chain: Serial | Đo một khoảng cách | Serial không phải nguồn đã được xác thực; các firmware/ID nguồn chưa thống nhất |
| Phân loại 30/60 cm và AI | Off-chain: gateway/UI | Quyết định an toàn trước chain | Browser là mô phỏng; không phải bộ điều khiển vật lý |
| Chi tiết safety event | Off-chain: Python JSON hoặc browser memory | Lưu dữ liệu chi tiết để kiểm toán | CSV pipeline chỉ trả/in JSON, browser event mất khi reload; chưa có kho evidence chung |
| `HRCSafetyLog` | On-chain | Hash event/device, timestamp, severity, reporter, E-Stop/device lock logic | Chưa cam kết một schema evidence chung với mọi producer |
| `WorkPermitHandoff` | On-chain | Worker/requester/approver, hash zone/task, thời hạn, vòng đời permit, handoff | Zone entry không kiểm chứng telemetryHash với SafetyLog; handoff/complete thiếu kiểm tra thời hạn |
| `SafetyLog` legacy | On-chain | Commitment warning và phân quyền gateway | Deployment chính không deploy contract này; adapter legacy vẫn sử dụng nó |
| Tx/receipt và xác minh | Off-chain + đọc chain | Đối chiếu giao dịch và commitment | Thiếu outbox bền vững, recovery và verifier đối chiếu đầy đủ |

## Các vấn đề đã xác định từ mã

1. **Hai đường ghi chain khác nhau.** `iot_code/blockchain.py` gọi `SafetyLog.recordWarning`; `gateway/blockchain_client.py` và dashboard gọi `HRCSafetyLog.recordEvent`. `scripts/deploy.js` chỉ deploy HRCSafetyLog và WorkPermitHandoff.
2. **Commitment không thống nhất.** CSV pipeline tạo SHA-256 từ chuỗi event; Python adapter tiếp tục Keccak trên chuỗi hex đó. Browser dùng Keccak trực tiếp trên chuỗi telemetry. Legacy dùng SHA-256 của JSON. Không có một quy tắc xuyên ngôn ngữ và schema version được kiểm thử chung.
3. **Chưa bảo vệ toàn bộ bản ghi.** Hash CSV không bao gồm confidence, chính sách/model và những trường evidence khác. Đổi các trường đó không nhất thiết đổi commitment.
4. **Thời gian audit lệch.** Adapter nhận `timestamp=int(time.time())` lúc submit thay vì thời điểm đo có trong event. Timestamp thiết bị, UTC gateway và block timestamp chưa được phân biệt rõ.
5. **Gateway có mã trùng và khác hành vi.** `iot_code/gateway.py` nhận EMERGENCY, nhưng package thực được import `iot_code/gateway/__init__.py` chỉ nhận WARNING/SENSOR_FAULT. Các test đang import package này.
6. **Lỗi RPC có thể cắt luồng xử lý.** Package compatibility và CSV pipeline không bảo vệ vòng xử lý khỏi lỗi chain. Chưa có cơ chế lưu trước, submit sau, retry/reconcile khi timeout.
7. **Nonce và receipt.** Adapter legacy không kiểm tra `receipt.status`; adapter mới dùng nonce latest và không lưu pending tx để phục hồi. Timeout sau khi node nhận tx dễ khiến ứng dụng không biết tx đã được ghi hay chưa.
8. **Xác minh chưa đi tới chain.** `iot_code.verify` chỉ kiểm tra JSON với hash bên trong chính file. Nếu sửa file và tính lại hash thì kiểm tra local có thể đạt dù khác bằng chứng đã cam kết. `SafetyLog.verifyLogHash` có thể trả true cho ID không tồn tại khi calculatedHash là zero.
9. **Input và fail-safe.** Không có validation thống nhất cho NaN/Infinity, âm, thiếu distance, timestamp/schema hoặc threshold cấu hình sai. Cần tránh mẫu lỗi bị coi là SAFE.
10. **E-Stop trong UI chỉ ở bộ nhớ.** Reload/đổi ví/chain làm mất latch local; UI chưa đọc trạng thái `emergencyStopByDevice`/quyền từ chain. Ghi emergency từ nút record thông thường chưa đồng bộ `estopOnChain`.
11. **Device của bằng chứng có thể khác device ghi chain.** Browser tạo event với device cố định nhưng luồng E-Stop dùng giá trị input `estopDevice` để băm device trên chain.
12. **Phân quyền UI chưa được đọc on-chain.** Nút được enable theo connected signer, không theo owner/reporter/supervisor/gateway thật. Contract vẫn chặn giao dịch trái quyền nhưng UI dễ gây nhầm lẫn và phí giao dịch.
13. **Workflow permit chưa ràng buộc bằng chứng.** `recordZoneEntry` nhận hash bất kỳ; handoff/complete không kiểm tra permit hết hạn. Không có policy buộc handoff trước complete; policy này cần được mô tả rõ trước khi thay đổi.
14. **Khóa logic không đồng nghĩa bảo mật dữ liệu.** Wallet address, thời hạn, tx sender và metadata vẫn công khai; hash ID ít entropy có thể bị dò. Chưa có retention/backup/kiểm soát đọc evidence ngoài chain.
15. **Tài liệu cũ còn hai cảm biến.** README/report có `left_cm/right_cm`, khác dataset distance_cm mới và một số ví dụ/số đường dẫn đã lỗi thời.

## Ranh giới implementation đề xuất

```text
HC-SR04 / replay / browser demo
              |
              v
VALIDATE -> LOCAL SAFETY DECISION / LATCH
              |
              v
VERSIONED OFF-CHAIN EVIDENCE -> DURABLE OUTBOX
                                      |
                              submit / reconcile
                                      v
                          HRCSafetyLog / Permit ledger
                                      |
                                      v
                    RECEIPT + FULL EVIDENCE VERIFICATION
```

### Off-chain

- Schema single-sensor versioned: nguồn, device/sensor, event identity, thời điểm đo/nhận, distance, chất lượng mẫu, severity, emergency flag, policy/model provenance. Không đưa private key vào evidence hoặc log.
- Quy tắc serialization/canonicalization và hash thống nhất giữa Python và browser, có fixture cross-language. Tách metadata giao dịch có thể thay đổi khỏi nội dung evidence bất biến.
- Lưu evidence trước khi submit; không overwrite nội dung khác dưới cùng ID. Có trạng thái queued/submitted/confirmed/failed hoặc tương đương, tx hash/chain ID/contract/block metadata và retry có giới hạn.
- Lỗi mạng/MetaMask/tx không được xóa hoặc gỡ local latch. On-chain clear chỉ là audit, không được tự khởi động phần cứng.
- Invalid sensor input dẫn tới chất lượng lỗi/fail-safe, không trở thành SAFE qua NaN hoặc coercion.
- CLI replay/serial, inspect, verify và retry dùng cùng public workflow; không có hai adapter ngầm trỏ sang hai contract khác nhau.

### On-chain

- HRCSafetyLog là ledger safety chính; giữ dữ liệu thô/model/file/PII ngoài chain.
- Role enforcement, dữ liệu hợp lệ/nonzero, chống duplicate, nhất quán severity/stop và latch không tự clear bởi event SAFE.
- Work permit có ma trận role và vòng đời/thời hạn rõ ràng. Phân biệt telemetry commitment được ghi và telemetry tự khai; nếu cần liên kết hai contract phải nâng version/deploy mới.
- Mọi ABI, deploy/demo, UI và Python adapter phải cập nhật đồng bộ. Không gửi giao dịch lên mainnet hoặc cấp role thật trong quá trình làm local tests.
- Ghi rõ blockchain chỉ chứng minh cam kết và nguồn reporter; không xác nhận cảm biến đo đúng, hiện trạng vật lý hoặc quyết định safety-certified.

### Vận hành, bảo mật và xác minh

- Kiểm tra chain ID/contract code/address, tx receipt status, số confirmations và block hash; không gắn nhãn verified chỉ vì đã có tx hash.
- Timeout phải reconcile commitment/receipt trước retry để tránh duplicate và nonce collision.
- Bí mật giữ trong môi trường ngoài repo; reporter ít quyền, owner tách khỏi gateway; backup/retention và hạn chế truy cập evidence.
- Kiểm toán: local integrity chỉ là bước đầu; verified on-chain yêu cầu đối chiếu digest, device, timestamp, severity, flag và context chain/contract.
- Reorg/local-chain reset, mất file evidence, giả reporter hoặc sensor, disk/RPC failure được mô tả như giới hạn/threat model và có test phù hợp.

## Seams kiểm thử đề xuất — chờ người dùng xác nhận

| Seam công khai | Các nhóm test cần bổ sung |
|---|---|
| Solidity API của HRCSafetyLog/SafetyLog/WorkPermitHandoff | Quyền cấp/thu hồi role; outsider; dữ liệu zero/không hợp lệ; duplicate; lock/clear; SAFE không gỡ lock; permit transition và validity window |
| Telemetry/CSV qua public gateway APIs/CLI tới evidence store | Mẫu single-sensor; biên 30/60 cm; dữ liệu lỗi; chính sách hard threshold ưu tiên AI; EMERGENCY không bị bỏ qua; persistence trước submit; restart/replay |
| JSON evidence qua public verify APIs/CLI tới chain | Known digest fixtures; khác thứ tự key; sửa distance/model/policy; tự tính lại hash; ID không tồn tại; sai device/metadata/chain/contract; read-only verification |
| RPC submission/retry qua adapter/outbox public interface | RPC down; receipt revert; timeout sau broadcast; retry/reconcile/idempotency; pending nonce; confirm/reorg; không lộ key; local action không phụ thuộc thành công chain |
| Dashboard public workflow | Local E-Stop tự bật/latch; submit thất bại không clear; quyền/chain/device đúng; trạng thái local và on-chain tách riêng; reload/account/network change; export/verify evidence |

Triển khai theo từng lát dọc: một hành vi test thất bại, sửa tối thiểu, chạy lại; không viết test vào nội bộ/private implementation.

## Kiểm tra đã thực hiện

`npm.cmd test` tại `contracts/`: **9 tests passed** sau khi compile source canonical; sau khi bổ sung các test invariant mới, suite sẽ tiếp tục bảo vệ boundary/schema/latch. `python -m unittest discover -s tests -p 'test_*.py'`: **9 tests passed** khi chạy bằng Python interpreter có dependencies. Kết quả này không chứng minh RPC thật/MetaMask/phần cứng, và không bao gồm mọi nhóm test vận hành đề xuất ở trên.
