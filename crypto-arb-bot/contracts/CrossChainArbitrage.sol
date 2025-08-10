pragma solidity ^0.8.19;

interface IStargateRouter {
    struct lzTxObj {
        uint256 dstGasForCall;
        uint256 dstNativeAmount;
        bytes dstNativeAddr;
    }
    function swap(
        uint16 _dstChainId,
        uint256 _srcPoolId,
        uint256 _dstPoolId,
        address payable _refundAddress,
        uint256 _amountLD,
        uint256 _minAmountLD,
        lzTxObj memory _lzTxParams,
        bytes calldata _to,
        bytes calldata _payload
    ) external payable;
}

contract CrossChainArbitrage {
    IStargateRouter constant stargateRouter = IStargateRouter(0x8731d54E9D02c286767d56ac03e8037C07e01e98);
    address immutable owner;
    mapping(uint16 => mapping(address => uint256)) public pendingArbitrage;
    
    struct CrossChainParams {
        uint16 srcChainId;
        uint16 dstChainId;
        uint256 srcPoolId;
        uint256 dstPoolId;
        uint256 amount;
        uint256 minAmount;
        address token;
    }
    
    constructor() {
        owner = msg.sender;
    }
    
    function initiateCrossChainArbitrage(CrossChainParams calldata params) external payable {
        require(msg.sender == owner, "Not owner");
        
        IStargateRouter.lzTxObj memory lzTxParams = IStargateRouter.lzTxObj({
            dstGasForCall: 500000,
            dstNativeAmount: 0,
            dstNativeAddr: "0x"
        });
        
        stargateRouter.swap{value: msg.value}(
            params.dstChainId,
            params.srcPoolId,
            params.dstPoolId,
            payable(address(this)),
            params.amount,
            params.minAmount,
            lzTxParams,
            abi.encodePacked(address(this)),
            ""
        );
        
        pendingArbitrage[params.dstChainId][params.token] = params.amount;
    }
    
    receive() external payable {}
}
