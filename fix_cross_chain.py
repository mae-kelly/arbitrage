import re

with open('cross_chain_sync.py', 'r') as f:
    content = f.read()

# Replace mock execution with real transaction building
real_execution = '''
    async def execute_ethereum_strategy(self, w3: Web3, opportunity: Dict) -> Dict:
        """Execute real strategy on Ethereum"""
        try:
            # Build real transaction
            nonce = w3.eth.get_transaction_count(self.account_address)
            
            # Determine strategy type and build appropriate calldata
            if opportunity['type'] == 'arbitrage':
                contract_address = self.get_arbitrage_contract()
                calldata = self.encode_arbitrage_execution(opportunity)
            elif opportunity['type'] == 'liquidation':
                contract_address = self.get_liquidation_contract()
                calldata = self.encode_liquidation_execution(opportunity)
            else:
                contract_address = self.get_generic_contract()
                calldata = self.encode_generic_execution(opportunity)
            
            tx = {
                'nonce': nonce,
                'gasPrice': w3.eth.gas_price,
                'gas': 1000000,
                'to': contract_address,
                'value': 0,
                'data': calldata,
                'chainId': 1
            }
            
            # Sign and send
            signed_tx = w3.eth.account.sign_transaction(tx, private_key=self.private_key)
            tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
            
            # Wait for receipt
            receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
            
            # Calculate actual profit from events
            profit = self.calculate_profit_from_receipt(receipt)
            
            return {
                'tx_hash': tx_hash.hex(),
                'profit': profit,
                'gas_used': receipt['gasUsed'],
                'status': receipt['status']
            }
        except Exception as e:
            return {'tx_hash': '0x', 'profit': 0, 'error': str(e)}
'''

# Replace the mock function
content = re.sub(
    r"async def execute_ethereum_strategy.*?return \{'tx_hash':.*?\}",
    real_execution,
    content,
    flags=re.DOTALL
)

with open('cross_chain_sync.py', 'w') as f:
    f.write(content)

print("✅ Fixed cross_chain_sync.py")
