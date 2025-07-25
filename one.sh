#!/bin/bash

echo "🔧 FIXING PYTHON-DOTENV IMPORT ISSUE"
echo "===================================="
echo "The package is installed as 'python-dotenv' but imports as 'dotenv'"
echo ""

# Test the current status
echo "🧪 Testing current dotenv status..."
python3 -c "
try:
    import dotenv
    print('✅ dotenv import works correctly')
    print(f'   Location: {dotenv.__file__}')
    print(f'   Version: {dotenv.__version__}')
except ImportError as e:
    print(f'❌ dotenv import failed: {e}')
    print('   Need to reinstall python-dotenv')

try:
    from dotenv import load_dotenv
    print('✅ load_dotenv import works')
except ImportError as e:
    print(f'❌ load_dotenv import failed: {e}')
"

echo ""
echo "🔧 Reinstalling python-dotenv to fix import issues..."
pip uninstall python-dotenv -y
pip install python-dotenv

echo ""
echo "🧪 Testing after reinstall..."
python3 -c "
print('Testing python-dotenv after reinstall:')
try:
    import dotenv
    from dotenv import load_dotenv
    print('✅ dotenv imports work perfectly')
    print(f'   Version: {dotenv.__version__}')
    
    # Test functionality
    import os
    load_dotenv()
    print('✅ load_dotenv() function works')
except ImportError as e:
    print(f'❌ Still having issues: {e}')
except Exception as e:
    print(f'⚠️  Import works but function error: {e}')
"

echo ""
echo "🧪 Now testing the complete setup..."
python3 -c "
print('🧪 COMPLETE PACKAGE TEST')
print('========================')

packages_to_test = [
    ('requests', 'requests'),
    ('ccxt', 'ccxt'), 
    ('fastapi', 'fastapi'),
    ('uvicorn', 'uvicorn'),
    ('dotenv', 'python-dotenv'),  # Correct import name
    ('loguru', 'loguru'),
    ('pandas', 'pandas'),
    ('numpy', 'numpy'),
    ('web3', 'web3'),
    ('aiohttp', 'aiohttp'),
    ('websockets', 'websockets'),
    ('psutil', 'psutil'),
    ('redis', 'redis')
]

success = 0
failed = 0

for import_name, package_name in packages_to_test:
    try:
        module = __import__(import_name)
        print(f'✅ {package_name} (imports as {import_name})')
        success += 1
    except ImportError as e:
        print(f'❌ {package_name}: {e}')
        failed += 1

print(f'\\n📊 Final Results: {success} working, {failed} failed')
if failed == 0:
    print('🎉 ALL PACKAGES WORKING PERFECTLY!')
else:
    print(f'⚠️  {failed} packages still need fixing')
"

echo ""
echo "🎯 DOTENV FIX COMPLETE!"
echo "======================="
echo ""
echo "The correct way to import python-dotenv is:"
echo "   import dotenv"
echo "   from dotenv import load_dotenv"
echo ""
echo "🧪 Test your bot now:"
echo "   python test_complete_setup.py"
echo ""
echo "🚀 If that works, start your bot:"
echo "   python main.py"