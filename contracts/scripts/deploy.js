const hre = require("hardhat");

async function main() {
  const [deployer] = await hre.ethers.getSigners();
  const factory = await hre.ethers.getContractFactory("HRCSafetyLog");
  const contract = await factory.deploy();
  await contract.waitForDeployment();

  const permitFactory = await hre.ethers.getContractFactory("WorkPermitHandoff");
  const permitContract = await permitFactory.deploy();
  await permitContract.waitForDeployment();

  const legacyFactory = await hre.ethers.getContractFactory("SafetyLog");
  const legacyContract = await legacyFactory.deploy(deployer.address);
  await legacyContract.waitForDeployment();

  console.log(`deployer=${deployer.address}`);
  console.log(`contract=${await contract.getAddress()}`);
  console.log(`permitContract=${await permitContract.getAddress()}`);
  console.log(`legacySafetyLog=${await legacyContract.getAddress()}`);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
