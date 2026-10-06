const hre = require("hardhat");

async function main() {
  const [deployer, supervisor] = await hre.ethers.getSigners();
  const factory = await hre.ethers.getContractFactory("HRCSafetyLog");
  const contract = await factory.deploy();
  await contract.waitForDeployment();
  await (await contract.setSupervisor(supervisor.address, true)).wait();

  const deviceIdHash = hre.ethers.keccak256(hre.ethers.toUtf8Bytes("HRC-ESP32-01"));
  const eventHash = hre.ethers.keccak256(hre.ethers.toUtf8Bytes("demo-emergency-event-001"));
  const tx = await contract.recordEvent(eventHash, deviceIdHash, Math.floor(Date.now() / 1000), 3, true);
  await tx.wait();

  const event = await contract["getEvent(bytes32)"](eventHash);
  console.log(JSON.stringify({
    deployer: deployer.address,
    supervisor: supervisor.address,
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
