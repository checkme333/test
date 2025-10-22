# Project Structure

Complete file structure of the Grid Trading Battle System.

```
grid-trading-battle/
├── README.md                          # Main documentation
├── DEPLOYMENT.md                      # Deployment guide
├── PROJECT_STRUCTURE.md              # This file
├── docker-compose.yml                # Docker orchestration
├── start.sh                          # Quick start script
├── .env.example                      # Environment template
├── .env                              # Environment config (create from .env.example)
│
├── docker/                           # Docker configurations
│   ├── caddy/
│   │   └── Caddyfile                # Reverse proxy config
│   ├── postgres/
│   │   └── init.sql                 # Database initialization
│   └── n8n/
│
├── trading-core/                     # FastAPI backend
│   ├── Dockerfile                   # Container definition
│   ├── README.md                    # Trading Core docs
│   ├── pyproject.toml              # Python dependencies
│   ├── poetry.lock                 # Locked dependencies
│   ├── .env.example                # Environment template
│   ├── .env                        # Environment config (create from .env.example)
│   │
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                 # FastAPI application & routes
│   │   ├── config.py               # Configuration management
│   │   ├── models.py               # Pydantic models
│   │   ├── database.py             # PostgreSQL operations
│   │   ├── aster_client.py         # Aster API integration
│   │   └── grid_engine.py          # Grid trading logic
│   │
│   └── tests/
│       └── __init__.py
│
├── n8n/                             # n8n workflow orchestration
│   └── workflows/
│       ├── workflow-a-signal-execution.json    # Grid signal processing
│       ├── workflow-b-sync-data.json           # Data synchronization
│       └── workflow-c-alerts.json              # Risk monitoring & alerts
│
├── frontend/                        # Next.js/React frontend
│   ├── README.md
│   ├── package.json                # Node dependencies
│   ├── package-lock.json
│   ├── tsconfig.json               # TypeScript config
│   ├── vite.config.ts              # Vite config
│   ├── tailwind.config.js          # Tailwind CSS config
│   ├── components.json             # shadcn/ui config
│   ├── .env.example                # Environment template
│   ├── .env                        # Environment config (create from .env.example)
│   │
│   ├── src/
│   │   ├── main.tsx                # Entry point
│   │   ├── App.tsx                 # Main application component
│   │   ├── App.css
│   │   ├── index.css
│   │   │
│   │   ├── components/
│   │   │   └── ui/                 # shadcn/ui components
│   │   │       ├── alert.tsx
│   │   │       ├── badge.tsx
│   │   │       ├── button.tsx
│   │   │       ├── card.tsx
│   │   │       ├── tabs.tsx
│   │   │       └── ... (50+ components)
│   │   │
│   │   └── hooks/
│   │       └── use-mobile.tsx
│   │
│   ├── public/
│   └── dist/                       # Build output (generated)
│
└── tests/                          # Integration tests
    ├── test_idempotency.py        # Idempotency tests
    ├── test_risk_controls.py      # Risk management tests
    └── test_503_handling.py       # Error handling tests
```

## Key Files Description

### Root Level

- **README.md**: Complete project documentation, API reference, usage guide
- **DEPLOYMENT.md**: Step-by-step deployment instructions
- **docker-compose.yml**: Orchestrates all services (postgres, redis, n8n, trading-core, caddy)
- **start.sh**: Quick start script for local development
- **.env**: Main environment configuration (domain, n8n, telegram)

### Trading Core (Backend)

- **app/main.py**: FastAPI application with all REST endpoints
  - `/grid/apply` - Apply grid strategy
  - `/grid/status` - Get grid status
  - `/grid/pause` - Pause grid
  - `/grid/resume` - Resume grid
  - `/orders` - Get orders
  - `/positions` - Get positions
  - `/pnl` - Get PnL metrics
  - `/account` - Get account info
  - `/balance` - Get balance
  - `/healthz` - Health check

- **app/aster_client.py**: Aster API integration
  - Order placement with idempotency
  - 503/5xx error handling
  - Order confirmation
  - Position management
  - Account queries

- **app/grid_engine.py**: Grid trading logic
  - Grid level calculation (arithmetic/geometric)
  - Order placement and management
  - Risk limit enforcement
  - Idempotent client order ID generation

- **app/database.py**: PostgreSQL operations
  - Grid configuration management
  - Order tracking
  - Metrics storage
  - Level state management

- **app/models.py**: Pydantic models for type safety
  - GridSignal
  - OrderRequest
  - Position
  - Order
  - GridConfig
  - GridLevel
  - PnLMetrics

- **app/config.py**: Configuration management
  - Environment variable loading
  - Risk limits
  - API credentials

### n8n Workflows

- **workflow-a-signal-execution.json**: 
  - Receives grid signals via webhook
  - Validates and rate limits (60s per model/symbol)
  - Calls Trading Core to execute
  - Sends success/error notifications

- **workflow-b-sync-data.json**:
  - Runs every 5 seconds
  - Fetches positions, orders, PnL
  - Writes snapshots to database
  - Enables real-time frontend updates

- **workflow-c-alerts.json**:
  - Monitors risk thresholds every 10 seconds
  - Checks daily loss, exposure, drawdown
  - Triggers circuit breaker on critical alerts
  - Sends Telegram notifications

### Frontend

- **src/App.tsx**: Main application
  - Model comparison cards (ChatGPT vs Grok)
  - Performance metrics display
  - Order flow table
  - Grid status monitoring
  - Real-time data updates (5s polling)

