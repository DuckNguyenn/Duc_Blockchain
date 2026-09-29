# SonarChain Web3 dashboard

Dashboard tĩnh cho HRC Safety Log: chạy mô phỏng dữ liệu hai cảm biến HC-SR04 ngay trên trình duyệt, hoặc kết nối MetaMask để gọi `HRCSafetyLog.recordEvent`.

## Chạy local

Từ thư mục gốc repository:

```powershell
python -m http.server 8080 -d web3
```

Mở <http://localhost:8080>. Nhấn **Chạy mô phỏng** để tạo event. Để ghi on-chain, chạy Hardhat local theo hướng dẫn ở `contracts/README.md`, deploy contract, nhập địa chỉ contract rồi kết nối MetaMask với chain `31337`.

Dashboard chỉ lưu hash event, hash thiết bị, severity và cờ EmergencyStop lên chain. Raw telemetry vẫn ở gateway/off-chain; blockchain không nằm trong vòng điều khiển dừng thời gian thực.
