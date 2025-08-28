import fileinput
import sys

# Fix the main.py file to properly get w3 from rpc_manager
with open('main.py', 'r') as f:
    content = f.read()

content = content.replace(
    "w3 = self.rpc_manager.get_best_provider()",
    "w3 = self.rpc_manager.get_best_provider().w3 if hasattr(self.rpc_manager.get_best_provider(), 'w3') else self.rpc_manager.w3"
)

with open('main.py', 'w') as f:
    f.write(content)
    
print("Fixed RPC issues")
