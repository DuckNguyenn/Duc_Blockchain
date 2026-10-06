const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("HRCSafetyLog", function () {
  it("records an emergency event and locks the device", async function () {
    const [owner] = await ethers.getSigners();
    const Factory = await ethers.getContractFactory("HRCSafetyLog");
    const log = await Factory.deploy();
    await log.waitForDeployment();

    const device = ethers.keccak256(ethers.toUtf8Bytes("HRC-ESP32-01"));
    const eventHash = ethers.keccak256(ethers.toUtf8Bytes("event-1"));
    await log.recordEvent(eventHash, device, 123, 3, true);

    // ethers v6 reserves `getEvent` for ABI event introspection, so use the
    // full signature to call the Solidity getter with the same name.
    const event = await log["getEvent(bytes32)"](eventHash);
    expect(event.reporter).to.equal(owner.address);
    expect(event.emergencyStop).to.equal(true);
    expect(await log.emergencyStopByDevice(device)).to.equal(true);
    expect(await log.deviceLocked(device)).to.equal(true);
  });

  it("rejects duplicate event hashes", async function () {
    const Factory = await ethers.getContractFactory("HRCSafetyLog");
    const log = await Factory.deploy();
    await log.waitForDeployment();
    const device = ethers.keccak256(ethers.toUtf8Bytes("device"));
    const hash = ethers.keccak256(ethers.toUtf8Bytes("same"));
    await log.recordEvent(hash, device, 123, 3, true);
    await expect(log.recordEvent(hash, device, 124, 3, true)).to.be.revertedWith("event already recorded");
  });

  it("enforces versioned evidence semantics and rejects inconsistent emergency flags", async function () {
    const [owner, reporter] = await ethers.getSigners();
    const Factory = await ethers.getContractFactory("HRCSafetyLog");
    const log = await Factory.deploy();
    await log.waitForDeployment();
    await log.setReporter(reporter.address, true);
    const device = ethers.keccak256(ethers.toUtf8Bytes("HRC-ESP32-01"));
    const evidence = ethers.keccak256(ethers.toUtf8Bytes("evidence-v1"));
    const schema = await log.EVIDENCE_SCHEMA_V1();
    await expect(log.connect(reporter).recordEvidence(evidence, device, 123, 3, true, schema)).to.emit(log, "SafetyEvidenceRecorded");
    const stored = await log["getEvent(bytes32)"](evidence);
    expect(stored.evidenceHash).to.equal(evidence);
    expect(stored.evidenceSchema).to.equal(schema);
    await expect(log.recordEvidence(ethers.id("bad"), device, 124, 0, true, schema)).to.be.revertedWith("only emergency events");
    await expect(log.recordEvidence(ethers.id("bad-stop"), device, 124, 3, false, schema)).to.be.revertedWith("emergency requires stop");
    await expect(log.recordEvidence(ethers.id("bad2"), device, 0, 0, false, schema)).to.be.revertedWith("empty measured timestamp");
    await expect(log.recordEvidence(ethers.id("bad3"), device, 123, 0, false, ethers.id("wrong-schema"))).to.be.revertedWith("unsupported evidence schema");
  });

  it("rejects an unapproved reporter", async function () {
    const [, outsider] = await ethers.getSigners();
    const Factory = await ethers.getContractFactory("HRCSafetyLog");
    const log = await Factory.deploy();
    await log.waitForDeployment();
    await expect(log.connect(outsider).recordEvent(ethers.id("outsider"), ethers.id("device"), 123, 0, false)).to.be.revertedWith("not reporter");
  });

  it("rejects SAFE/WARNING/DANGER without changing the emergency latch", async function () {
    const Factory = await ethers.getContractFactory("HRCSafetyLog");
    const log = await Factory.deploy();
    await log.waitForDeployment();
    const device = ethers.id("device-latch");
    await log.recordEvent(ethers.id("danger-latch"), device, 123, 3, true);
    for (const severity of [0, 1, 2]) {
      const hash = ethers.id(`non-emergency-${severity}`);
      await expect(log.recordEvent(hash, device, 124, severity, false)).to.be.revertedWith("only emergency events");
      await expect(log.recordEvidence(hash, device, 124, severity, false, await log.EVIDENCE_SCHEMA_V1())).to.be.revertedWith("only emergency events");
      expect(await log.eventExists(hash)).to.equal(false);
    }
    expect(await log.deviceLocked(device)).to.equal(true);
    expect(await log.emergencyStopByDevice(device)).to.equal(true);
  });

  it("only an explicitly granted Supervisor can clear, including after revocation", async function () {
    const [owner, reporter, supervisor, worker] = await ethers.getSigners();
    const log = await (await ethers.getContractFactory("HRCSafetyLog")).deploy();
    await log.waitForDeployment();
    await log.setReporter(reporter.address, true);
    await expect(log.connect(worker).setSupervisor(worker.address, true)).to.be.revertedWith("not owner");
    await expect(log.setSupervisor(ethers.ZeroAddress, true)).to.be.revertedWith("empty supervisor");
    await expect(log.setSupervisor(supervisor.address, true)).to.emit(log, "SupervisorUpdated").withArgs(supervisor.address, true);
    const device = ethers.id("supervised-device");
    await log.connect(reporter).recordEvent(ethers.id("emergency-1"), device, 123, 3, true);
    for (const account of [owner, reporter, worker]) {
      await expect(log.connect(account).clearEmergencyStop(device)).to.be.revertedWith("not supervisor");
      expect(await log.deviceLocked(device)).to.equal(true);
    }
    await expect(log.connect(supervisor).clearEmergencyStop(device)).to.emit(log, "EmergencyStopChanged").withArgs(device, false, ethers.ZeroHash);
    expect(await log.deviceLocked(device)).to.equal(false);
    expect(await log.emergencyStopByDevice(device)).to.equal(false);
    expect(await log.eventExists(ethers.id("emergency-1"))).to.equal(true);
    await log.connect(reporter).recordEvent(ethers.id("emergency-2"), device, 124, 3, true);
    await log.setSupervisor(supervisor.address, false);
    await expect(log.connect(supervisor).clearEmergencyStop(device)).to.be.revertedWith("not supervisor");
    expect(await log.deviceLocked(device)).to.equal(true);
  });
});
