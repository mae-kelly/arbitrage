#!/bin/bash
echo "🚀 Deploying production contracts..."
cd crypto-arb-bot
npx hardhat compile
npx hardhat run scripts/deploy.ts --network mainnet
npx hardhat verify --network mainnet CONTRACT_ADDRESS
