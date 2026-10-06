const hre = require("hardhat");
const assert = require("node:assert/strict");

async function confirmed(transaction) {
  return (await transaction).wait();
}

async function rejected(label, action, reason) {
  await assert.rejects(async () => confirmed(action()), (error) => String(error.message).includes(reason));
  console.log(`PASS | ${label} | ${reason}`);
}

async function main() {
  const { ethers } = hre;
  const [owner, reporter, supervisor, gateway, worker, outsider] = await ethers.getSigners();
  const safety = await (await ethers.getContractFactory("HRCSafetyLog", owner)).deploy();
  const permit = await (await ethers.getContractFactory("WorkPermitHandoff", owner)).deploy();
  await safety.waitForDeployment();
  await permit.waitForDeployment();
  await confirmed(safety.setReporter(reporter.address, true));
  await confirmed(safety.setSupervisor(supervisor.address, true));
  await confirmed(permit.setSupervisor(supervisor.address, true));
  await confirmed(permit.setGateway(gateway.address, true));
  console.log(JSON.stringify({
    network: hre.network.name,
    contract: await safety.getAddress(), permitContract: await permit.getAddress(),
    roles: Object.fromEntries(Object.entries({ owner, reporter, supervisor, gateway, worker, outsider }).map(([role, signer]) => [role, signer.address]))
  }, null, 2));

  const device = ethers.id("HRC-ESP32-01");
  const timestamp = (await ethers.provider.getBlock("latest")).timestamp;
  await rejected("Worker khong tu cap Supervisor", () => safety.connect(worker).setSupervisor(worker.address, true), "not owner");
  for (const [name, severity] of [["SAFE", 0], ["WARNING", 1]]) {
    const event = ethers.id(`demo-${name}`);
    await rejected(`${name} khong vao safety log`, () => safety.connect(reporter).recordEvent(event, device, timestamp, severity, false), "only emergency events");
    assert.equal(await safety.eventExists(event), false);
  }
  await rejected("Outsider khong ghi EMERGENCY", () => safety.connect(outsider).recordEvent(ethers.id("outsider"), device, timestamp, 3, true), "not reporter");
  const emergency = ethers.id("demo-emergency-001");
  await confirmed(safety.connect(reporter).recordEvent(emergency, device, timestamp, 3, true));
  assert.equal(await safety.deviceLocked(device), true);
  assert.equal(await safety.emergencyStopByDevice(device), true);
  console.log("PASS | Reporter ghi EMERGENCY => E-STOP ACTIVE, device LOCKED");
  await rejected("Khong ghi trung EMERGENCY", () => safety.connect(reporter).recordEvent(emergency, device, timestamp, 3, true), "event already recorded");
  for (const [role, signer] of Object.entries({ owner, reporter, gateway, worker, outsider })) {
    await rejected(`${role} khong go E-STOP`, () => safety.connect(signer).clearEmergencyStop(device), "not supervisor");
    assert.equal(await safety.deviceLocked(device), true);
  }
  // The Supervisor checks the workspace before this transaction; the ledger
  // cannot determine the physical distance from an off-chain sensor.
  await confirmed(safety.connect(supervisor).clearEmergencyStop(device));
  assert.equal(await safety.deviceLocked(device), false);
  assert.equal(await safety.emergencyStopByDevice(device), false);
  assert.equal(await safety.eventExists(emergency), true);
  console.log("PASS | Supervisor go khoa; log EMERGENCY van duoc giu");

  const permitId = ethers.id("demo-work-permit-001");
  const start = (await ethers.provider.getBlock("latest")).timestamp;
  await confirmed(permit.connect(worker).createPermit(permitId, ethers.id(worker.address), ethers.id("ASSEMBLY-A"), ethers.id("HANDOFF-001"), worker.address, start, start + 3600));
  await rejected("Gateway khong entry truoc approve", () => permit.connect(gateway).recordZoneEntry(permitId, ethers.id("safe-telemetry")), "permit not approved");
  await rejected("Worker khong approve permit", () => permit.connect(worker).approvePermit(permitId), "not supervisor");
  await confirmed(permit.connect(supervisor).approvePermit(permitId));
  await rejected("Reporter khong ghi zone entry", () => permit.connect(reporter).recordZoneEntry(permitId, ethers.id("safe-telemetry")), "not gateway");
  await confirmed(permit.connect(gateway).recordZoneEntry(permitId, ethers.id("safe-telemetry")));
  await rejected("Outsider khong handoff", () => permit.connect(outsider).confirmHandoff(ethers.id("outsider-handoff"), permitId, ethers.id("HRC-ROBOT-01")), "not handoff participant");
  await confirmed(permit.connect(worker).confirmHandoff(ethers.id("demo-handoff-001"), permitId, ethers.id("HRC-ROBOT-01")));
  await confirmed(permit.connect(worker).completePermit(permitId));
  assert.equal(Number((await permit.getPermit(permitId)).status), 4);
  console.log("PASS | Worker tao permit => Supervisor approve => Gateway entry => Worker handoff / COMPLETED");

  await confirmed(safety.connect(reporter).recordEvent(ethers.id("demo-emergency-002"), device, start, 3, true));
  await confirmed(safety.setSupervisor(supervisor.address, false));
  await confirmed(permit.setSupervisor(supervisor.address, false));
  await rejected("Supervisor bi thu hoi khong go khoa", () => safety.connect(supervisor).clearEmergencyStop(device), "not supervisor");
  assert.equal(await safety.deviceLocked(device), true);
  // Restore the demo roles and leave the demo devices ready for a UI walkthrough.
  await confirmed(safety.setSupervisor(supervisor.address, true));
  await confirmed(permit.setSupervisor(supervisor.address, true));
  await confirmed(safety.connect(supervisor).clearEmergencyStop(device));
  console.log("PASS | Tat ca kich ban role hoan tat; Supervisor da duoc cap lai, device CLEAR");
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
