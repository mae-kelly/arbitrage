const hre = require("hardhat");

async function main() {
  console.log("Deploying MEV Bot contracts...");
  
  const MegaExtractor = await hre.ethers.getContractFactory("MegaExtractor");
  const megaExtractor = await MegaExtractor.deploy();
  await megaExtractor.deployed();
  
  console.log("MegaExtractor deployed to:", megaExtractor.address);
  
  // Save address to .env
  const fs = require('fs');
  let env = fs.readFileSync('.env', 'utf8');
  env = env.replace(/CONTRACT_ADDRESS=.*/, `CONTRACT_ADDRESS=${megaExtractor.address}`);
  fs.writeFileSync('.env', env);
  
  console.log("✅ Contract address saved to .env");
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
