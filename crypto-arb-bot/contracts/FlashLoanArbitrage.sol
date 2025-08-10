pragma solidity ^0.8.19;

interface IERC20 {
    function transfer(address to, uint256 amount) external returns (bool);
    function approve(address spender, uint256 amount) external returns (bool);
    function balanceOf(address account) external view returns (uint256);
}

interface IFlashLoanReceiver {
    function executeOperation(
        address[] calldata assets,
        uint256[] calldata amounts,
        uint256[] calldata premiums,
        address initiator,
        bytes calldata params
    ) external returns (bool);
}

interface ILendingPool {
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

interface IUniswapV2Router {
    function swapExactTokensForTokens(
        uint amountIn,
        uint amountOutMin,
        address[] calldata path,
        address to,
        uint deadline
    ) external returns (uint[] memory amounts);
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
    function exactInputSingle(ExactInputSingleParams calldata params) external payable returns (uint256 amountOut);
}

contract FlashLoanArbitrage is IFlashLoanReceiver {
    ILendingPool constant lendingPool = ILendingPool(0x7d2768dE32b0b80b7a3454c06BdAc94A69DDc7A9);
    address immutable owner;
    
    struct ArbitrageParams {
        address tokenA;
        address tokenB;
        uint256 amountA;
        address[] routers;
        bytes routerCalldata;
        uint256 expectedProfit;
    }
    
    modifier onlyOwner() {
        require(msg.sender == owner, "Not owner");
        _;
    }
    
    constructor() {
        owner = msg.sender;
    }
    
    function initiateArbitrage(ArbitrageParams calldata params) external onlyOwner {
        address[] memory assets = new address[](1);
        assets[0] = params.tokenA;
        
        uint256[] memory amounts = new uint256[](1);
        amounts[0] = params.amountA;
        
        uint256[] memory modes = new uint256[](1);
        modes[0] = 0;
        
        lendingPool.flashLoan(
            address(this),
            assets,
            amounts,
            modes,
            address(this),
            abi.encode(params),
            0
        );
    }
    
    function executeOperation(
        address[] calldata assets,
        uint256[] calldata amounts,
        uint256[] calldata premiums,
        address initiator,
        bytes calldata params
    ) external override returns (bool) {
        require(msg.sender == address(lendingPool), "Invalid caller");
        require(initiator == address(this), "Invalid initiator");
        
        ArbitrageParams memory arbParams = abi.decode(params, (ArbitrageParams));
        
        uint256 amountOwed = amounts[0] + premiums[0];
        
        IERC20(arbParams.tokenA).approve(arbParams.routers[0], amounts[0]);
        
        (bool success,) = arbParams.routers[0].call(arbParams.routerCalldata);
        require(success, "Router execution failed");
        
        uint256 profit = IERC20(arbParams.tokenA).balanceOf(address(this)) - amountOwed;
        require(profit >= arbParams.expectedProfit * 95 / 100, "Insufficient profit");
        
        IERC20(arbParams.tokenA).approve(address(lendingPool), amountOwed);
        
        return true;
    }
    
    function withdraw(address token) external onlyOwner {
        uint256 balance = IERC20(token).balanceOf(address(this));
        require(balance > 0, "No balance");
        IERC20(token).transfer(owner, balance);
    }
}
