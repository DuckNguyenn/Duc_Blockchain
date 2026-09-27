const hre = require("hardhat");

async function main() {
  const [deployer] = await hre.ethers.getSigners();
  const factory = await hre.ethers.getContractFactory("HRCSafetyLog");
  const contract = await factory.deploy();
  await contract.waitForDeployment();

  const deviceIdHash = hre.ethers.keccak256(hre.ethers.toUtf8Bytes("HRC-ESP32-01"));
  const eventHash = hre.ethers.keccak256(hre.ethers.toUtf8Bytes("demo-danger-event-001"));
  const tx = await contract.recordEvent(eventHash, deviceIdHash, Math.floor(Date.now() / 1000), 2, true);
  await tx.wait();

  const event = await contract.getEvent(eventHash);
  console.log(JSON.stringify({
    deployer: deployer.address,
    contract: await contract.getAddress(),
    eventHash,
    deviceIdHash,
    severity: Number(event.severity),
    emergencyStop: event.emergencyStop,
    deviceLocked: await contract.deviceLocked(deviceIdHash)
  }, null, 2));
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
