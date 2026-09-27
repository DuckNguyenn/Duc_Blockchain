const hre = require("hardhat");

async function main() {
  const [deployer] = await hre.ethers.getSigners();
  const factory = await hre.ethers.getContractFactory("HRCSafetyLog");
  const contract = await factory.deploy();
  await contract.waitForDeployment();

  console.log(`deployer=${deployer.address}`);
  console.log(`contract=${await contract.getAddress()}`);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
