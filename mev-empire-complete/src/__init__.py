__version__ = "1.0.0"
__title__ = "MEV Empire"
__description__ = "Ultimate Flash Loan MEV Arbitrage System"
__author__ = "MEV Empire Team"
__license__ = "Proprietary"

from .main import main
from .empire_controller import EmpireController

__all__ = ["main", "EmpireController"]
