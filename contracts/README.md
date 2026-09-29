# Smart Contracts

Đây là phần Blockchain của HRC Safety Log.

- `HRCSafetyLog.sol`: lưu hash sự kiện an toàn, định danh thiết bị đã băm và trạng thái EmergencyStop/khóa thiết bị.
- `WorkPermitHandoff.sol`: cấp phép zone, phê duyệt supervisor và xác nhận human–robot handoff.
- `scripts/deploy.js`: deploy contract lên Hardhat local node.
- `scripts/demo.js`: ghi một sự kiện khẩn cấp và đọc lại trạng thái khóa.
- `test/HRCSafetyLog.js`: kiểm tra EmergencyStop, khóa thiết bị và chống ghi trùng event hash.
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

`npm.cmd run deploy` in ra hai địa chỉ: `contract=` cho HRCSafetyLog và `permitContract=` cho WorkPermitHandoff. Nhập đúng `permitContract` vào panel Work permit trên dashboard.

On Windows PowerShell, use `npm.cmd` when execution policy blocks `npm.ps1`.
The local RPC is `http://127.0.0.1:8545` (chain ID `31337`).

Smart Contract chỉ lưu bằng chứng audit và trạng thái logic. Nó không thay thế mạch dừng khẩn cấp vật lý hoặc hệ thống safety-certified.
