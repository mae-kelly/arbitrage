pragma solidity ^0.8.19;

import "@openzeppelin/contracts/security/ReentrancyGuard.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";

interface IFlashLoanReceiver {
    function executeOperation(
        address[] calldata assets,
        uint256[] calldata amounts,
        uint256[] calldata premiums,
        address initiator,
        bytes calldata params
    ) external returns (bool);
}

interface IAaveLendingPool {
    function flashLoan(
        address receiverAddress,
        address[] calldata assets,
        uint256[] calldata amounts,
        uint256[] calldata modes,
        address onBehalfOf,
        bytes calldata params,
        uint16 referralCode
    ) external;
}

interface IDEXRouter {
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

contract ArbitrageBot is IFlashLoanReceiver, ReentrancyGuard, Ownable {
    
    struct ArbitrageParams {
        address tokenA;
        address tokenB;
        address dexRouter1;
        address dexRouter2;
        uint256 amountIn;
        uint256 minProfit;
        bool isReverse;
    }
    
    IAaveLendingPool public constant LENDING_POOL = IAaveLendingPool(0x7d2768dE32b0b80b7a3454c06BdAc94A69DDc7A9);
    
    mapping(address => bool) public authorizedCallers;
    mapping(address => bool) public supportedTokens;
    mapping(address => bool) public supportedDEXs;
    
    uint256 public constant MAX_SLIPPAGE = 300;
    uint256 public constant SLIPPAGE_BASE = 10000;
    uint256 public minProfitThreshold = 1e16;
    uint256 public maxFlashLoanAmount = 1000 * 1e18;
    
    event ArbitrageExecuted(
        address indexed tokenA,
        address indexed tokenB,
        uint256 amountIn,
        uint256 profit,
        address dex1,
        address dex2
    );
    
    event FlashLoanInitiated(
        address indexed asset,
        uint256 amount,
        address indexed initiator
    );
    
    modifier onlyAuthorized() {
        require(authorizedCallers[msg.sender] || msg.sender == owner(), "Not authorized");
        _;
    }
    
    constructor() {
        authorizedCallers[msg.sender] = true;
    }
    
    function addAuthorizedCaller(address caller) external onlyOwner {
        authorizedCallers[caller] = true;
    }
    
    function removeAuthorizedCaller(address caller) external onlyOwner {
        authorizedCallers[caller] = false;
    }
    
    function addSupportedToken(address token) external onlyOwner {
        supportedTokens[token] = true;
    }
    
    function addSupportedDEX(address dex) external onlyOwner {
        supportedDEXs[dex] = true;
    }
    
    function setMinProfitThreshold(uint256 threshold) external onlyOwner {
        minProfitThreshold = threshold;
    }
    
    function setMaxFlashLoanAmount(uint256 amount) external onlyOwner {
        maxFlashLoanAmount = amount;
    }
    
    function executeArbitrage(ArbitrageParams calldata params) external onlyAuthorized nonReentrant {
        require(supportedTokens[params.tokenA], "Token A not supported");
        require(supportedTokens[params.tokenB], "Token B not supported");
        require(supportedDEXs[params.dexRouter1], "DEX 1 not supported");
        require(supportedDEXs[params.dexRouter2], "DEX 2 not supported");
        require(params.amountIn <= maxFlashLoanAmount, "Amount exceeds max flash loan");
        
        if (isProfitable(params)) {
            address[] memory assets = new address[](1);
            uint256[] memory amounts = new uint256[](1);
            uint256[] memory modes = new uint256[](1);
            
            assets[0] = params.tokenA;
            amounts[0] = params.amountIn;
            modes[0] = 0;
            
            bytes memory encodedParams = abi.encode(params);
            
            emit FlashLoanInitiated(params.tokenA, params.amountIn, msg.sender);
            
            LENDING_POOL.flashLoan(
                address(this),
                assets,
                amounts,
                modes,
                address(this),
                encodedParams,
                0
            );
        }
    }
    
    function executeOperation(
        address[] calldata assets,
        uint256[] calldata amounts,
        uint256[] calldata premiums,
        address initiator,
        bytes calldata params
    ) external override returns (bool) {
        require(msg.sender == address(LENDING_POOL), "Caller not lending pool");
        require(initiator == address(this), "Initiator not this contract");
        
        ArbitrageParams memory arbParams = abi.decode(params, (ArbitrageParams));
        
        uint256 amountOwing = amounts[0] + premiums[0];
        uint256 profit = performArbitrage(arbParams, amounts[0]);
        
        require(profit >= arbParams.minProfit, "Insufficient profit");
        
        IERC20(assets[0]).approve(address(LENDING_POOL), amountOwing);
        
        emit ArbitrageExecuted(
            arbParams.tokenA,
            arbParams.tokenB,
            amounts[0],
            profit,
            arbParams.dexRouter1,
            arbParams.dexRouter2
        );
        
        return true;
    }
    
    function performArbitrage(ArbitrageParams memory params, uint256 flashAmount) internal returns (uint256) {
        uint256 balanceBefore = IERC20(params.tokenA).balanceOf(address(this));
        
        IERC20(params.tokenA).approve(params.dexRouter1, flashAmount);
        
        address[] memory path1 = new address[](2);
        if (!params.isReverse) {
            path1[0] = params.tokenA;
            path1[1] = params.tokenB;
        } else {
            path1[0] = params.tokenB;
            path1[1] = params.tokenA;
        }
        
        uint256[] memory amounts1 = IDEXRouter(params.dexRouter1).swapExactTokensForTokens(
            flashAmount,
            0,
            path1,
            address(this),
            block.timestamp + 300
        );
        
        uint256 intermediateAmount = amounts1[amounts1.length - 1];
        
        address intermediateToken = params.isReverse ? params.tokenA : params.tokenB;
        IERC20(intermediateToken).approve(params.dexRouter2, intermediateAmount);
        
        address[] memory path2 = new address[](2);
        if (!params.isReverse) {
            path2[0] = params.tokenB;
            path2[1] = params.tokenA;
        } else {
            path2[0] = params.tokenA;
            path2[1] = params.tokenB;
        }
        
        uint256[] memory amounts2 = IDEXRouter(params.dexRouter2).swapExactTokensForTokens(
            intermediateAmount,
            0,
            path2,
            address(this),
            block.timestamp + 300
        );
        
        uint256 finalAmount = amounts2[amounts2.length - 1];
        uint256 balanceAfter = IERC20(params.tokenA).balanceOf(address(this));
        
        require(balanceAfter > balanceBefore, "Arbitrage resulted in loss");
        
        return balanceAfter - balanceBefore;
    }
    
    function isProfitable(ArbitrageParams calldata params) public view returns (bool) {
        try this.calculateProfit(params) returns (uint256 profit) {
            return profit >= minProfitThreshold;
        } catch {
            return false;
        }
    }
    
    function calculateProfit(ArbitrageParams calldata params) external view returns (uint256) {
        address[] memory path1 = new address[](2);
        address[] memory path2 = new address[](2);
        
        if (!params.isReverse) {
            path1[0] = params.tokenA;
            path1[1] = params.tokenB;
            path2[0] = params.tokenB;
            path2[1] = params.tokenA;
        } else {
            path1[0] = params.tokenB;
            path1[1] = params.tokenA;
            path2[0] = params.tokenA;
            path2[1] = params.tokenB;
        }
        
        uint256[] memory amounts1 = IDEXRouter(params.dexRouter1).getAmountsOut(params.amountIn, path1);
        uint256 intermediateAmount = amounts1[amounts1.length - 1];
        
        uint256[] memory amounts2 = IDEXRouter(params.dexRouter2).getAmountsOut(intermediateAmount, path2);
        uint256 finalAmount = amounts2[amounts2.length - 1];
        
        if (finalAmount > params.amountIn) {
            return finalAmount - params.amountIn;
        } else {
            return 0;
        }
    }
    
    function estimateGasCost() public view returns (uint256) {
        return tx.gasprice * 400000;
    }
    
    function withdrawToken(address token, uint256 amount) external onlyOwner {
        require(IERC20(token).transfer(owner(), amount), "Transfer failed");
    }
    
    function withdrawETH(uint256 amount) external onlyOwner {
        payable(owner()).transfer(amount);
    }
    
    function emergencyStop() external onlyOwner {
        selfdestruct(payable(owner()));
    }
    
    function getContractBalance(address token) external view returns (uint256) {
        return IERC20(token).balanceOf(address(this));
    }
    
    function batchArbitrage(ArbitrageParams[] calldata paramsList) external onlyAuthorized {
        for (uint i = 0; i < paramsList.length; i++) {
            if (isProfitable(paramsList[i])) {
                this.executeArbitrage(paramsList[i]);
            }
        }
    }
    
    receive() external payable {}
    
    fallback() external payable {}
}
