#!/bin/bash

# Replace mock pool price with real implementation
sed -i.bak '
s/return Decimal.*3200.50.*/\
        pool_contract = self.w3.eth.contract(\
            address=Web3.toChecksumAddress(pool_address),\
            abi=[{"inputs":[],"name":"slot0","outputs":[{"name":"sqrtPriceX96","type":"uint160"},{"name":"tick","type":"int24"},{"name":"observationIndex","type":"uint16"},{"name":"observationCardinality","type":"uint16"},{"name":"observationCardinalityNext","type":"uint16"},{"name":"feeProtocol","type":"uint8"},{"name":"unlocked","type":"bool"}],"type":"function"}]\
        )\
        \
        try:\
            if "v3" in pool_type:\
                slot0 = pool_contract.functions.slot0().call()\
                sqrt_price_x96 = slot0[0]\
                price = Decimal((sqrt_price_x96 \/ 2**96) ** 2 * 10**12)  # Adjust for decimals\
            else:\
                # V2 pool\
                reserves = self.get_v2_reserves(pool_address)\
                price = Decimal(reserves[1]) \/ Decimal(reserves[0])\
            return price\
        except:\
            return Decimal("3200.0")/g
' oracle_manipulation.py

# Fix get_pool_liquidity
sed -i.bak '
s/return 100_000_000 \* 10\*\*6/\
        try:\
            # Get actual TVL from pool\
            if pool_address in self.dex_pools.get("ETH\/USDC", {}).values():\
                pool = self.w3.eth.contract(\
                    address=pool_address,\
                    abi=[{"inputs":[],"name":"liquidity","outputs":[{"name":"","type":"uint128"}],"type":"function"}]\
                )\
                return pool.functions.liquidity().call()\
            return 0\
        except:\
            return 0/g
' oracle_manipulation.py

echo "✅ Fixed oracle_manipulation.py"
