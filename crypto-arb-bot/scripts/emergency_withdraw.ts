import { ethers } from "hardhat";

async function emergencyWithdraw() {
    const [deployer] = await ethers.getSigners();
    const safeWallet = process.env.SAFE_WALLET_ADDRESS;
    
    if (!safeWallet) {
        throw new Error("SAFE_WALLET_ADDRESS not set in .env");
    }
    
    console.log("Withdrawing all funds to:", safeWallet);
    
    const flashLoanContract = await ethers.getContractAt(
        "ProductionFlashLoan", 
        process.env.FLASH_LOAN_CONTRACT_ADDRESS!
    );
    
    const tokens = [
        "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48", // USDC
        "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2", // WETH
        "0x6B175474E89094C44Da98b954EedeAC495271d0F"  // DAI
    ];
    
    for (const token of tokens) {
        const tokenContract = await ethers.getContractAt("IERC20", token);
        const balance = await tokenContract.balanceOf(flashLoanContract.address);
        
        if (balance.gt(0)) {
            console.log(`Withdrawing ${ethers.utils.formatUnits(balance, 18)} tokens from ${token}`);
            await flashLoanContract.withdrawToken(token, safeWallet, balance);
        }
    }
    
    const ethBalance = await ethers.provider.getBalance(flashLoanContract.address);
    if (ethBalance.gt(0)) {
        console.log(`Withdrawing ${ethers.utils.formatEther(ethBalance)} ETH`);
        await flashLoanContract.withdrawETH(safeWallet, ethBalance);
    }
    
    console.log("✅ Emergency withdrawal completed");
}

emergencyWithdraw().catch(console.error);
