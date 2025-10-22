#!/bin/bash


WEBHOOK_URL="${1:-http://localhost:5678/signal/grid}"

echo "=========================================="
echo "Grid Signal Test Script"
echo "=========================================="
echo ""
echo "Webhook URL: $WEBHOOK_URL"
echo ""

echo "1. Sending ChatGPT grid signal..."
echo ""

curl -X POST "$WEBHOOK_URL" \
  -H "Content-Type: application/json" \
  -d @signal-chatgpt.json

echo ""
echo ""
echo "Waiting 3 seconds..."
sleep 3
echo ""

echo "2. Sending Grok grid signal..."
echo ""

curl -X POST "$WEBHOOK_URL" \
  -H "Content-Type: application/json" \
  -d @signal-grok.json

echo ""
echo ""
echo "=========================================="
echo "Signals sent!"
echo "=========================================="
echo ""
echo "Check results:"
echo "  - Orders: curl http://localhost:8000/orders"
echo "  - Grid status: curl http://localhost:8000/grid/status?model=chatgpt&symbol=SOLUSDT"
echo "  - Frontend: Open http://localhost:5173 (if running locally)"
echo ""
