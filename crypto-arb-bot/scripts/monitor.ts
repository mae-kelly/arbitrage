import { ethers } from "ethers";
import { FlashbotsBundle, FlashbotsBundleProvider } from "@flashbots/ethers-provider-bundle";
import WebSocket from "ws";
import axios from "axios";

interface Opportunity {
    dexA: string;
    dexB: string;
    tokenA: string;
    tokenB: string;
    spread: number;
    estimatedProfit: ethers.BigNumber;
    gasEstimate: number;
}

class ArbitrageMonitor {
    private provider: ethers.providers.WebSocketProvider;
    private flashbotsProvider: FlashbotsBundleProvider;
    private wallet: ethers.Wallet;
    private opportunities: Map<string, Opportunity>;
    private wsConnections: Map<string, WebSocket>;
    
    constructor() {
        this.provider = new ethers.providers.WebSocketProvider(process.env.ETHEREUM_RPC_URL!);
        this.wallet = new ethers.Wallet(process.env.PRIVATE_KEY!, this.provider);
        this.opportunities = new Map();
        this.wsConnections = new Map();
        
        this.initializeFlashbots();
        this.connectToDEXs();
    }
    
    async initializeFlashbots() {
        this.flashbotsProvider = await FlashbotsBundleProvider.create(
            this.provider,
            this.wallet,
            process.env.FLASHBOTS_RELAY_URL
        );
    }
    
    connectToDEXs() {
        const uniswapWS = new WebSocket("wss://api.thegraph.com/subgraphs/name/uniswap/uniswap-v3");
        const sushiWS = new WebSocket("wss://api.thegraph.com/subgraphs/name/sushiswap/exchange");
        
        this.wsConnections.set("uniswap", uniswapWS);
        this.wsConnections.set("sushi", sushiWS);
        
        uniswapWS.on("message", (data) => this.handleUniswapData(data));
        sushiWS.on("message", (data) => this.handleSushiData(data));
    }
    
    async handleUniswapData(data: WebSocket.Data) {
        const parsed = JSON.parse(data.toString());
        await this.checkArbitrage("uniswap", parsed);
    }
    
    async handleSushiData(data: WebSocket.Data) {
        const parsed = JSON.parse(data.toString());
        await this.checkArbitrage("sushi", parsed);
    }
    
    async checkArbitrage(dex: string, poolData: any) {
        const uniswapV3Router = "0x68b3465833fb72A70ecDF485E0e4C7bD8665Fc45";
        const sushiRouter = "0xd9e1cE17f2641f24aE83637ab66a2cca9C378B9F";
        
        try {
            const quoterContract = new ethers.Contract(
                "0xb27308f9F90D607463bb33eA1BeBb41C27CE5AB6",
                ["function quoteExactInputSingle(tuple(address,address,uint256,uint24,uint160)) returns (uint256)"],
                this.provider
            );
            
            const amountIn = ethers.utils.parseEther("1");
            const quote = await quoterContract.quoteExactInputSingle({
                tokenIn: poolData.token0,
                tokenOut: poolData.token1,
                amountIn: amountIn,
                fee: 3000,
                sqrtPriceLimitX96: 0
            });
            
            const spread = this.calculateSpread(quote, poolData.expectedOut);
            
            if (spread > 0.003) {
                const opportunity: Opportunity = {
                    dexA: dex,
                    dexB: "other",
                    tokenA: poolData.token0,
                    tokenB: poolData.token1,
                    spread: spread,
                    estimatedProfit: this.calculateProfit(amountIn, spread),
                    gasEstimate: 300000
                };
                
                this.opportunities.set(`${dex}-${poolData.id}`, opportunity);
                await this.executeIfProfitable(opportunity);
            }
        } catch (error) {
            console.error("Error checking arbitrage:", error);
        }
    }
    
    calculateSpread(priceA: ethers.BigNumber, priceB: ethers.BigNumber): number {
        const diff = priceA.sub(priceB).abs();
        return diff.mul(10000).div(priceA).toNumber() / 10000;
    }
    
    calculateProfit(amount: ethers.BigNumber, spread: number): ethers.BigNumber {
        return amount.mul(Math.floor(spread * 10000)).div(10000);
    }
    
    async executeIfProfitable(opp: Opportunity) {
        const gasPrice = await this.provider.getGasPrice();
        const gasCost = gasPrice.mul(opp.gasEstimate);
        
        if (opp.estimatedProfit.gt(gasCost.mul(2))) {
            console.log(`Executing arbitrage: ${opp.dexA} -> ${opp.dexB}, profit: ${ethers.utils.formatEther(opp.estimatedProfit)}`);
            await this.executeFlashbotBundle(opp);
        }
    }
    
    async executeFlashbotBundle(opp: Opportunity) {
        const flashLoanContract = "0x7d2768dE32b0b80b7a3454c06BdAc94A69DDc7A9";
        
        const tx = {
            to: flashLoanContract,
            data: this.encodeArbitrageCall(opp),
            gasLimit: opp.gasEstimate,
            maxFeePerGas: ethers.utils.parseUnits("50", "gwei"),
            maxPriorityFeePerGas: ethers.utils.parseUnits("3", "gwei"),
            chainId: 1,
            nonce: await this.wallet.getTransactionCount()
        };
        
        const signedTx = await this.wallet.signTransaction(tx);
        const blockNumber = await this.provider.getBlockNumber();
        
        const bundle: FlashbotsBundle = [
            { signedTransaction: signedTx }
        ];
        
        const bundleSubmission = await this.flashbotsProvider.sendBundle(bundle, blockNumber + 1);
        
        if ("error" in bundleSubmission) {
            console.error("Bundle submission failed:", bundleSubmission.error);
        } else {
            const waitResponse = await bundleSubmission.wait();
            console.log("Bundle status:", waitResponse);
        }
    }
    
    encodeArbitrageCall(opp: Opportunity): string {
        const iface = new ethers.utils.Interface([
            "function initiateArbitrage(tuple(address,address,uint256,address[],bytes,uint256))"
        ]);
        
        return iface.encodeFunctionData("initiateArbitrage", [{
            tokenA: opp.tokenA,
            tokenB: opp.tokenB,
            amountA: ethers.utils.parseEther("100"),
            routers: [opp.dexA, opp.dexB],
            routerCalldata: "0x",
            expectedProfit: opp.estimatedProfit
        }]);
    }
    
    async run() {
        console.log("Arbitrage monitor started");
        
        this.provider.on("block", async (blockNumber) => {
            console.log(`New block: ${blockNumber}`);
            
            for (const [id, opp] of this.opportunities) {
                await this.executeIfProfitable(opp);
            }
            
            this.opportunities.clear();
        });
        
        setInterval(() => {
            console.log(`Active opportunities: ${this.opportunities.size}`);
        }, 10000);
    }
}

const monitor = new ArbitrageMonitor();
monitor.run().catch(console.error);
