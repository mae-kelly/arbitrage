#!/bin/bash
echo "🚀 Starting Crypto Arbitrage Bot..."

# Activate virtual environment
if [[ -d "venv" ]]; then
    source venv/bin/activate
else
    echo "❌ Virtual environment not found"
    echo "Run: python3 -m venv venv && source venv/bin/activate"
    exit 1
fi

# Check if Redis is running
if ! redis-cli ping > /dev/null 2>&1; then
    echo "⚠️  Redis not running. Starting Redis..."
    brew services start redis
    sleep 2
fi

# Start the bot
if [[ -f "main.py" ]]; then
    echo "🤖 Starting main bot..."
    python main.py
else
    echo "❌ main.py not found. Available files:"
    ls -la *.py 2>/dev/null || echo "No Python files found"
    echo ""
    echo "💡 Try running the test bot instead:"
    echo "python tests/test_bot.py"
fi
