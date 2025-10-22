#!/bin/bash

echo "=========================================="
echo "Grid Trading Battle System - Quick Start"
echo "=========================================="
echo ""

if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    echo "   Run: curl -fsSL https://get.docker.com -o get-docker.sh && sudo sh get-docker.sh"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    echo "   Run: sudo apt install docker-compose -y"
    exit 1
fi

echo "✅ Docker and Docker Compose are installed"
echo ""

if [ ! -f .env ]; then
    echo "⚠️  Main .env file not found. Creating from template..."
    cp .env.example .env
    echo "   Please edit .env with your configuration"
fi

if [ ! -f trading-core/.env ]; then
    echo "⚠️  trading-core/.env file not found. Creating from template..."
    cp trading-core/.env.example trading-core/.env
    echo "   Please edit trading-core/.env with your Aster API credentials"
fi

echo ""
echo "Checking configuration..."
echo ""

if grep -q "your_aster_api_key_here" trading-core/.env; then
    echo "⚠️  WARNING: Aster API credentials not configured in trading-core/.env"
    echo "   Please update ASTER_API_KEY and ASTER_API_SECRET"
    echo ""
fi

if grep -q "yourdomain.com" docker/caddy/Caddyfile; then
    echo "⚠️  WARNING: Domain not configured in docker/caddy/Caddyfile"
    echo "   Please replace yourdomain.com with your actual domain"
    echo ""
fi

echo "Starting services..."
echo ""

docker-compose up -d

echo ""
echo "Waiting for services to start..."
sleep 10

echo ""
echo "Service Status:"
echo "=========================================="
docker-compose ps

echo ""
echo "Testing services..."
echo ""

if curl -s http://localhost:8000/healthz | grep -q "ok"; then
    echo "✅ Trading Core is running"
else
    echo "❌ Trading Core is not responding"
fi

if curl -s http://localhost:5678 > /dev/null 2>&1; then
    echo "✅ n8n is running"
else
    echo "❌ n8n is not responding"
fi

if docker exec grid-postgres pg_isready -U tradeuser > /dev/null 2>&1; then
    echo "✅ PostgreSQL is running"
else
    echo "❌ PostgreSQL is not responding"
fi

if docker exec grid-redis redis-cli ping | grep -q "PONG"; then
    echo "✅ Redis is running"
else
    echo "❌ Redis is not responding"
fi

echo ""
echo "=========================================="
echo "Next Steps:"
echo "=========================================="
echo ""
echo "1. Configure your environment:"
echo "   - Edit .env with your domain and API keys"
echo "   - Edit trading-core/.env with Aster credentials"
echo "   - Edit docker/caddy/Caddyfile with your domain"
echo ""
echo "2. Restart services after configuration:"
echo "   docker-compose restart"
echo ""
echo "3. Access services:"
echo "   - Trading Core API: http://localhost:8000"
echo "   - n8n Interface: http://localhost:5678"
echo "   - Frontend: Deploy to Vercel (see DEPLOYMENT.md)"
echo ""
echo "4. Import n8n workflows:"
echo "   - Open http://localhost:5678"
echo "   - Import workflows from n8n/workflows/"
echo ""
echo "5. Test the system:"
echo "   - See README.md for testing instructions"
echo "   - Run tests: cd tests && python test_idempotency.py"
echo ""
echo "For detailed deployment guide, see DEPLOYMENT.md"
echo ""
