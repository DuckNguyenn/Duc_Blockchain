const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("WorkPermitHandoff", function () {
  async function deployed() {
    const [owner, worker, requester, outsider] = await ethers.getSigners();
    const Factory = await ethers.getContractFactory("WorkPermitHandoff");
    const contract = await Factory.deploy();
    await contract.waitForDeployment();
    return { contract, owner, worker, requester, outsider };
  }

  async function createAndApprove(contract, worker, requester) {
    const permitId = ethers.keccak256(ethers.toUtf8Bytes("permit-1"));
    const workerId = ethers.keccak256(ethers.toUtf8Bytes("worker-1"));
    const zoneId = ethers.keccak256(ethers.toUtf8Bytes("zone-a"));
    const taskId = ethers.keccak256(ethers.toUtf8Bytes("task-1"));
    const now = (await ethers.provider.getBlock("latest")).timestamp;
    await contract.connect(requester).createPermit(permitId, workerId, zoneId, taskId, worker.address, now, now + 3600);
    await contract.approvePermit(permitId);
    return { permitId, workerId, zoneId, taskId };
  }

  it("creates, approves, activates and completes a permit with a worker handoff", async function () {
    const { contract, owner, worker, requester } = await deployed();
    const { permitId, taskId } = await createAndApprove(contract, worker, requester);
    const telemetryHash = ethers.keccak256(ethers.toUtf8Bytes("sonar-event"));
    await contract.recordZoneEntry(permitId, telemetryHash);
    const handoffId = ethers.keccak256(ethers.toUtf8Bytes("handoff-1"));
    const robotId = ethers.keccak256(ethers.toUtf8Bytes("robot-1"));
    await expect(contract.connect(worker).confirmHandoff(handoffId, permitId, robotId)).to.emit(contract, "HandoffConfirmed");
    const handoff = await contract.getHandoff(handoffId);
    expect(handoff.taskIdHash).to.equal(taskId);
    await contract.connect(worker).completePermit(permitId);
    const permit = await contract.getPermit(permitId);
    expect(permit.status).to.equal(4); // COMPLETED
    expect(permit.approver).to.equal(owner.address);
  });

  it("rejects activation before supervisor approval and rejects an outsider handoff", async function () {
    const { contract, worker, requester, outsider } = await deployed();
    const permitId = ethers.keccak256(ethers.toUtf8Bytes("permit-2"));
    const now = (await ethers.provider.getBlock("latest")).timestamp;
    await contract.connect(requester).createPermit(permitId, ethers.id("worker-2"), ethers.id("zone-b"), ethers.id("task-2"), worker.address, now, now + 3600);
    await expect(contract.recordZoneEntry(permitId, ethers.id("telemetry"))).to.be.revertedWith("permit not approved");
    await contract.approvePermit(permitId);
    await contract.recordZoneEntry(permitId, ethers.id("telemetry"));
    await expect(contract.connect(outsider).confirmHandoff(ethers.id("handoff-2"), permitId, ethers.id("robot-2"))).to.be.revertedWith("not handoff participant");
  });
});
