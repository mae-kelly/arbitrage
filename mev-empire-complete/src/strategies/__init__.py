from .dex_arbitrage.engine import DEXArbitrageEngine
from .liquidation_hunting.hunter import LiquidationHunter
from .sandwich_attacks.coordinator import SandwichCoordinator
from .bridge_arbitrage.bridge_monitor import BridgeArbitrageMonitor
from .governance_sniping.vote_tracker import GovernanceSniper
from .nft_arbitrage.marketplace_scanner import NFTArbitrageEngine
from .options_arbitrage.options_scanner import OptionsArbitrageEngine
from .protocol_exploits.new_protocol_scanner import ProtocolExploiter

AVAILABLE_STRATEGIES = {
    "dex_arbitrage": DEXArbitrageEngine,
    "liquidation_hunting": LiquidationHunter,
    "sandwich_attacks": SandwichCoordinator,
    "bridge_arbitrage": BridgeArbitrageMonitor,
    "governance_sniping": GovernanceSniper,
    "nft_arbitrage": NFTArbitrageEngine,
    "options_arbitrage": OptionsArbitrageEngine,
    "protocol_exploits": ProtocolExploiter
}

__all__ = [
    "DEXArbitrageEngine",
    "LiquidationHunter", 
    "SandwichCoordinator",
    "BridgeArbitrageMonitor",
    "GovernanceSniper",
    "NFTArbitrageEngine",
    "OptionsArbitrageEngine",
    "ProtocolExploiter",
    "AVAILABLE_STRATEGIES"
]
