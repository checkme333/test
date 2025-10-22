# Grid Trading Battle System: ChatGPT vs Grok

A complete multi-model grid trading system running on Aster Perpetual Exchange, featuring automated strategy execution, risk management, and real-time performance comparison.

## 🏗️ Architecture

```
[ChatGPT Strategy]     [Grok Strategy]
        \               /
         \——→ n8n (Orchestration/Risk/Audit) ——→ Trading Core (Executor)
                                                     ↘
                              Postgres (Orders/Grid/PnL) ← Redis (Queue/Rate Limit)
                                                     ↘
                                            Frontend (Next.js on Vercel)
```

## 📦 Components

### 1. Trading Core (FastAPI)
- REST API for grid management and order execution
- Aster API integration with idempotent order handling
- Risk management (leverage, exposure, daily loss limits)
- 503/5xx error handling with order confirmation
- PostgreSQL for persistent storage

### 2. n8n Workflows
- **Workflow A**: Grid signal reception and execution
- **Workflow B**: Data synchronization pipeline (every 5s)
- **Workflow C**: Risk monitoring and circuit breaker alerts

### 3. Frontend (Next.js)
- Real-time model performance comparison
- Order flow visualization
- Grid status monitoring
- Deployed to Vercel

### 4. Infrastructure
- Docker Compose orchestration
- Caddy reverse proxy with automatic HTTPS
- PostgreSQL database
- Redis for queuing and rate limiting

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- Domain name with DNS configured
- Aster API credentials
- (Optional) Telegram bot for alerts

### 1. Clone and Configure

```bash
cd /home/ubuntu/grid-trading-battle

# Copy environment files
cp .env.example .env
cp trading-core/.env.example trading-core/.env

# Edit .env files with your credentials
nano .env
nano trading-core/.env
```

### 2. Configure DNS

Point these domains to your VPS IP:
- `api.yourdomain.com` → A record to VPS IP
- `hook.yourdomain.com` → A record to VPS IP
- `app.yourdomain.com` → CNAME to Vercel (after frontend deployment)

### 3. Update Caddyfile

```bash
nano docker/caddy/Caddyfile
# Replace yourdomain.com with your actual domain
# Replace admin@yourdomain.com with your email
```

### 4. Start Services

```bash
# Start all services
docker-compose up -d

# Check logs
docker-compose logs -f

# Verify services are running
docker-compose ps
```

### 5. Deploy Frontend to Vercel

```bash
cd frontend

# Build the app
npm run build

# Update .env with production API URL
echo "VITE_API_BASE_URL=https://api.yourdomain.com" > .env

# Rebuild
npm run build

# Deploy (requires Vercel CLI or manual upload)
# Option 1: Vercel CLI
vercel --prod

# Option 2: Manual - upload dist/ folder to Vercel dashboard
```

## 📝 Environment Variables

### Root .env
```env
N8N_HOST=hook.yourdomain.com
N8N_PROTOCOL=https
N8N_ENCRYPTION_KEY=<generate-random-32-char-string>
GROK_API_KEY=<your-grok-api-key>
TELEGRAM_BOT_TOKEN=<your-telegram-bot-token>
TELEGRAM_CHAT_ID=<your-telegram-chat-id>
PUBLIC_API_BASE=https://api.yourdomain.com
```

### trading-core/.env
```env
ASTER_API_KEY=<your-aster-api-key>
ASTER_API_SECRET=<your-aster-api-secret>
ASTER_BASE_URL=https://fapi.asterdex.com

RISK_MAX_LEVERAGE=2
RISK_MAX_DAILY_LOSS=-200
RISK_MAX_SYMBOL_EXPOSURE=5000
SLIPPAGE_BPS=10

REDIS_URL=redis://redis:6379
DATABASE_URL=postgresql://tradeuser:tradepass@postgres:5432/trade

TELEGRAM_BOT_TOKEN=<your-telegram-bot-token>
TELEGRAM_CHAT_ID=<your-telegram-chat-id>
```

## 🔧 API Endpoints

### Trading Core (api.yourdomain.com)

#### Grid Management
- `POST /grid/apply` - Apply grid strategy
- `GET /grid/status?model=chatgpt&symbol=SOLUSDT` - Get grid status
- `POST /grid/pause?model=chatgpt&symbol=SOLUSDT` - Pause grid
- `POST /grid/resume?model=chatgpt&symbol=SOLUSDT` - Resume grid

#### Orders & Positions
- `GET /orders?model=chatgpt&symbol=SOLUSDT` - Get orders
- `GET /positions?symbol=SOLUSDT` - Get positions
- `GET /pnl?model=chatgpt&window=daily` - Get PnL metrics

#### Account
- `GET /account` - Get account info
- `GET /balance` - Get balance
- `GET /healthz` - Health check

### n8n Webhook (hook.yourdomain.com)

