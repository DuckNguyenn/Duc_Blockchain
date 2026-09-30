# Smart Contracts

Đây là phần Blockchain của HRC Safety Log.

- `HRCSafetyLog.sol`: ledger safety chính. Nhận evidence digest v1 qua `recordEvidence`; `recordEvent` được giữ làm compatibility API. Lưu digest/schema/thời điểm đo/severity/reporter và trạng thái EmergencyStop; raw telemetry ở off-chain.
- `WorkPermitHandoff.sol`: cấp phép zone, phê duyệt supervisor và xác nhận human–robot handoff.
- `scripts/deploy.js`: deploy contract lên Hardhat local node.
- `scripts/demo.js`: ghi một sự kiện khẩn cấp và đọc lại trạng thái khóa.
- `test/HRCSafetyLog.js`: kiểm tra quyền reporter, evidence schema, invariant severity/stop, latch và chống ghi trùng.
- `abi/HRCSafetyLog.json`: ABI được gateway Python sử dụng.

Chạy Demo:

```powershell
cd contracts
npm.cmd install
npm.cmd run compile
npm.cmd test
npm.cmd run node
```

Trong một terminal khác, sau khi node chạy:

```powershell
npm.cmd run deploy
npm.cmd run demo
```

`npm.cmd run deploy` in ra ba địa chỉ: `contract=` cho HRCSafetyLog, `permitContract=` cho WorkPermitHandoff và `legacySafetyLog=` cho contract legacy `SafetyLog`. Luồng mới dùng `contract=`; legacy chỉ dành cho compatibility.

## Ranh giới on-chain/off-chain

- Off-chain: telemetry chi tiết, evidence JSON v1, confidence, policy/model version, outbox, retry state và file phân tích.
- On-chain: `evidenceHash`, `deviceIdHash`, `evidenceSchema`, measured timestamp, severity, emergency flag, reporter và E-Stop logic.
- Gateway lưu evidence trước khi submit. RPC failure giữ file pending để retry/reconcile; không coi transaction failure là mất quyết định local.
- Blockchain là audit/evidence layer, không điều khiển motor/relay/E-Stop vật lý.

On Windows PowerShell, use `npm.cmd` when execution policy blocks `npm.ps1`.
The local RPC is `http://127.0.0.1:8545` (chain ID `31337`).

Smart Contract chỉ lưu bằng chứng audit và trạng thái logic. Nó không thay thế mạch dừng khẩn cấp vật lý hoặc hệ thống safety-certified.
