require("@nomicfoundation/hardhat-toolbox");

module.exports = {
  solidity: "0.8.24",
  paths: {
    // Keep the project sources isolated from node_modules. With `.` Hardhat
    // also discovers fixture contracts shipped by dependencies (HH1006).
    sources: "./contracts",
    tests: "test",
    cache: "cache",
    artifacts: "artifacts"
  },
  networks: {
    hardhat: {},
    localhost: { url: "http://127.0.0.1:8545" }
  }
};
