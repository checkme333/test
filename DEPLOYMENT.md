# Deployment Guide

Complete step-by-step guide to deploy the Grid Trading Battle System.

## Pre-Deployment Checklist

### 1. Domain & DNS Setup
- [ ] Purchase domain (e.g., `yourdomain.com`)
- [ ] Configure DNS A records:
  - `api.yourdomain.com` → VPS IP address
  - `hook.yourdomain.com` → VPS IP address
- [ ] Wait for DNS propagation (5-30 minutes)

### 2. VPS Setup
- [ ] VPS with minimum 2vCPU, 4GB RAM, 60GB storage
- [ ] Ubuntu 20.04+ or Debian 11+
- [ ] Docker and Docker Compose installed
- [ ] Ports 80, 443 open in firewall

### 3. API Credentials
- [ ] Aster API Key and Secret (testnet or mainnet)
- [ ] Grok API Key (optional, for Grok strategy)
- [ ] Telegram Bot Token and Chat ID (optional, for alerts)
- [ ] Vercel account for frontend deployment

## Step-by-Step Deployment

### Step 1: Install Docker (if not already installed)

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Docker Compose
sudo apt install docker-compose -y

# Add user to docker group
sudo usermod -aG docker $USER

# Log out and back in for group changes to take effect
```

### Step 2: Clone/Upload Project

```bash
# If using git
git clone <your-repo-url> /home/ubuntu/grid-trading-battle

# Or upload the project directory to your VPS
# scp -r grid-trading-battle user@vps-ip:/home/ubuntu/
```

### Step 3: Configure Environment Variables

```bash
cd /home/ubuntu/grid-trading-battle

# Copy environment templates
cp .env.example .env
cp trading-core/.env.example trading-core/.env

# Edit main .env
nano .env
```

**Main .env configuration:**
```env
N8N_HOST=hook.yourdomain.com
N8N_PROTOCOL=https
N8N_ENCRYPTION_KEY=<generate-with: openssl rand -hex 16>

GROK_API_KEY=<your-grok-api-key>
TELEGRAM_BOT_TOKEN=<your-telegram-bot-token>
TELEGRAM_CHAT_ID=<your-telegram-chat-id>

PUBLIC_API_BASE=https://api.yourdomain.com
```

**Trading Core .env configuration:**
```bash
nano trading-core/.env
```

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

### Step 4: Update Caddyfile with Your Domain

```bash
nano docker/caddy/Caddyfile
```

Replace `yourdomain.com` with your actual domain:

```
{
    email admin@yourdomain.com
}

api.yourdomain.com {
    reverse_proxy trading-core:8000
    
    log {
        output file /var/log/caddy/api.log
    }
}

hook.yourdomain.com {
    reverse_proxy n8n:5678
    
    log {
        output file /var/log/caddy/hook.log
    }
}
```

### Step 5: Start Backend Services

```bash
cd /home/ubuntu/grid-trading-battle

# Build and start all services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f
```

Expected output:
```
NAME                COMMAND                  SERVICE             STATUS              PORTS
grid-caddy          "caddy run --config …"   caddy               running             0.0.0.0:80->80/tcp, 0.0.0.0:443->443/tcp
grid-n8n            "tini -- /docker-ent…"   n8n                 running             0.0.0.0:5678->5678/tcp
grid-postgres       "docker-entrypoint.s…"   postgres            running             0.0.0.0:5432->5432/tcp
grid-redis          "docker-entrypoint.s…"   redis               running             0.0.0.0:6379->6379/tcp
grid-trading-core   "poetry run fastapi …"   trading-core        running             0.0.0.0:8000->8000/tcp
```

### Step 6: Verify Backend Services

```bash
# Test Trading Core health
curl http://localhost:8000/healthz

# Test through Caddy (after DNS propagation)
curl https://api.yourdomain.com/healthz

# Check n8n is accessible
curl http://localhost:5678
```

### Step 7: Configure n8n

1. Open n8n in browser: `https://hook.yourdomain.com`
2. Create admin account (first time only)
3. Import workflows:
   - Go to Workflows → Import from File
   - Import `n8n/workflows/workflow-a-signal-execution.json`
   - Import `n8n/workflows/workflow-b-sync-data.json`
   - Import `n8n/workflows/workflow-c-alerts.json`
4. Configure credentials:
   - Add PostgreSQL credentials (host: postgres, user: tradeuser, password: tradepass, database: trade)
   - Add Telegram credentials (if using alerts)
5. Activate all workflows

### Step 8: Deploy Frontend to Vercel

```bash
cd frontend

# Install dependencies (if not already done)
npm install

# Update .env for production
echo "VITE_API_BASE_URL=https://api.yourdomain.com" > .env

# Build
npm run build

# Deploy to Vercel
# Option 1: Using Vercel CLI
npm install -g vercel
vercel --prod

# Option 2: Manual deployment
# - Go to vercel.com
# - Import project
# - Set environment variable: VITE_API_BASE_URL=https://api.yourdomain.com
# - Deploy
```

### Step 9: Configure Frontend DNS

After Vercel deployment:
1. Get Vercel deployment URL (e.g., `your-project.vercel.app`)
2. Add CNAME record in your DNS:
   - `app.yourdomain.com` → `cname.vercel-dns.com`
3. In Vercel dashboard, add custom domain: `app.yourdomain.com`

### Step 10: Test End-to-End