#### Grid Signal
```bash
POST https://hook.yourdomain.com/signal/grid
Content-Type: application/json

{
  "model": "chatgpt",
  "strategy": "grid",
  "symbol": "SOLUSDT",
  "lower": 180.0,
  "upper": 210.0,
  "grids": 12,
  "spacing": "arithmetic",
  "base_allocation": 2000,
  "leverage": 2,
  "entry_mode": "maker_first",
  "tp_pct": 0.03,
  "sl_pct": 0.05,
  "rebalance": false,
  "notes": "Range-bound strategy"
}
```

## 🧪 Testing

### Manual Testing

```bash
# Test Trading Core health
curl https://api.yourdomain.com/healthz

# Test grid signal (replace with your domain)
curl -X POST https://hook.yourdomain.com/signal/grid \
  -H "Content-Type: application/json" \
  -d '{
    "model": "chatgpt",
    "strategy": "grid",
    "symbol": "SOLUSDT",
    "lower": 180.0,
    "upper": 210.0,
    "grids": 12,
    "spacing": "arithmetic",
    "base_allocation": 100,
    "leverage": 1,
    "entry_mode": "maker_first",
    "tp_pct": 0.03,
    "sl_pct": 0.05,
    "rebalance": false
  }'

# Check orders
curl https://api.yourdomain.com/orders?model=chatgpt
```

### Automated Tests

```bash
cd tests
python test_idempotency.py
python test_risk_controls.py
python test_503_handling.py
```

## 🔒 Security Best Practices

1. **API Keys**: Store in .env files, never commit to git
2. **Database**: Use strong passwords, restrict network access
3. **HTTPS**: Caddy handles automatic SSL certificates
4. **Rate Limiting**: n8n enforces 60s cooldown per model/symbol
5. **Risk Controls**: Hard limits on leverage, exposure, and daily loss

## 📊 Monitoring

### Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f trading-core
docker-compose logs -f n8n

# Caddy access logs
docker exec grid-caddy cat /var/log/caddy/api.log
```

### Database
```bash
# Connect to PostgreSQL
docker exec -it grid-postgres psql -U tradeuser -d trade

# Check grid configs
SELECT * FROM grid_configs;

# Check recent orders
SELECT * FROM orders ORDER BY created_at DESC LIMIT 10;

# Check metrics
SELECT * FROM metrics ORDER BY ts DESC LIMIT 10;
```

### Redis
```bash
# Connect to Redis
docker exec -it grid-redis redis-cli

# Check rate limits
KEYS ratelimit:*

# Check queue
LLEN bull:n8n:wait
```

## 🔄 Maintenance

### Backup Database
```bash
docker exec grid-postgres pg_dump -U tradeuser trade > backup_$(date +%Y%m%d).sql
```

### Restore Database
```bash
cat backup_20251022.sql | docker exec -i grid-postgres psql -U tradeuser trade
```

### Update Services
```bash
# Pull latest images
docker-compose pull

# Restart services
docker-compose down
docker-compose up -d
```

### Clear Data (Development Only)
```bash
# WARNING: This deletes all data
docker-compose down -v
docker-compose up -d
```

## 🐛 Troubleshooting

### Trading Core won't start
- Check .env file exists and has valid credentials
- Verify database connection: `docker-compose logs postgres`
- Check port conflicts: `netstat -tulpn | grep 8000`

### n8n workflows not triggering
- Verify webhook URL is accessible
- Check n8n logs: `docker-compose logs n8n`
- Ensure Redis is running: `docker-compose ps redis`

### Frontend can't connect to API
- Verify CORS is enabled in Trading Core
- Check API URL in frontend .env
- Test API directly: `curl https://api.yourdomain.com/healthz`

### Orders not executing
- Check Aster API credentials
- Verify account has sufficient balance
- Check risk limits in trading-core/.env
- Review Trading Core logs for errors

## 📈 Performance Tuning

### Database
```sql
-- Add indexes for common queries
CREATE INDEX idx_orders_created_at ON orders(created_at DESC);
CREATE INDEX idx_metrics_model_symbol ON metrics(model, symbol, ts DESC);
```

### Redis
```bash
# Increase memory limit if needed
docker exec grid-redis redis-cli CONFIG SET maxmemory 512mb
```

### n8n
- Adjust execution timeout in workflow settings
- Enable workflow caching for better performance
- Use queue mode for high-volume scenarios

## 🎯 Next Steps

1. **Test with Paper Trading**: Use Aster testnet API keys first
2. **Monitor Performance**: Watch metrics for 24-48 hours
3. **Adjust Risk Limits**: Fine-tune based on observed volatility
4. **Scale Up**: Increase allocation once confident
5. **Add More Models**: Extend to additional AI strategy providers

## 📞 Support

- Aster API Docs: https://docs.asterdex.com
- n8n Documentation: https://docs.n8n.io
- FastAPI Docs: https://fastapi.tiangolo.com

## 📄 License

This project is for educational and research purposes. Use at your own risk. Trading involves substantial risk of loss.

---

**Built by Devin AI** | [Devin Run Link](https://app.devin.ai/sessions/d30fb57c71344089bbc89d2c8304eec6)
