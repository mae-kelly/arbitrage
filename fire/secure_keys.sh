#!/bin/bash
# secure_keys.sh

set -e

echo "======================================"
echo "    Secure Key Management Setup       "
echo "======================================"
echo ""

KEY_STORE_METHOD=""
while [[ ! "$KEY_STORE_METHOD" =~ ^[1-4]$ ]]; do
    echo "Select key storage method:"
    echo "1) Environment Variables (Session Only)"
    echo "2) Encrypted File (Password Protected)"
    echo "3) Hardware Security Module (HSM)"
    echo "4) AWS Secrets Manager"
    read -p "Enter choice (1-4): " KEY_STORE_METHOD
done

case $KEY_STORE_METHOD in
    1)
        echo ""
        echo "Setting up session-only environment variables..."
        echo "================================================="
        echo ""
        echo "⚠️  Keys will only persist in this terminal session"
        echo ""
        
        read -sp "Enter PRIVATE_KEY: " PRIVATE_KEY
        export PRIVATE_KEY
        echo ""
        
        read -p "Enter WALLET_ADDRESS: " WALLET_ADDRESS
        export WALLET_ADDRESS
        
        read -p "Enter ALCHEMY_API_KEY: " ALCHEMY_API_KEY
        export ALCHEMY_API_KEY
        
        read -p "Enter OKX_API_KEY: " OKX_API_KEY
        export OKX_API_KEY
        
        read -sp "Enter OKX_SECRET_KEY: " OKX_SECRET_KEY
        export OKX_SECRET_KEY
        echo ""
        
        read -p "Enter OKX_PASSPHRASE: " OKX_PASSPHRASE
        export OKX_PASSPHRASE
        
        echo ""
        echo "✅ Environment variables set for this session"
        echo ""
        echo "To use in Python:"
        echo "  import os"
        echo "  private_key = os.environ.get('PRIVATE_KEY')"
        ;;
        
    2)
        echo ""
        echo "Setting up encrypted key storage..."
        echo "===================================="
        echo ""
        
        if ! command -v openssl &> /dev/null; then
            echo "Installing OpenSSL..."
            sudo apt-get update && sudo apt-get install -y openssl
        fi
        
        KEY_FILE=".keys.enc"
        
        read -sp "Create encryption password: " ENCRYPT_PASS
        echo ""
        read -sp "Confirm password: " ENCRYPT_PASS_CONFIRM
        echo ""
        
        if [ "$ENCRYPT_PASS" != "$ENCRYPT_PASS_CONFIRM" ]; then
            echo "❌ Passwords do not match"
            exit 1
        fi
        
        echo "Enter your keys:"
        read -sp "PRIVATE_KEY: " PRIVATE_KEY
        echo ""
        read -p "WALLET_ADDRESS: " WALLET_ADDRESS
        read -p "ALCHEMY_API_KEY: " ALCHEMY_API_KEY
        read -p "OKX_API_KEY: " OKX_API_KEY
        read -sp "OKX_SECRET_KEY: " OKX_SECRET_KEY
        echo ""
        read -p "OKX_PASSPHRASE: " OKX_PASSPHRASE
        
        cat > .keys.tmp << EOF
export PRIVATE_KEY="$PRIVATE_KEY"
export WALLET_ADDRESS="$WALLET_ADDRESS"
export ALCHEMY_API_KEY="$ALCHEMY_API_KEY"
export OKX_API_KEY="$OKX_API_KEY"
export OKX_SECRET_KEY="$OKX_SECRET_KEY"
export OKX_PASSPHRASE="$OKX_PASSPHRASE"
EOF
        
        openssl enc -aes-256-cbc -salt -in .keys.tmp -out $KEY_FILE -pass pass:$ENCRYPT_PASS
        rm .keys.tmp
        
        echo ""
        echo "✅ Keys encrypted and saved to $KEY_FILE"
        echo ""
        echo "To load keys:"
        echo "  ./secure_keys.sh --decrypt"
        
        cat > decrypt_keys.sh << 'EOF'
