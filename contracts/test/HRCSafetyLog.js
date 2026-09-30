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
    await log.recordEvent(eventHash, device, 123, 2, true);

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
    await log.recordEvent(hash, device, 123, 0, false);
    await expect(log.recordEvent(hash, device, 124, 0, false)).to.be.revertedWith("event already recorded");
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
    await expect(log.recordEvidence(ethers.id("bad"), device, 124, 0, true, schema)).to.be.revertedWith("stop requires danger severity");
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

  it("does not clear the emergency latch when a later safe event is recorded", async function () {
    const Factory = await ethers.getContractFactory("HRCSafetyLog");
    const log = await Factory.deploy();
    await log.waitForDeployment();
    const device = ethers.id("device-latch");
    await log.recordEvent(ethers.id("danger-latch"), device, 123, 3, true);
    await log.recordEvent(ethers.id("safe-after-latch"), device, 124, 0, false);
    expect(await log.deviceLocked(device)).to.equal(true);
    expect(await log.emergencyStopByDevice(device)).to.equal(true);
  });
});
