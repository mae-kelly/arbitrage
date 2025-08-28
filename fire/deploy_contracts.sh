#!/bin/bash
# deploy_contracts.sh

set -e

echo "======================================"
echo "    Smart Contract Deployment        "
echo "======================================"
echo ""

if [ ! -f ".env.testnet" ]; then
    echo "❌ .env.testnet not found. Please run setup_testnet.sh first"
    exit 1
fi

source .env.testnet

echo "Checking for required tools..."

if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed"
    echo "Installing Node.js..."
    curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
    sudo apt-get install -y nodejs
fi

echo "✅ Node.js found: $(node --version)"

if [ ! -d "node_modules" ]; then
    echo "Installing Hardhat and dependencies..."
    npm init -y
    npm install --save-dev hardhat @nomicfoundation/hardhat-toolbox @openzeppelin/contracts @aave/core-v3
fi

if [ ! -f "hardhat.config.js" ]; then
    echo "Creating Hardhat configuration..."
    cat > hardhat.config.js << EOF
require("@nomicfoundation/hardhat-toolbox");

const PRIVATE_KEY = process.env.PRIVATE_KEY || "";
const ALCHEMY_API_KEY = process.env.ALCHEMY_API_KEY || "";

module.exports = {
  solidity: {
    version: "0.8.10",
    settings: {
      optimizer: {
        enabled: true,
        runs: 200
      }
    }
  },
  networks: {
    sepolia: {
      url: \`https://eth-sepolia.g.alchemy.com/v2/\${ALCHEMY_API_KEY}\`,
      accounts: [PRIVATE_KEY],
      chainId: 11155111
    },
    "arbitrum-sepolia": {
      url: \`https://arb-sepolia.g.alchemy.com/v2/\${ALCHEMY_API_KEY}\`,
      accounts: [PRIVATE_KEY],
      chainId: 421614
    },
    "optimism-sepolia": {
      url: \`https://opt-sepolia.g.alchemy.com/v2/\${ALCHEMY_API_KEY}\`,
      accounts: [PRIVATE_KEY],
      chainId: 11155420
    },
    "base-sepolia": {
      url: \`https://base-sepolia.g.alchemy.com/v2/\${ALCHEMY_API_KEY}\`,
      accounts: [PRIVATE_KEY],
      chainId: 84532
    }
  }
};
EOF
fi

echo ""
echo "Creating deployment script..."

mkdir -p scripts

cat > scripts/deploy.js << 'EOF'
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
EOF

echo ""
echo "======================================"
echo "       Compiling Contracts            "
echo "======================================"
echo ""

npx hardhat compile

echo ""
echo "======================================"
echo "       Deploying to $NETWORK          "
echo "======================================"
echo ""

if [ -z "$PRIVATE_KEY" ]; then
    read -sp "Enter PRIVATE_KEY for deployment: " PRIVATE_KEY
    echo ""
    export PRIVATE_KEY
fi

npx hardhat run scripts/deploy.js --network $NETWORK

echo ""
echo "======================================"
echo "     Verifying Contracts (Optional)   "
echo "======================================"
echo ""

read -p "Do you want to verify contracts on Etherscan? (y/n): " VERIFY

if [ "$VERIFY" == "y" ]; then
    if [ -f "deployment_${NETWORK}.json" ]; then
        MULTICALL_ADDRESS=$(cat deployment_${NETWORK}.json | python3 -c "import sys, json; print(json.load(sys.stdin)['contracts']['Multicall3'])")
        FLASHLOAN_ADDRESS=$(cat deployment_${NETWORK}.json | python3 -c "import sys, json; print(json.load(sys.stdin)['contracts']['FlashLoanArbitrage'])")
        
        echo "Verifying Multicall3..."
        npx hardhat verify --network $NETWORK $MULTICALL_ADDRESS || true
        
        echo "Verifying FlashLoanArbitrage..."
        AAVE_PROVIDER=$(cat deployment_${NETWORK}.json | python3 -c "
import sys, json
network = json.load(sys.stdin)['network']
providers = {
    'sepolia': '0x012bAC54348C0E635dCAc9D5FB99f06F24136C9A',
    'arbitrum-sepolia': '0x302B8b596452d65fE816bC45F45331C93Bd09e30',
    'optimism-sepolia': '0x36616cf17557639614c1cdDb356b1B83fc0B2132',
    'base-sepolia': '0x36616cf17557639614c1cdDb356b1B83fc0B2132'
}
print(providers.get(network, providers['sepolia']))
")
        npx hardhat verify --network $NETWORK $FLASHLOAN_ADDRESS $AAVE_PROVIDER || true
    fi
fi

echo ""
echo "✅ Contract deployment complete!"
echo ""
echo "Next step: Run the bot with ./run_testnet.sh"