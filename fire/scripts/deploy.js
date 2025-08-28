const hre = require("hardhat");
const fs = require("fs");

async function main() {
  const [deployer] = await hre.ethers.getSigners();
  
  console.log("Deploying contracts with account:", deployer.address);
  console.log("Account balance:", (await deployer.getBalance()).toString());
  
  // Testnet Aave Pool Addresses Provider
  const TESTNET_POOL_ADDRESSES = {
    "sepolia": "0x012bAC54348C0E635dCAc9D5FB99f06F24136C9A",
    "arbitrum-sepolia": "0x302B8b596452d65fE816bC45F45331C93Bd09e30",
    "optimism-sepolia": "0x36616cf17557639614c1cdDb356b1B83fc0B2132",
    "base-sepolia": "0x36616cf17557639614c1cdDb356b1B83fc0B2132"
  };
  
  const network = hre.network.name;
  const poolAddressesProvider = TESTNET_POOL_ADDRESSES[network] || TESTNET_POOL_ADDRESSES["sepolia"];
  
  console.log("\nDeploying Multicall3...");
  const Multicall3 = await hre.ethers.getContractFactory("Multicall3");
  const multicall = await Multicall3.deploy();
  await multicall.deployed();
  console.log("Multicall3 deployed to:", multicall.address);
  
  console.log("\nDeploying FlashLoanArbitrage...");
  const FlashLoanArbitrage = await hre.ethers.getContractFactory("FlashLoanArbitrage");
  const flashloan = await FlashLoanArbitrage.deploy(poolAddressesProvider);
  await flashloan.deployed();
  console.log("FlashLoanArbitrage deployed to:", flashloan.address);
  
  const deploymentData = {
    network: network,
    deployer: deployer.address,
    timestamp: new Date().toISOString(),
    contracts: {
      Multicall3: multicall.address,
      FlashLoanArbitrage: flashloan.address
    }
  };
  
  fs.writeFileSync(
    `deployment_${network}.json`,
    JSON.stringify(deploymentData, null, 2)
  );
  
  console.log("\n✅ Deployment complete!");
  console.log("Deployment data saved to:", `deployment_${network}.json`);
  
  return deploymentData;
}

main()
  .then((data) => {
    console.log("\nUpdating .env.testnet with contract addresses...");
    const envContent = fs.readFileSync(".env.testnet", "utf8");
    const updatedEnv = envContent
      .replace(/FLASHLOAN_CONTRACT_ADDRESS=.*/, `FLASHLOAN_CONTRACT_ADDRESS=${data.contracts.FlashLoanArbitrage}`)
      .replace(/MULTICALL_CONTRACT_ADDRESS=.*/, `MULTICALL_CONTRACT_ADDRESS=${data.contracts.Multicall3}`);
    fs.writeFileSync(".env.testnet", updatedEnv);
    console.log("✅ .env.testnet updated");
    process.exit(0);
  })
  .catch((error) => {
    console.error(error);
    process.exit(1);
  });
