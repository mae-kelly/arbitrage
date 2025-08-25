#!/bin/bash

echo "Fixing the final type annotation issue..."

# Fix the Vec type annotation in main.rs
sed -i '' 's/Arc::new(RwLock::new(Vec::new()))/Arc::new(RwLock::new(Vec::<arbitrage::Opportunity>::new()))/g' src/main.rs

echo "Type annotation fixed. Building..."
docker-compose up -d