pragma solidity ^0.8.19;

import "@openzeppelin/contracts/security/ReentrancyGuard.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

interface IBridge {
    function deposit(address token, uint256 amount, address recipient) external;
    function withdraw(bytes32 txHash) external;
}

contract CrossChainCoordinator is ReentrancyGuard, Ownable {
    struct CrossChainOrder {
        uint256 chainId;
        address token;
        uint256 amount;
        address bridge;
        bytes bridgeData;
        uint256 expectedOutput;
        uint256 deadline;
    }
    
    mapping(uint256 => address) public chainBridges;
    mapping(bytes32 => bool) public executedOrders;
    mapping(address => bool) public authorizedExecutors;
    
    event CrossChainOrderExecuted(bytes32 indexed orderId, uint256 chainId, uint256 profit);
    event BridgeRegistered(uint256 indexed chainId, address bridge);
    
    modifier onlyExecutor() {
        require(authorizedExecutors[msg.sender], "Not authorized");
        _;
    }
    
    function executeCrossChainArbitrage(CrossChainOrder calldata order) external onlyExecutor nonReentrant {
        bytes32 orderId = keccak256(abi.encode(order, block.timestamp));
        require(!executedOrders[orderId], "Order already executed");
        require(block.timestamp <= order.deadline, "Order expired");
        
        executedOrders[orderId] = true;
        
        IBridge bridge = IBridge(chainBridges[order.chainId]);
        require(address(bridge) != address(0), "Bridge not supported");
        
        IERC20(order.token).transferFrom(msg.sender, address(this), order.amount);
        IERC20(order.token).approve(address(bridge), order.amount);
        
        bridge.deposit(order.token, order.amount, address(this));
        
        uint256 profit = _calculateProfit(order);
        emit CrossChainOrderExecuted(orderId, order.chainId, profit);
    }
    
    function batchCrossChainExecute(CrossChainOrder[] calldata orders) external onlyExecutor nonReentrant {
        for (uint256 i = 0; i < orders.length; i++) {
            if (_validateOrder(orders[i])) {
                _executeSingleOrder(orders[i]);
            }
        }
    }
    
    function registerBridge(uint256 chainId, address bridge) external onlyOwner {
        require(bridge != address(0), "Invalid bridge");
        chainBridges[chainId] = bridge;
        emit BridgeRegistered(chainId, bridge);
    }
    
    function authorizeExecutor(address executor, bool authorized) external onlyOwner {
        authorizedExecutors[executor] = authorized;
    }
    
    function _validateOrder(CrossChainOrder memory order) internal view returns (bool) {
        return order.amount > 0 && 
               order.deadline > block.timestamp && 
               chainBridges[order.chainId] != address(0);
    }
    
    function _executeSingleOrder(CrossChainOrder memory order) internal {
        bytes32 orderId = keccak256(abi.encode(order, block.timestamp));
        
        if (!executedOrders[orderId]) {
            executedOrders[orderId] = true;
            
            IBridge bridge = IBridge(chainBridges[order.chainId]);
            bridge.deposit(order.token, order.amount, address(this));
        }
    }
    
    function _calculateProfit(CrossChainOrder memory order) internal pure returns (uint256) {
        return order.expectedOutput > order.amount ? order.expectedOutput - order.amount : 0;
    }
    
    function emergencyPause() external onlyOwner {
        // Emergency pause functionality
    }
}