```bash
# Test grid signal submission
curl -X POST https://hook.yourdomain.com/signal/grid \
  -H "Content-Type: application/json" \
  -d '{
    "model": "chatgpt",
    "strategy": "grid",
    "symbol": "SOLUSDT",
    "lower": 180.0,
    "upper": 210.0,
    "grids": 5,
    "spacing": "arithmetic",
    "base_allocation": 100,
    "leverage": 1,
    "entry_mode": "maker_first",
    "tp_pct": 0.03,
    "sl_pct": 0.05,
    "rebalance": false,
    "notes": "Test signal"
  }'

# Check orders were created
curl https://api.yourdomain.com/orders?model=chatgpt

# Open frontend
# Visit https://app.yourdomain.com
```

## Post-Deployment

### Security Hardening

1. **Firewall Configuration:**
```bash
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

2. **Database Security:**
```bash
# Change default passwords in docker-compose.yml
# Restart services after changing passwords
docker-compose down
docker-compose up -d
```

3. **API Key Rotation:**
- Regularly rotate Aster API keys
- Update .env and restart: `docker-compose restart trading-core`

### Monitoring Setup

1. **View Logs:**
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f trading-core
docker-compose logs -f n8n

# Caddy access logs
docker exec grid-caddy tail -f /var/log/caddy/api.log
```

2. **Database Monitoring:**
```bash
# Connect to database
docker exec -it grid-postgres psql -U tradeuser -d trade

# Check recent orders
SELECT * FROM orders ORDER BY created_at DESC LIMIT 10;

# Check grid configs
SELECT * FROM grid_configs;

# Check metrics
SELECT * FROM metrics ORDER BY ts DESC LIMIT 10;
```

3. **Resource Monitoring:**
```bash
# Container stats
docker stats

# Disk usage
df -h

# Memory usage
free -h
```

### Backup Strategy

1. **Database Backup:**
```bash
# Create backup script
cat > /home/ubuntu/backup.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/home/ubuntu/backups"
mkdir -p $BACKUP_DIR
DATE=$(date +%Y%m%d_%H%M%S)
docker exec grid-postgres pg_dump -U tradeuser trade > $BACKUP_DIR/backup_$DATE.sql
# Keep only last 7 days
find $BACKUP_DIR -name "backup_*.sql" -mtime +7 -delete
EOF

chmod +x /home/ubuntu/backup.sh

# Add to crontab (daily at 2 AM)
(crontab -l 2>/dev/null; echo "0 2 * * * /home/ubuntu/backup.sh") | crontab -
```

2. **Configuration Backup:**
```bash
# Backup .env files and configs
tar -czf config_backup_$(date +%Y%m%d).tar.gz \
  .env \
  trading-core/.env \
  docker-compose.yml \
  docker/caddy/Caddyfile
```

### Troubleshooting

**Problem: Services won't start**
```bash
# Check logs
docker-compose logs

# Check disk space
df -h

# Restart services
docker-compose restart
```

**Problem: Can't connect to API**
```bash
# Check DNS propagation
dig api.yourdomain.com

# Check Caddy logs
docker-compose logs caddy

# Test locally first
curl http://localhost:8000/healthz
```

**Problem: Orders not executing**
```bash
# Check Trading Core logs
docker-compose logs trading-core

# Verify Aster API credentials
# Check balance on Aster exchange
# Verify risk limits in .env
```

**Problem: n8n workflows not triggering**
```bash
# Check n8n logs
docker-compose logs n8n

# Verify webhook URL is accessible
curl https://hook.yourdomain.com

# Check Redis is running
docker-compose ps redis
```

## Maintenance

### Update Services

```bash
cd /home/ubuntu/grid-trading-battle

# Pull latest images
docker-compose pull

# Restart with new images
docker-compose down
docker-compose up -d
```

### Scale Up

When ready to increase allocation:
1. Update `RISK_MAX_SYMBOL_EXPOSURE` in trading-core/.env
2. Update `RISK_MAX_DAILY_LOSS` if needed
3. Restart: `docker-compose restart trading-core`
4. Monitor closely for first 24 hours

### Rollback

If issues occur:
```bash
# Stop services
docker-compose down

# Restore database backup
cat backup_YYYYMMDD_HHMMSS.sql | docker exec -i grid-postgres psql -U tradeuser trade

# Restore config
tar -xzf config_backup_YYYYMMDD.tar.gz

# Restart
docker-compose up -d
```

## Support Checklist

Before asking for help, verify:
- [ ] All services are running: `docker-compose ps`
- [ ] No errors in logs: `docker-compose logs`
- [ ] DNS is propagated: `dig api.yourdomain.com`
- [ ] API credentials are correct
- [ ] Firewall allows ports 80, 443
- [ ] Sufficient disk space: `df -h`
- [ ] Database is accessible
- [ ] Frontend can reach API

## Success Criteria

Your deployment is successful when:
- ✅ All 5 Docker containers are running
- ✅ `https://api.yourdomain.com/healthz` returns `{"status":"ok"}`
- ✅ `https://hook.yourdomain.com` shows n8n interface
- ✅ `https://app.yourdomain.com` shows frontend
- ✅ Test grid signal creates orders in database
- ✅ Frontend displays real-time data
- ✅ Telegram alerts working (if configured)

Congratulations! Your Grid Trading Battle System is now live! 🎉
