import sys
import os
sys.path.insert(0, '/app')

print("Testing container startup...")
print(f"Python path: {sys.path}")
print(f"Working directory: {os.getcwd()}")
print(f"Directory contents: {os.listdir('.')}")

try:
    import redis
    print("Redis import: OK")
except Exception as e:
    print(f"Redis import failed: {e}")

try:
    import torch
    print("PyTorch import: OK")
except Exception as e:
    print(f"PyTorch import failed: {e}")

try:
    import pandas
    print("Pandas import: OK")
except Exception as e:
    print(f"Pandas import failed: {e}")

print("Container test completed successfully!")
