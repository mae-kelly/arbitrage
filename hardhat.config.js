require("@nomicfoundation/hardhat-toolbox");
require("dotenv").config();

module.exports = {
  solidity: {
    version: "0.8.19",
    settings: {
      optimizer: {
        enabled: true,
        runs: 1000000
      }
    }
  },
  networks: {
    mainnet: {
      url: process.env.ETH_RPC_URL + process.env.ALCHEMY_KEY,
      accounts: [process.env.PRIVATE_KEY]
    },
    hardhat: {
      forking: {
        url: process.env.ETH_RPC_URL + process.env.ALCHEMY_KEY,
        blockNumber: 18500000
      }
    }
  }
};
