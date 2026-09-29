const hre = require("hardhat");

async function main() {
  const [deployer] = await hre.ethers.getSigners();
  const factory = await hre.ethers.getContractFactory("HRCSafetyLog");
  const contract = await factory.deploy();
  await contract.waitForDeployment();

  const permitFactory = await hre.ethers.getContractFactory("WorkPermitHandoff");
  const permitContract = await permitFactory.deploy();
  await permitContract.waitForDeployment();

  console.log(`deployer=${deployer.address}`);
  console.log(`contract=${await contract.getAddress()}`);
  console.log(`permitContract=${await permitContract.getAddress()}`);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
