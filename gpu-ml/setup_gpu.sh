#!/bin/bash

export CUDA_HOME=/usr/local/cuda
export PATH=$CUDA_HOME/bin:$PATH
export LD_LIBRARY_PATH=$CUDA_HOME/lib64:$LD_LIBRARY_PATH

nvidia-smi

python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}'); print(f'GPU count: {torch.cuda.device_count()}')"

python -c "import cupy; print(f'CuPy version: {cupy.__version__}')"

mkdir -p models checkpoints logs

nohup python gpu_price_predictor.py > logs/predictor.log 2>&1 &
nohup python gpu_portfolio_optimizer.py > logs/optimizer.log 2>&1 &

echo "GPU ML components initialized"
