#!/bin/bash
echo "📦 Installing all packages..."

# Make sure venv is activated
if [[ "$VIRTUAL_ENV" == "" ]]; then
    echo "❌ Please activate virtual environment first:"
    echo "source venv/bin/activate"
    exit 1
fi

echo "📦 Installing Python packages..."
pip install --upgrade pip
pip install -r requirements.txt

echo "✅ All packages installed!"
echo ""
echo "🚀 Next steps:"
echo "   ./scripts/run_tests.sh    # Test the system"
echo "   ./scripts/start_bot.sh    # Start the bot"