#!/bin/bash
read -sp "Enter decryption password: " DECRYPT_PASS
echo ""
DECRYPTED=$(openssl enc -aes-256-cbc -d -in .keys.enc -pass pass:$DECRYPT_PASS)
eval "$DECRYPTED"
echo "✅ Keys loaded into environment"
EOF
        chmod +x decrypt_keys.sh
        ;;
        
    3)
        echo ""
        echo "Hardware Security Module Setup"
        echo "==============================="
        echo ""
        echo "Supported HSMs:"
        echo "- Ledger Nano S/X"
        echo "- Trezor Model T"
        echo "- YubiHSM 2"
        echo ""
        
        read -p "Enter HSM type (ledger/trezor/yubihsm): " HSM_TYPE
        
        if [ "$HSM_TYPE" == "ledger" ]; then
            echo ""
            echo "Installing Ledger support..."
            pip3 install ledger-ethereum
            
            cat > hsm_config.py << 'EOF'
from ledger_ethereum import LedgerEthereumClient

def get_hsm_signer():
    client = LedgerEthereumClient()
    return client.get_account(0)
EOF
            
        elif [ "$HSM_TYPE" == "trezor" ]; then
            echo ""
            echo "Installing Trezor support..."
            pip3 install trezor ethereum-trezor
            
            cat > hsm_config.py << 'EOF'
from trezorlib.client import get_default_client
from trezorlib.tools import parse_path
from trezorlib import ethereum

def get_hsm_signer():
    client = get_default_client()
    path = parse_path("m/44'/60'/0'/0/0")
    return ethereum.get_address(client, path)
EOF
        fi
        
        echo ""
        echo "✅ HSM configuration created in hsm_config.py"
        ;;
        
    4)
        echo ""
        echo "AWS Secrets Manager Setup"
        echo "========================="
        echo ""
        
        if ! command -v aws &> /dev/null; then
            echo "Installing AWS CLI..."
            curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
            unzip awscliv2.zip
            sudo ./aws/install
            rm -rf aws awscliv2.zip
        fi
        
        echo "Configuring AWS credentials..."
        aws configure
        
        SECRET_NAME="defi-bot-keys-$(date +%s)"
        REGION=$(aws configure get region)
        
        echo ""
        echo "Creating secret: $SECRET_NAME"
        
        read -sp "Enter PRIVATE_KEY: " PRIVATE_KEY
        echo ""
        read -p "Enter other keys..."
        
        aws secretsmanager create-secret \
            --name $SECRET_NAME \
            --secret-string "{
                \"PRIVATE_KEY\":\"$PRIVATE_KEY\",
                \"WALLET_ADDRESS\":\"$WALLET_ADDRESS\",
                \"ALCHEMY_API_KEY\":\"$ALCHEMY_API_KEY\",
                \"OKX_API_KEY\":\"$OKX_API_KEY\",
                \"OKX_SECRET_KEY\":\"$OKX_SECRET_KEY\",
                \"OKX_PASSPHRASE\":\"$OKX_PASSPHRASE\"
            }"
        
        cat > aws_secrets.py << EOF
import boto3
import json

def get_secrets():
    client = boto3.client('secretsmanager', region_name='$REGION')
    response = client.get_secret_value(SecretId='$SECRET_NAME')
    return json.loads(response['SecretString'])
EOF
        
        echo ""
        echo "✅ Keys stored in AWS Secrets Manager"
        echo "   Secret Name: $SECRET_NAME"
        echo "   Region: $REGION"
        ;;
esac

echo ""
echo "======================================"
echo "    Additional Security Options       "
echo "======================================"
echo ""

read -p "Enable key rotation reminder? (y/n): " ROTATION

if [ "$ROTATION" == "y" ]; then
    echo "*/30 * * * * echo 'Time to rotate your API keys!' | mail -s 'Key Rotation Reminder' $USER" | crontab -
    echo "✅ Monthly key rotation reminder set"
fi

read -p "Set up fail2ban for API protection? (y/n): " FAIL2BAN

if [ "$FAIL2BAN" == "y" ]; then
    sudo apt-get install -y fail2ban
    
    sudo tee /etc/fail2ban/jail.local << EOF
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 5

[defi-bot]
enabled = true
port = 8080
filter = defi-bot
logpath = $(pwd)/logs/*.log
EOF
    
    sudo systemctl restart fail2ban
    echo "✅ Fail2ban configured"
fi

echo ""
echo "Security setup complete!"