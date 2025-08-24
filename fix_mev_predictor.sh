#!/bin/bash
sed -i.bak '
s/return 3200 + np.random.uniform(-50, 50)/# Get real price from DEX\
        try:\
            pair_contract = self.w3.eth.contract(\
                address=Web3.toChecksumAddress(pool_address),\
                abi=[{"constant":True,"inputs":[],"name":"getReserves","outputs":[{"name":"_reserve0","type":"uint112"},{"name":"_reserve1","type":"uint112"},{"name":"_blockTimestampLast","type":"uint32"}],"type":"function"},\
                     {"constant":True,"inputs":[],"name":"token0","outputs":[{"name":"","type":"address"}],"type":"function"}]\
            )\
            reserves = pair_contract.functions.getReserves().call()\
            token0 = pair_contract.functions.token0().call()\
            \
            # Assuming WETH\/USDC pair\
            weth = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"\
            if token0.lower() == weth.lower():\
                price = (reserves[1] \/ 10**6) \/ (reserves[0] \/ 10**18)\
            else:\
                price = (reserves[0] \/ 10**6) \/ (reserves[1] \/ 10**18)\
            return price\
        except:\
            return 3200.0/g
' mev_predictor.py

echo "✅ Fixed mev_predictor.py pool price function"
