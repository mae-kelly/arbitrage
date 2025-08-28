require("@nomicfoundation/hardhat-toolbox");

module.exports = {
  solidity: "0.8.19",
  networks: {
    hardhat: {
      forking: {
        url: "https://eth-mainnet.g.alchemy.com/v2/alcht_oZ7wU7JpIoZejlOWUcMFOpNsIlLDsX"
      }
    }
  }
};
