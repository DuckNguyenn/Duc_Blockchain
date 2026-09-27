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

    const event = await log.getEvent(eventHash);
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
});
