#!/bin/bash
# Real-time system monitoring

echo "📊 ULTRA-HFT SYSTEM MONITOR"
echo "==========================="

while true; do
    clear
    echo "🚀 Ultra-HFT Performance Dashboard - $(date)"
    echo "=============================================="
    echo ""
    
    # System metrics
    echo "💻 SYSTEM METRICS:"
    echo "CPU Usage: $(top -l 1 | grep "CPU usage" | awk '{print $3}' | sed 's/%//g')%"
    echo "Memory: $(ps -o pid,rss,comm -p $(pgrep realistic-arbitrage-bot) 2>/dev/null | tail -n +2 | awk '{print $2/1024 "MB"}' || echo "0MB")"
    echo "Network: $(netstat -ibn 2>/dev/null | grep -E "en0|eth0" | head -1 | awk '{print "RX: " $7/1024/1024 "MB TX: " $10/1024/1024 "MB"}' || echo "N/A")"
    echo ""
    
    # Application metrics
    echo "⚡ APPLICATION METRICS:"
    echo "Status: $(pgrep realistic-arbitrage-bot >/dev/null && echo "🟢 RUNNING" || echo "🔴 STOPPED")"
    echo "Uptime: $(ps -o etime= -p $(pgrep realistic-arbitrage-bot) 2>/dev/null | tr -d ' ' || echo "0:00")"
    echo ""
    
    # Trading metrics (from logs)
    echo "💰 TRADING METRICS:"
    if [ -f "data/logs/performance.log" ]; then
        tail -n 5 data/logs/performance.log
    else
        echo "No performance data available"
    fi
    echo ""
    
    # Live opportunities
    echo "🎯 LATEST OPPORTUNITIES:"
    if [ -f "data/logs/opportunities.log" ]; then
        tail -n 3 data/logs/opportunities.log
    else
        echo "No opportunities logged yet"
    fi
    
    echo ""
    echo "Press Ctrl+C to exit monitoring..."
    
    sleep 5
done
