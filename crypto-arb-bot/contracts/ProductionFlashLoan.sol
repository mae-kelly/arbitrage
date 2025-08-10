pragma solidity ^0.8.19;

interface IAavePool {
    function flashLoanSimple(address receiverAddress, address asset, uint256 amount, bytes calldata params, uint16 referralCode) external;
}

interface IERC20 {
    function balanceOf(address) external view returns (uint256);
    function approve(address, uint256) external returns (bool);
}

contract ProductionFlashLoan {
    IAavePool constant AAVE = IAavePool(0x7d2768dE32b0b80b7a3454c06BdAc94A69DDc7A9);
    address owner;
    
    constructor() { owner = msg.sender; }
    
    function executeArbitrage(address asset, uint256 amount, bytes calldata params) external {
        require(msg.sender == owner);
        AAVE.flashLoanSimple(address(this), asset, amount, params, 0);
    }
    
    function executeOperation(address asset, uint256 amount, uint256 premium, address initiator, bytes calldata params) external returns (bool) {
        require(msg.sender == address(AAVE));
        
        (address dexA, address dexB, uint256 minProfit) = abi.decode(params, (address, address, uint256));
        
        IERC20(asset).approve(dexA, amount);
        (bool success1,) = dexA.call(abi.encodeWithSignature("swapExactTokensForTokens(uint256,uint256,address[],address,uint256)", amount, 0, new address[](0), address(this), block.timestamp));
        require(success1);
        
        uint256 balance = IERC20(asset).balanceOf(address(this));
        IERC20(asset).approve(dexB, balance);
        (bool success2,) = dexB.call(abi.encodeWithSignature("swapExactTokensForTokens(uint256,uint256,address[],address,uint256)", balance, 0, new address[](0), address(this), block.timestamp));
        require(success2);
        
        uint256 finalBalance = IERC20(asset).balanceOf(address(this));
        require(finalBalance >= amount + premium + minProfit);
        
        IERC20(asset).approve(address(AAVE), amount + premium);
        return true;
    }
}
