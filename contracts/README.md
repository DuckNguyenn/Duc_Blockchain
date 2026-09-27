# Smart contracts

Project Hardhat độc lập. Contract nhận `warningId`, `logHash`, `deviceId`, `sensorId` và mức độ (`WARNING` hoặc `SENSOR_FAULT`) từ gateway ESP32. Contract chỉ lưu bằng chứng audit, không điều khiển cảm biến hay thiết bị chấp hành.

```powershell
cd contracts
npm install
npx hardhat test
```