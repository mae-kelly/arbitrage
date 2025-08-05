pragma solidity ^0.8.19;

import "@openzeppelin/contracts/security/ReentrancyGuard.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "./MegaFlashLoanAggregator.sol";

contract AtomicMEVExecutor is ReentrancyGuard, Ownable {
    MegaFlashLoanAggregator public flashLoanAggregator;
    
    struct MEVOpportunity {
        uint8 strategyType;
        address targetToken;
        uint256 amount;
        address[] exchanges;
        bytes executionData;
        uint256 minProfit;
    }
    
    mapping(address => bool) public authorizedStrategies;
    mapping(uint8 => address) public strategyContracts;
    
    event MEVExecuted(uint8 indexed strategyType, uint256 profit, uint256 gasUsed);
    event StrategyRegistered(uint8 indexed strategyType, address indexed strategy);
    
    modifier onlyAuthorized() {
        require(authorizedStrategies[msg.sender], "Unauthorized");
        _;
    }
    
    constructor(address _flashLoanAggregator) {
        flashLoanAggregator = MegaFlashLoanAggregator(_flashLoanAggregator);
    }
    
    function executeAtomicMEV(MEVOpportunity calldata opportunity) external onlyAuthorized nonReentrant {
        uint256 gasStart = gasleft();
        
        require(opportunity.minProfit > 0, "Invalid min profit");
        require(strategyContracts[opportunity.strategyType] != address(0), "Strategy not registered");
        
        bytes memory flashLoanData = abi.encode(opportunity.strategyType, opportunity.executionData);
        
        flashLoanAggregator.executeFlashLoan(
            opportunity.targetToken,
            opportunity.amount,
            flashLoanData
        );
        
        uint256 gasUsed = gasStart - gasleft();
        emit MEVExecuted(opportunity.strategyType, opportunity.minProfit, gasUsed);
    }
    
    function executeMultiStrategy(MEVOpportunity[] calldata opportunities) external onlyAuthorized nonReentrant {
        for (uint256 i = 0; i < opportunities.length; i++) {
            if (_validateOpportunity(opportunities[i])) {
                _executeSingleStrategy(opportunities[i]);
            }
        }
    }
    
    function registerStrategy(uint8 strategyType, address strategy) external onlyOwner {
        require(strategy != address(0), "Invalid strategy address");
        strategyContracts[strategyType] = strategy;
        authorizedStrategies[strategy] = true;
        emit StrategyRegistered(strategyType, strategy);
    }
    
    function _executeSingleStrategy(MEVOpportunity memory opportunity) internal {
        address strategy = strategyContracts[opportunity.strategyType];
        
        (bool success, bytes memory result) = strategy.call(
            abi.encodeWithSignature("execute(bytes)", opportunity.executionData)
        );
        
        require(success, "Strategy execution failed");
        
        uint256 profit = abi.decode(result, (uint256));
        require(profit >= opportunity.minProfit, "Insufficient profit");
    }
    
    function _validateOpportunity(MEVOpportunity memory opportunity) internal view returns (bool) {
        return opportunity.amount > 0 && 
               opportunity.minProfit > 0 && 
               strategyContracts[opportunity.strategyType] != address(0);
    }
    
    function emergencyWithdraw(address token, uint256 amount) external onlyOwner {
        IERC20(token).transfer(owner(), amount);
    }
    
    function updateFlashLoanAggregator(address newAggregator) external onlyOwner {
        flashLoanAggregator = MegaFlashLoanAggregator(newAggregator);
    }
}
