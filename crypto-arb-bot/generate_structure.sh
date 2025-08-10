#!/bin/bash
mkdir -p contracts/interfaces
mkdir -p core/src/{executor,scanner,ml,feeds}
mkdir -p ml
mkdir -p scripts
mkdir -p config

touch contracts/FlashLoanArbitrage.sol
touch contracts/CrossChainArbitrage.sol
touch contracts/interfaces/{IAave.sol,IUniswapV3.sol,IDyDx.sol}
touch core/src/main.rs
touch core/src/executor/{mod.rs,flash_loan.rs,cross_chain.rs}
touch core/src/scanner/{mod.rs,mempool.rs,orderbook.rs}
touch core/src/ml/{mod.rs,predictor.rs,reinforcement.rs}
touch core/src/feeds/{mod.rs,websocket.rs,graph_indexer.rs}
touch core/Cargo.toml
touch ml/{train.py,model.py,dataset.py,metal_optimizer.py}
touch scripts/{deploy.ts,monitor.ts,backtest.ts}
touch config/{chains.json,dexs.json,strategies.json}
touch {.env,package.json,requirements.txt,hardhat.config.ts,docker-compose.yml}
