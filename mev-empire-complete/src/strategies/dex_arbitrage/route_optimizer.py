import asyncio
import logging
from typing import Dict, List, Optional, Tuple
from decimal import Decimal
import networkx as nx
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class DEXInfo:
    name: str
    router_address: str
    fee_rate: Decimal
    gas_cost: int
    liquidity_score: float

@dataclass
class Route:
    path: List[str]
    exchanges: List[str]
    amounts: List[Decimal]
    profit: Decimal
    gas_cost: int
    slippage: Decimal

class RouteOptimizer:
    def __init__(self):
        self.dex_registry = {}
        self.liquidity_graph = nx.Graph()
        self.price_cache = {}
        
    async def initialize(self):
        logger.info("Initializing Route Optimizer")
        await self._load_dex_registry()
        await self._build_liquidity_graph()
        logger.info("Route Optimizer initialized")
    
    async def find_optimal_route(self, token_in: str, token_out: str, 
                                amount: Decimal, preferred_exchanges: List[str] = None) -> Optional[Route]:
        try:
            if token_in == token_out:
                return None
            
            all_routes = await self._find_all_routes(token_in, token_out, amount)
            
            if preferred_exchanges:
                all_routes = [r for r in all_routes if any(ex in preferred_exchanges for ex in r.exchanges)]
            
            if not all_routes:
                return None
            
            optimal_route = max(all_routes, key=lambda r: r.profit - Decimal(str(r.gas_cost)) * Decimal("0.00001"))
            
            return optimal_route
            
        except Exception as e:
            logger.error(f"Route optimization error: {e}")
            return None
    
    async def _find_all_routes(self, token_in: str, token_out: str, amount: Decimal) -> List[Route]:
        routes = []
        
        direct_routes = await self._find_direct_routes(token_in, token_out, amount)
        routes.extend(direct_routes)
        
        multi_hop_routes = await self._find_multi_hop_routes(token_in, token_out, amount)
        routes.extend(multi_hop_routes)
        
        triangular_routes = await self._find_triangular_routes(token_in, token_out, amount)
        routes.extend(triangular_routes)
        
        return routes
    
    async def _find_direct_routes(self, token_in: str, token_out: str, amount: Decimal) -> List[Route]:
        routes = []
        
        for dex_name, dex_info in self.dex_registry.items():
            try:
                output_amount = await self._get_amount_out(token_in, token_out, amount, dex_name)
                
                if output_amount > amount:
                    profit = output_amount - amount
                    
                    route = Route(
                        path=[token_in, token_out],
                        exchanges=[dex_name],
                        amounts=[amount, output_amount],
                        profit=profit,
                        gas_cost=dex_info.gas_cost,
                        slippage=await self._calculate_slippage(token_in, token_out, amount, dex_name)
                    )
                    routes.append(route)
                    
            except Exception as e:
                logger.debug(f"Direct route error for {dex_name}: {e}")
                continue
        
        return routes
    
    async def _find_multi_hop_routes(self, token_in: str, token_out: str, amount: Decimal) -> List[Route]:
        routes = []
        intermediate_tokens = ["WETH", "USDC", "USDT", "DAI", "WBTC"]
        
        for intermediate in intermediate_tokens:
            if intermediate == token_in or intermediate == token_out:
                continue
            
            for dex1 in self.dex_registry.keys():
                for dex2 in self.dex_registry.keys():
                    try:
                        amount1 = await self._get_amount_out(token_in, intermediate, amount, dex1)
                        amount2 = await self._get_amount_out(intermediate, token_out, amount1, dex2)
                        
                        if amount2 > amount:
                            profit = amount2 - amount
                            total_gas = self.dex_registry[dex1].gas_cost + self.dex_registry[dex2].gas_cost
                            
                            route = Route(
                                path=[token_in, intermediate, token_out],
                                exchanges=[dex1, dex2],
                                amounts=[amount, amount1, amount2],
                                profit=profit,
                                gas_cost=total_gas,
                                slippage=await self._calculate_multi_hop_slippage([token_in, intermediate, token_out], [dex1, dex2])
                            )
                            routes.append(route)
                            
                    except Exception as e:
                        continue
        
        return routes
    
    async def _find_triangular_routes(self, token_in: str, token_out: str, amount: Decimal) -> List[Route]:
        routes = []
        base_tokens = ["WETH", "USDC", "USDT"]
        
        for base in base_tokens:
            if base == token_in or base == token_out:
                continue
            
            for dex in self.dex_registry.keys():
                try:
                    amount1 = await self._get_amount_out(token_in, base, amount, dex)
                    amount2 = await self._get_amount_out(base, token_out, amount1, dex)
                    amount3 = await self._get_amount_out(token_out, token_in, amount2, dex)
                    
                    if amount3 > amount:
                        profit = amount3 - amount
                        
                        route = Route(
                            path=[token_in, base, token_out, token_in],
                            exchanges=[dex, dex, dex],
                            amounts=[amount, amount1, amount2, amount3],
                            profit=profit,
                            gas_cost=self.dex_registry[dex].gas_cost * 3,
                            slippage=await self._calculate_multi_hop_slippage([token_in, base, token_out, token_in], [dex, dex, dex])
                        )
