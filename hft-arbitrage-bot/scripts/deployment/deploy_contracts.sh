#!/bin/bash
# Deploy smart contracts to all networks

echo "🚀 Deploying arbitrage contracts..."

# Install dependencies
npm install --save-dev hardhat @nomiclabs/hardhat-ethers ethers @openzeppelin/contracts

# Deploy to Ethereum mainnet
echo "📜 Deploying to Ethereum mainnet..."
npx hardhat run scripts/deploy-arbitrage.js --network mainnet

# Deploy to Arbitrum
echo "📜 Deploying to Arbitrum..."
npx hardhat run scripts/deploy-arbitrage.js --network arbitrum

# Deploy to Optimism
echo "📜 Deploying to Optimism..."
npx hardhat run scripts/deploy-arbitrage.js --network optimism

echo "✅ All contracts deployed!"
