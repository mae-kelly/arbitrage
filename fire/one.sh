# Fix the path to the compiled binary in rust_bridge.py
sed -i '' "s|'./core/rust_ws/target/release/mev_scanner'|'./rust_ws/target/release/rust_ws'|g" core/rust_bridge.py
sed -i '' "s|'./rust_ws/target/release/mev_scanner'|'./rust_ws/target/release/rust_ws'|g" core/rust_bridge.py

# Run the bot again
python3 main.py