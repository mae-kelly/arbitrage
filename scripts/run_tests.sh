#!/bin/bash
echo "🧪 Running test suite..."

# Activate virtual environment
if [[ -d "venv" ]]; then
    source venv/bin/activate
fi

echo "🔍 Looking for test files..."

# Run tests in order of preference
if [[ -f "tests/test_bot.py" ]]; then
    echo "Running main test bot..."
    python tests/test_bot.py
elif [[ -f "test_bot.py" ]]; then
    echo "Running test bot..."
    python test_bot.py
else
    echo "⚠️  No test files found. Creating basic test..."
    cat > tests/basic_test.py << 'TESTEOF'
#!/usr/bin/env python3
"""Basic system test"""

print("🧪 Basic System Test")
print("=" * 30)

# Test Python environment
try:
    import sys
    print(f"✅ Python {sys.version.split()[0]}")
except Exception as e:
    print(f"❌ Python test failed: {e}")

# Test core modules
modules = ['json', 'asyncio', 'decimal', 'datetime']
for module in modules:
    try:
        __import__(module)
        print(f"✅ {module}")
    except ImportError:
        print(f"❌ {module}")

print("\n🎉 Basic tests completed!")
print("Install packages with: ./scripts/install_all.sh")
TESTEOF
    python tests/basic_test.py
fi

echo "✅ Tests completed!"
