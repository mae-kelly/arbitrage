// contracts/FlashLoanArbitrage.sol

pragma solidity 0.8.10;

import "@aave/core-v3/contracts/flashloan/base/FlashLoanSimpleReceiverBase.sol";
import "@aave/core-v3/contracts/interfaces/IPoolAddressesProvider.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";

interface IUniswapV2Router {
    function swapExactTokensForTokens(
        uint amountIn,
        uint amountOutMin,
        address[] calldata path,
        address to,
        uint deadline
    ) external returns (uint[] memory amounts);
    
    function getAmountsOut(uint amountIn, address[] calldata path)
        external view returns (uint[] memory amounts);
}

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
    
    function exactInputSingle(ExactInputSingleParams calldata params)
        external payable returns (uint256 amountOut);
}

contract FlashLoanArbitrage is FlashLoanSimpleReceiverBase {
    address payable owner;
    uint256 public totalProfit;
    
    IUniswapV2Router constant uniswapV2Router = IUniswapV2Router(0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D);
    IUniswapV3Router constant uniswapV3Router = IUniswapV3Router(0xE592427A0AEce92De3Edee1F18E0157C05861564);
    
    event ProfitMade(uint256 profit);
    event ArbitrageFailed(string reason);
    
    modifier onlyOwner() {
        require(msg.sender == owner, "Not owner");
        _;
    }
    
    constructor(address _addressProvider) 
        FlashLoanSimpleReceiverBase(IPoolAddressesProvider(_addressProvider)) {
        owner = payable(msg.sender);
    }
    
    function executeOperation(
        address asset,
        uint256 amount,
        uint256 premium,
        address initiator,
        bytes calldata params
    ) external override returns (bool) {
        require(initiator == address(this), "Invalid initiator");
        
        (address targetDEX, uint256 minProfit, bytes memory strategyData) = 
            abi.decode(params, (address, uint256, bytes));
        
        uint256 initialBalance = IERC20(asset).balanceOf(address(this));
        
        bool success = executeArbitrageStrategy(asset, amount, targetDEX, strategyData);
        
        if (!success) {
            emit ArbitrageFailed("Strategy execution failed");
            return false;
        }
        
        uint256 finalBalance = IERC20(asset).balanceOf(address(this));
        uint256 amountOwed = amount + premium;
        
        require(finalBalance >= amountOwed, "Insufficient funds to repay");
        
        uint256 profit = finalBalance - amountOwed;
        require(profit >= minProfit, "Profit below minimum");
        
        totalProfit += profit;
        emit ProfitMade(profit);
        
        IERC20(asset).approve(address(POOL), amountOwed);
        
        if (profit > 0) {
            IERC20(asset).transfer(owner, profit);
        }
        
        return true;
    }
    
    function executeArbitrageStrategy(
        address asset,
        uint256 amount,
        address targetDEX,
        bytes memory strategyData
    ) internal returns (bool) {
        
        (string memory buyDEX, string memory sellDEX) = 
            abi.decode(strategyData, (string, string));
        
        if (keccak256(bytes(buyDEX)) == keccak256(bytes("uniswap_v2"))) {
            return executeUniswapV2Trade(asset, amount, targetDEX);
        } else if (keccak256(bytes(buyDEX)) == keccak256(bytes("uniswap_v3"))) {
            return executeUniswapV3Trade(asset, amount, targetDEX);
        }
        
        return false;
    }
    
    function executeUniswapV2Trade(
        address tokenIn,
        uint256 amountIn,
        address tokenOut
    ) internal returns (bool) {
        IERC20(tokenIn).approve(address(uniswapV2Router), amountIn);
        
        address[] memory path = new address[](2);
        path[0] = tokenIn;
        path[1] = tokenOut;
        
        try uniswapV2Router.swapExactTokensForTokens(
            amountIn,
            0,
            path,
            address(this),
            block.timestamp + 120
        ) {
            return true;
        } catch {
            return false;
        }
    }
    
    function executeUniswapV3Trade(
        address tokenIn,
        uint256 amountIn,
        address tokenOut
    ) internal returns (bool) {
        IERC20(tokenIn).approve(address(uniswapV3Router), amountIn);
        
        IUniswapV3Router.ExactInputSingleParams memory params = 
            IUniswapV3Router.ExactInputSingleParams({
                tokenIn: tokenIn,
                tokenOut: tokenOut,
                fee: 3000,
                recipient: address(this),
                deadline: block.timestamp + 120,
                amountIn: amountIn,
                amountOutMinimum: 0,
                sqrtPriceLimitX96: 0
            });
        
        try uniswapV3Router.exactInputSingle(params) {
            return true;
        } catch {
            return false;
        }
    }
    
    function requestFlashLoan(address token, uint256 amount, bytes memory params) public onlyOwner {
        POOL.flashLoanSimple(address(this), token, amount, params, 0);
    }
    
    function withdraw(address token) external onlyOwner {
        if (token == address(0)) {
            owner.transfer(address(this).balance);
        } else {
            IERC20(token).transfer(owner, IERC20(token).balanceOf(address(this)));
        }
    }
    
    function updateOwner(address payable newOwner) external onlyOwner {
        owner = newOwner;
    }
    
    receive() external payable {}
}