const { expect } = require("chai");

describe("SafetyLog", function () {
  async function deployed() {
    const [admin, gateway, stranger] = await ethers.getSigners();
    const Factory = await ethers.getContractFactory("SafetyLog");
    const contract = await Factory.deploy(admin.address);
    await contract.waitForDeployment();
    await contract.grantRole(await contract.GATEWAY_ROLE(), gateway.address);
    return { contract, gateway, stranger };
  }

  it("records a distance warning only from the gateway", async function () {
    const { contract, gateway, stranger } = await deployed();
    const warningId = ethers.encodeBytes32String("WARN-001");
    const logHash = ethers.keccak256(ethers.toUtf8Bytes("distance warning"));
    const deviceId = ethers.encodeBytes32String("ESP32-HRC-01");
    const sensorId = ethers.encodeBytes32String("HC-SR04");

    await expect(
      contract.connect(stranger).recordWarning(
        warningId,
        logHash,
        deviceId,
        sensorId,
        0
      )
    ).to.be.reverted;

    await expect(
      contract.connect(gateway).recordWarning(
        warningId,
        logHash,
        deviceId,
        sensorId,
        0
      )
    ).to.emit(contract, "WarningRecorded");

    expect(await contract.verifyLogHash(warningId, logHash)).to.equal(true);
  });

  it("rejects a duplicate warning ID", async function () {
    const { contract, gateway } = await deployed();
    const warningId = ethers.encodeBytes32String("WARN-001");
    const logHash = ethers.keccak256(ethers.toUtf8Bytes("sensor timeout"));
    const deviceId = ethers.encodeBytes32String("ESP32-HRC-01");
    const sensorId = ethers.encodeBytes32String("HC-SR04");

    await contract.connect(gateway).recordWarning(
      warningId,
      logHash,
      deviceId,
      sensorId,
      1
    );

    await expect(
      contract.connect(gateway).recordWarning(
        warningId,
        logHash,
        deviceId,
        sensorId,
        1
      )
    ).to.be.revertedWith("Warning already exists");
  });
});