- **src/components/ui/**: shadcn/ui components
  - Pre-built, accessible UI components
  - Tailwind CSS styling
  - TypeScript support

### Tests

- **test_idempotency.py**: 
  - Tests duplicate signal handling
  - Verifies client order ID uniqueness
  - Ensures no duplicate orders

- **test_risk_controls.py**:
  - Tests leverage limits
  - Tests exposure limits
  - Tests valid grid acceptance
  - Tests pause/resume functionality

- **test_503_handling.py**:
  - Verifies 503 error handling implementation
  - Tests order confirmation flow
  - Validates idempotency key generation
  - Checks retry safety

## Database Schema

### grid_configs
- Stores grid configuration for each model/symbol pair
- Fields: model, symbol, lower, upper, grids, spacing, leverage, etc.
- Unique constraint on (model, symbol)

### grid_levels
- Stores individual grid levels and their state
- Fields: config_id, level_idx, price, side, qty, client_order_id, state
- Unique constraint on client_order_id

### orders
- Stores all orders with execution details
- Fields: model, symbol, client_order_id, exchange_order_id, side, price, qty, fill_qty, status, fee, pnl
- Unique constraint on client_order_id

### metrics
- Stores performance metrics snapshots
- Fields: ts, model, symbol, pnl, daily_pnl, win_rate, max_drawdown, exposure
- Primary key: (ts, model, symbol)

## Service Ports

- **Trading Core**: 8000 (internal), 443 (external via Caddy)
- **n8n**: 5678 (internal), 443 (external via Caddy)
- **PostgreSQL**: 5432 (internal only)
- **Redis**: 6379 (internal only)
- **Caddy**: 80, 443 (external)
- **Frontend**: Deployed to Vercel (CDN)

## Data Flow

1. **Signal Reception**:
   - ChatGPT/Grok → Webhook (n8n) → Trading Core → Aster API

2. **Order Execution**:
   - Trading Core → Aster API → Order Confirmation → Database

3. **Data Sync**:
   - n8n (every 5s) → Trading Core → Database → Frontend

4. **Risk Monitoring**:
   - n8n (every 10s) → Check Metrics → Alert if threshold exceeded → Telegram

5. **Frontend Display**:
   - Frontend (every 5s) → Trading Core API → Display metrics/orders

## Environment Variables

### Main .env
```
N8N_HOST=hook.yourdomain.com
N8N_PROTOCOL=https
N8N_ENCRYPTION_KEY=<random-32-chars>
GROK_API_KEY=<grok-key>
TELEGRAM_BOT_TOKEN=<telegram-token>
TELEGRAM_CHAT_ID=<telegram-chat-id>
PUBLIC_API_BASE=https://api.yourdomain.com
```

### trading-core/.env
```
ASTER_API_KEY=<aster-key>
ASTER_API_SECRET=<aster-secret>
ASTER_BASE_URL=https://fapi.asterdex.com
RISK_MAX_LEVERAGE=2
RISK_MAX_DAILY_LOSS=-200
RISK_MAX_SYMBOL_EXPOSURE=5000
SLIPPAGE_BPS=10
REDIS_URL=redis://redis:6379
DATABASE_URL=postgresql://tradeuser:tradepass@postgres:5432/trade
TELEGRAM_BOT_TOKEN=<telegram-token>
TELEGRAM_CHAT_ID=<telegram-chat-id>
```

### frontend/.env
```
VITE_API_BASE_URL=https://api.yourdomain.com
```

## Dependencies

### Trading Core (Python)
- fastapi[standard] - Web framework
- psycopg[binary] - PostgreSQL driver
- redis - Redis client
- httpx - HTTP client for Aster API
- pydantic-settings - Configuration management
- python-dotenv - Environment variable loading

### Frontend (Node.js)
- react - UI library
- typescript - Type safety
- vite - Build tool
- tailwindcss - CSS framework
- shadcn/ui - UI components
- recharts - Charting library
- lucide-react - Icons

### Infrastructure
- PostgreSQL 16 - Database
- Redis 7 - Queue and cache
- n8n - Workflow automation
- Caddy 2 - Reverse proxy with auto HTTPS

## Security Considerations

1. **API Keys**: Stored in .env files, never committed to git
2. **Database**: Strong passwords, internal network only
3. **HTTPS**: Automatic SSL via Caddy
4. **Rate Limiting**: 60s cooldown per model/symbol in n8n
5. **Risk Controls**: Hard limits on leverage, exposure, daily loss
6. **Idempotency**: Prevents duplicate orders
7. **Error Handling**: 503/5xx errors handled with order confirmation

## Deployment Checklist

- [ ] Configure DNS (api, hook, app subdomains)
- [ ] Set up VPS with Docker
- [ ] Configure .env files
- [ ] Update Caddyfile with domain
- [ ] Start backend services
- [ ] Import n8n workflows
- [ ] Deploy frontend to Vercel
- [ ] Test end-to-end
- [ ] Set up monitoring
- [ ] Configure backups

## Maintenance

- **Logs**: `docker-compose logs -f`
- **Backup**: Daily database dumps via cron
- **Updates**: `docker-compose pull && docker-compose up -d`
- **Monitoring**: Check logs, database, metrics regularly
- **Scaling**: Adjust risk limits in .env as needed

---

For detailed instructions, see README.md and DEPLOYMENT.md
