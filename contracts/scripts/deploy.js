const hre = require("hardhat");

async function main() {
  const [admin] = await hre.ethers.getSigners();
  const Factory = await hre.ethers.getContractFactory("SafetyLog");
  const contract = await Factory.deploy(admin.address);
  await contract.waitForDeployment();

  console.log(`admin=${admin.address}`);
  console.log(`contract=${await contract.getAddress()}`);
  console.log("Grant GATEWAY_ROLE to the optional warning-log gateway after deployment.");
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});