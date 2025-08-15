// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "@openzeppelin/contracts/security/ReentrancyGuard.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@aave/core-v3/contracts/interfaces/IPoolAddressesProvider.sol";
import "@aave/core-v3/contracts/interfaces/IPool.sol";
import "@aave/core-v3/contracts/flashloan/base/FlashLoanSimpleReceiverBase.sol";

interface IUniswapV3Router {
    struct ExactInputSingleParams {
        address tokenIn;
        address tokenOut;
        uint24 fee;
        address recipient;
        uint256 deadline;
        uint256 amountIn;
        uint256 amountOutMinimum;
        uint160 sqrtPriceLimitX96;
    }
    
    function exactInputSingle(ExactInputSingleParams calldata params) external payable returns (uint256 amountOut);
}

contract ArbitrageContract is FlashLoanSimpleReceiverBase, ReentrancyGuard, Ownable {
    IUniswapV3Router public constant uniswapRouter = IUniswapV3Router(0xE592427A0AEce92De3Edee1F18E0157C05861564);
    
    struct ArbitrageParams {
        address tokenIn;
        address tokenOut;
        uint24 fee1;
        uint24 fee2;
        uint256 amountIn;
        bool direction; // true: Uniswap -> Sushiswap, false: Sushiswap -> Uniswap
    }
    
    event ArbitrageExecuted(
        address indexed tokenIn,
        address indexed tokenOut,
        uint256 amountIn,
        uint256 profit,
        address indexed executor
    );
    
    event FlashLoanExecuted(
        address indexed asset,
        uint256 amount,
        uint256 premium,
        bool success
    );
    
    constructor(IPoolAddressesProvider _addressProvider) 
        FlashLoanSimpleReceiverBase(_addressProvider) {}
    
    function executeFlashLoanArbitrage(
        address asset,
        uint256 amount,
        ArbitrageParams calldata params
    ) external nonReentrant {
        require(amount > 0, "Amount must be greater than 0");
        require(asset == params.tokenIn, "Asset mismatch");
        
        bytes memory paramsData = abi.encode(params, msg.sender);
        
        IPool(POOL).flashLoanSimple(
            address(this),
            asset,
            amount,
            paramsData,
            0 // referral code
        );
    }
    
    function executeSimpleFlashLoan(address asset, uint256 amount) external {
        IPool(POOL).flashLoanSimple(address(this), asset, amount, "", 0);
    }
    
    function executeOperation(
        address asset,
        uint256 amount,
        uint256 premium,
        address initiator,
        bytes calldata params
    ) external override returns (bool) {
        require(msg.sender == address(POOL), "Only pool can call");
        require(initiator == address(this), "Only this contract can initiate");
        
        if (params.length > 0) {
            (ArbitrageParams memory arbParams, address originalCaller) = abi.decode(params, (ArbitrageParams, address));
            
            // Execute arbitrage logic
            uint256 profit = _executeArbitrageLogic(arbParams, amount);
            
            emit ArbitrageExecuted(
                arbParams.tokenIn,
                arbParams.tokenOut,
                amount,
                profit,
                originalCaller
            );
        }
        
        // Approve the pool to pull the owed amount
        uint256 amountOwed = amount + premium;
        IERC20(asset).approve(address(POOL), amountOwed);
        
        emit FlashLoanExecuted(asset, amount, premium, true);
        
        return true;
    }
    
    function _executeArbitrageLogic(ArbitrageParams memory params, uint256 amount) internal returns (uint256) {
        // Step 1: Swap on first DEX (Uniswap)
        IERC20(params.tokenIn).approve(address(uniswapRouter), amount);
        
        IUniswapV3Router.ExactInputSingleParams memory swapParams = IUniswapV3Router.ExactInputSingleParams({
            tokenIn: params.tokenIn,
            tokenOut: params.tokenOut,
            fee: params.fee1,
            recipient: address(this),
            deadline: block.timestamp + 300,
            amountIn: amount,
            amountOutMinimum: 0,
            sqrtPriceLimitX96: 0
        });
        
        uint256 amountOut1 = uniswapRouter.exactInputSingle(swapParams);
        
        // Step 2: Swap back on second DEX (could be another Uniswap pool or different DEX)
        IERC20(params.tokenOut).approve(address(uniswapRouter), amountOut1);
        
        swapParams = IUniswapV3Router.ExactInputSingleParams({
            tokenIn: params.tokenOut,
            tokenOut: params.tokenIn,
            fee: params.fee2,
            recipient: address(this),
            deadline: block.timestamp + 300,
            amountIn: amountOut1,
            amountOutMinimum: amount, // Must get back at least the original amount
            sqrtPriceLimitX96: 0
        });
        
        uint256 amountOut2 = uniswapRouter.exactInputSingle(swapParams);
        
        // Calculate profit
        require(amountOut2 > amount, "Arbitrage not profitable");
        uint256 profit = amountOut2 - amount;
        
        return profit;
    }
    
    function withdrawToken(address token) external onlyOwner {
        IERC20(token).transfer(owner(), IERC20(token).balanceOf(address(this)));
    }
    
    function withdrawETH() external onlyOwner {
        payable(owner()).transfer(address(this).balance);
    }
    
    receive() external payable {}
}
