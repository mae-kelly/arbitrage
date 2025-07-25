#!/usr/bin/env python3
"""Test script to verify the setup is working."""

def test_imports():
    """Test importing key packages."""
    import sys
    print(f"Python version: {sys.version}")
    
    packages = [
        'redis',
        'websockets', 
        'aiohttp',
        'web3',
        'numpy',
        'pandas',
        'ccxt',
        'pydantic',
        'fastapi',
        'loguru'
    ]
    
    results = {}
    for package in packages:
        try:
            __import__(package)
            results[package] = "✅ OK"
        except ImportError as e:
            results[package] = f"❌ FAILED: {e}"
    
    print("\n📋 Package Import Results:")
    print("=" * 40)
    for package, status in results.items():
        print(f"{package:15} {status}")
    
    # Test Redis connection
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379, db=0)
        r.ping()
        print(f"{'Redis conn':15} ✅ Connected")
    except Exception as e:
        print(f"{'Redis conn':15} ❌ Failed: {e}")

if __name__ == "__main__":
    test_imports()
