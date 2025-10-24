# Live Trading Setup Guide

## ✅ Completed Setup

### 1. Aster API Configuration
- ✅ Configured individual Aster API keys for each LLM model:
  - ChatGPT account
  - Grok account
  - Claude account
  - DeepSeek account

### 2. Database Reset
- ✅ Cleared all historical trading records
- ✅ Reset all model accounts to initial balance of $500
- ✅ Current balances synced from Aster API: ~$499.93 each

### 3. New API Endpoints
- ✅ `/prices/sync` - Fetches latest prices from Aster API (SOL, BTC, ETH, BNB, ASTER)
- ✅ `/models/sync-balances` - Syncs balances from each model's Aster account

### 4. N8N Workflows Created
- ✅ `workflow-f-aster-price-sync.json` - Syncs prices every 10 seconds
- ✅ `workflow-g-aster-balance-sync.json` - Syncs balances every 1 minute

## 🔧 Manual Steps Required

### Activate N8N Workflows

The workflows have been imported into n8n but need to be manually activated:

1. **Access n8n interface**:
   - URL: `http://47.77.195.172:5678`
   - Or use SSH port forwarding: `ssh -L 5678:localhost:5678 root@47.77.195.172`

2. **Activate workflows**:
   - Find "Aster Price Sync (Every 10 Seconds)" workflow
   - Click the toggle to activate it
   - Find "Aster Balance Sync (Every 1 Minute)" workflow
   - Click the toggle to activate it

3. **Verify workflows are running**:
   - Check the execution history in n8n
   - Verify prices are updating on the website
   - Verify balances are syncing correctly

### Alternative: Activate via n8n CLI

If you have access to the server, you can activate workflows via CLI:

```bash
# SSH into the server
ssh root@47.77.195.172

# List all workflows to get their IDs
docker exec grid-n8n n8n list:workflow

# Activate workflows by ID (replace <workflow-id> with actual ID)
docker exec grid-n8n sqlite3 /home/node/.n8n/database.sqlite "UPDATE workflow_entity SET active = 1 WHERE name LIKE '%Aster%';"

# Restart n8n to apply changes
docker compose restart n8n
```

## 📊 Current Status

### Account Balances (as of reset)
- ChatGPT: $499.93 (P&L: -$0.07)
- Grok: $499.93 (P&L: -$0.07)
- Claude: $499.93 (P&L: -$0.07)
- DeepSeek: $499.93 (P&L: -$0.07)

### Trading Status
- ✅ All historical data cleared
- ✅ No open positions
- ✅ No pending orders
- ✅ LLMs are making decisions (but not executing yet)
- ⚠️ Need to activate n8n workflows for automatic sync

## 🚀 Ready for Live Trading

Once the n8n workflows are activated:

1. **Price Updates**: Will sync every 10 seconds from Aster API
2. **Balance Updates**: Will sync every 1 minute from each model's Aster account
3. **LLM Decisions**: Already being generated (visible on dashboard)
4. **Trade Execution**: Ready to execute when LLMs make decisions

## 📝 Notes

- All 4 models are using their own Aster accounts
- Real-time P&L tracking is enabled
- Initial balance set to $500 for all models
- Website: https://algoarena.app/
- Backend API: http://47.77.195.172:8000

## ⚠️ Important

Before starting live trading:
1. Verify all n8n workflows are active and running
2. Monitor the first few trades closely
3. Check that balances are syncing correctly
4. Ensure LLM decisions are being executed properly
