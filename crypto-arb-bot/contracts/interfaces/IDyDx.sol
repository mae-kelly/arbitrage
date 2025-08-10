pragma solidity ^0.8.19;

interface ISoloMargin {
    struct Info {
        address owner;
        uint256 number;
    }
    
    struct Wei {
        bool sign;
        uint256 value;
    }
    
    struct Price {
        uint256 value;
    }
    
    struct TotalPar {
        uint128 borrow;
        uint128 supply;
    }
    
    struct Index {
        uint96 borrow;
        uint96 supply;
        uint32 lastUpdate;
    }
    
    function operate(Info[] memory accounts, ActionArgs[] memory actions) external;
    
    struct ActionArgs {
        ActionType actionType;
        uint256 accountId;
        AssetAmount amount;
        uint256 primaryMarketId;
        uint256 secondaryMarketId;
        address otherAddress;
        uint256 otherAccountId;
        bytes data;
    }
    
    enum ActionType {
        Deposit,
        Withdraw,
        Transfer,
        Buy,
        Sell,
        Trade,
        Liquidate,
        Vaporize,
        Call
    }
    
    enum AssetDenomination {
        Wei,
        Par
    }
    
    enum AssetReference {
        Delta,
        Target
    }
    
    struct AssetAmount {
        bool sign;
        AssetDenomination denomination;
        AssetReference ref;
        uint256 value;
    }
}
