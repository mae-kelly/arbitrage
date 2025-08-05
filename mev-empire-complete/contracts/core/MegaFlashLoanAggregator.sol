pragma solidity ^0.8.19;

import "@openzeppelin/contracts/security/ReentrancyGuard.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";

interface IAaveFlashLoan {
    function flashLoan(address receiverAddress, address[] calldata assets, uint256[] calldata amounts, uint256[] calldata modes, address onBehalfOf, bytes calldata params, uint16 referralCode) external;
}

interface IDYDXFlashLoan {
    function flashLoan(address token, uint256 amount, bytes calldata data) external;
}

interface IBalancerVault {
    function flashLoan(address recipient, address[] memory tokens, uint256[] memory amounts, bytes memory userData) external;
}

interface IUniswapV3FlashCallback {
    function uniswapV3FlashCallback(uint256 fee0, uint256 fee1, bytes calldata data) external;
}

contract MegaFlashLoanAggregator is ReentrancyGuard, Ownable {
    address public constant AAVE_LENDING_POOL = 0x7d2768dE32b0b80b7a3454c06BdAc94A69DDc7A9;
    address public constant DYDX_SOLO_MARGIN = 0x1E0447b19BB6EcFdAe1e4AE1694b0C3659614e4e;
    address public constant BALANCER_VAULT = 0xBA12222222228d8Ba445958a75a0704d566BF2C8;
    address public constant UNISWAP_V3_FACTORY = 0x1F98431c8aD98523631AE4a59f267346ea31F984;
    
    struct FlashLoanParams {
        address token;
        uint256 amount;
        bytes strategyData;
        uint8 provider;
    }
    
    event FlashLoanExecuted(address indexed token, uint256 amount, uint256 profit, uint8 provider);
    
    function executeFlashLoan(address token, uint256 amount, bytes calldata strategyData) external nonReentrant {
        FlashLoanParams memory params = FlashLoanParams({
            token: token,
            amount: amount,
            strategyData: strategyData,
            provider: _selectOptimalProvider(token, amount)
        });
        
        if (params.provider == 1) {
            _executeAaveFlashLoan(params);
        } else if (params.provider == 2) {
            _executeDYDXFlashLoan(params);
        } else if (params.provider == 3) {
            _executeBalancerFlashLoan(params);
        } else {
            _executeUniswapV3FlashLoan(params);
        }
    }
    
    function _selectOptimalProvider(address token, uint256 amount) internal view returns (uint8) {
        uint256 aaveFee = _getAaveFee(token, amount);
        uint256 dydxFee = _getDYDXFee(token, amount);
        uint256 balancerFee = _getBalancerFee(token, amount);
        uint256 uniswapFee = _getUniswapV3Fee(token, amount);
        
        uint256 minFee = aaveFee;
        uint8 provider = 1;
        
        if (dydxFee < minFee) {
            minFee = dydxFee;
            provider = 2;
        }
        if (balancerFee < minFee) {
            minFee = balancerFee;
            provider = 3;
        }
        if (uniswapFee < minFee) {
            provider = 4;
        }
        
        return provider;
    }
    
    function _executeAaveFlashLoan(FlashLoanParams memory params) internal {
        address[] memory assets = new address[](1);
        uint256[] memory amounts = new uint256[](1);
        uint256[] memory modes = new uint256[](1);
        
        assets[0] = params.token;
        amounts[0] = params.amount;
        modes[0] = 0;
        
        IAaveFlashLoan(AAVE_LENDING_POOL).flashLoan(
            address(this),
            assets,
            amounts,
            modes,
            address(this),
            params.strategyData,
            0
        );
    }
    
    function _executeDYDXFlashLoan(FlashLoanParams memory params) internal {
        IDYDXFlashLoan(DYDX_SOLO_MARGIN).flashLoan(params.token, params.amount, params.strategyData);
    }
    
    function _executeBalancerFlashLoan(FlashLoanParams memory params) internal {
        address[] memory tokens = new address[](1);
        uint256[] memory amounts = new uint256[](1);
        
        tokens[0] = params.token;
        amounts[0] = params.amount;
        
        IBalancerVault(BALANCER_VAULT).flashLoan(address(this), tokens, amounts, params.strategyData);
    }
    
    function _executeUniswapV3FlashLoan(FlashLoanParams memory params) internal {
        address pool = _getUniswapV3Pool(params.token);
        (bool success,) = pool.call(
            abi.encodeWithSignature("flash(address,uint256,uint256,bytes)", address(this), params.amount, 0, params.strategyData)
        );
        require(success, "Uniswap flash loan failed");
    }
    
    function executeReceiveFlashLoan(
        address[] calldata assets,
        uint256[] calldata amounts,
        uint256[] calldata premiums,
        address initiator,
        bytes calldata params
    ) external returns (bool) {
        require(msg.sender == AAVE_LENDING_POOL, "Invalid sender");
        
        _executeStrategy(assets[0], amounts[0], params);
        
        uint256 amountOwing = amounts[0] + premiums[0];
        IERC20(assets[0]).transfer(AAVE_LENDING_POOL, amountOwing);
        
        return true;
    }
    
    function _executeStrategy(address token, uint256 amount, bytes calldata strategyData) internal {
        (address strategy, bytes memory callData) = abi.decode(strategyData, (address, bytes));
        
        IERC20(token).transfer(strategy, amount);
        
        (bool success, bytes memory result) = strategy.call(callData);
        require(success, "Strategy execution failed");
        
        uint256 profit = abi.decode(result, (uint256));
        emit FlashLoanExecuted(token, amount, profit, 1);
    }
    
    function _getAaveFee(address token, uint256 amount) internal pure returns (uint256) {
        return amount * 9 / 10000;
    }
    
    function _getDYDXFee(address token, uint256 amount) internal pure returns (uint256) {
        return amount * 2 / 10000;
    }
    
    function _getBalancerFee(address token, uint256 amount) internal pure returns (uint256) {
        return 0;
    }
    
    function _getUniswapV3Fee(address token, uint256 amount) internal pure returns (uint256) {
        return amount * 5 / 10000;
    }
    
    function _getUniswapV3Pool(address token) internal pure returns (address) {
        return address(0);
    }
}
