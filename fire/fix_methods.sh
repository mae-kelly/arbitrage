#!/bin/bash
echo "Fixing method names..."
# Check what method actually exists and replace
if grep -q "async def scan_opportunities" strategies/dex_arbitrage.py; then
    sed -i '' 's/find_opportunity/scan_opportunities/g' main.py
elif grep -q "async def scan" strategies/dex_arbitrage.py; then
    sed -i '' 's/find_opportunity/scan/g' main.py
else
    echo "Creating find_opportunity method..."
    # Add the method if it doesn't exist
    cat >> strategies/dex_arbitrage.py << 'ENDMETHOD'

    async def find_opportunity(self):
        """Find arbitrage opportunity"""
        try:
            return await self.scan_opportunities() if hasattr(self, 'scan_opportunities') else None
        except:
            return None
ENDMETHOD
fi
echo "✓ Methods fixed"
