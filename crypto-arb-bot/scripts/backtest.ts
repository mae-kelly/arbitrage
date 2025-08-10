import { ethers } from "ethers";
import axios from "axios";
import * as fs from "fs";

interface BacktestResult {
    totalTrades: number;
    profitableTrades: number;
    totalProfit: ethers.BigNumber;
    totalGasCost: ethers.BigNumber;
    netProfit: ethers.BigNumber;
    winRate: number;
}

class Backtester {
    private provider: ethers.providers.JsonRpcProvider;
    private results: BacktestResult;
    
    constructor() {
        this.provider = new ethers.providers.JsonRpcProvider(process.env.ETHEREUM_RPC_URL);
        this.results = {
            totalTrades: 0,
            profitableTrades: 0,
            totalProfit: ethers.BigNumber.from(0),
            totalGasCost: ethers.BigNumber.from(0),
            netProfit: ethers.BigNumber.from(0),
            winRate: 0
        };
    }
    
    async fetchHistoricalData(startBlock: number, endBlock: number) {
        const query = `
        {
            swaps(
                first: 1000,
                where: { blockNumber_gte: ${startBlock}, blockNumber_lte: ${endBlock} }
                orderBy: blockNumber
            ) {
                id
                token0 { symbol }
                token1 { symbol }
                amount0In
                amount1In
                amount0Out
                amount1Out
                blockNumber
                timestamp
            }
        }`;
        
        const response = await axios.post(
            "https://api.thegraph.com/subgraphs/name/uniswap/uniswap-v3",
            { query }
        );
        
        return response.data.data.swaps;
    }
    
    async simulateTrade(swap: any) {
        const gasPrice = ethers.utils.parseUnits("30", "gwei");
        const gasLimit = 300000;
        const gasCost = gasPrice.mul(gasLimit);
        
        const amount0 = ethers.BigNumber.from(swap.amount0In || 0);
        const amount1 = ethers.BigNumber.from(swap.amount1Out || 0);
        
        const spread = amount1.sub(amount0).mul(100).div(amount0);
        
        if (spread.gt(30)) {
            const profit = amount1.sub(amount0);
            const netProfit = profit.sub(gasCost);
            
            this.results.totalTrades++;
            
            if (netProfit.gt(0)) {
                this.results.profitableTrades++;
                this.results.totalProfit = this.results.totalProfit.add(profit);
            }
            
            this.results.totalGasCost = this.results.totalGasCost.add(gasCost);
        }
    }
    
    async runBacktest(blocks: number = 1000) {
        const latestBlock = await this.provider.getBlockNumber();
        const startBlock = latestBlock - blocks;
        
        console.log(`Running backtest from block ${startBlock} to ${latestBlock}`);
        
        const swaps = await this.fetchHistoricalData(startBlock, latestBlock);
        
        for (const swap of swaps) {
            await this.simulateTrade(swap);
        }
        
        this.results.netProfit = this.results.totalProfit.sub(this.results.totalGasCost);
        this.results.winRate = this.results.totalTrades > 0 
            ? (this.results.profitableTrades / this.results.totalTrades) * 100 
            : 0;
        
        this.printResults();
        this.saveResults();
    }
    
    printResults() {
        console.log("\n=== Backtest Results ===");
        console.log(`Total Trades: ${this.results.totalTrades}`);
        console.log(`Profitable Trades: ${this.results.profitableTrades}`);
        console.log(`Win Rate: ${this.results.winRate.toFixed(2)}%`);
        console.log(`Total Profit: ${ethers.utils.formatEther(this.results.totalProfit)} ETH`);
        console.log(`Total Gas Cost: ${ethers.utils.formatEther(this.results.totalGasCost)} ETH`);
        console.log(`Net Profit: ${ethers.utils.formatEther(this.results.netProfit)} ETH`);
    }
    
    saveResults() {
        const timestamp = new Date().toISOString();
        const filename = `backtest_${timestamp}.json`;
        
        fs.writeFileSync(
            filename,
            JSON.stringify({
                timestamp,
                results: {
                    ...this.results,
                    totalProfit: this.results.totalProfit.toString(),
                    totalGasCost: this.results.totalGasCost.toString(),
                    netProfit: this.results.netProfit.toString()
                }
            }, null, 2)
        );
        
        console.log(`\nResults saved to ${filename}`);
    }
}

const backtester = new Backtester();
backtester.runBacktest(10000).catch(console.error);
