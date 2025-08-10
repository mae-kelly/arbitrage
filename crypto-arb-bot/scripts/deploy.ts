import { ethers } from "hardhat";
import * as dotenv from "dotenv";

dotenv.config();

async function main() {
    const [deployer] = await ethers.getSigners();
    console.log("Deploying contracts with:", deployer.address);
    
    const FlashLoanArbitrage = await ethers.getContractFactory("FlashLoanArbitrage");
    const flashLoan = await FlashLoanArbitrage.deploy();
    await flashLoan.deployed();
    console.log("FlashLoanArbitrage deployed to:", flashLoan.address);
    
    const CrossChainArbitrage = await ethers.getContractFactory("CrossChainArbitrage");
    const crossChain = await CrossChainArbitrage.deploy();
    await crossChain.deployed();
    console.log("CrossChainArbitrage deployed to:", crossChain.address);
}

main()
    .then(() => process.exit(0))
    .catch((error) => {
        console.error(error);
        process.exit(1);
    });
