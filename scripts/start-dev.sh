#!/bin/bash
# Start development environment

echo "🚀 Starting Sexta-Feira OS Development Environment..."

# Check if .env exists
if [ ! -f .env ]; then
    echo "❌ .env file not found. Please copy from .env.example"
    echo "   cp .env.example .env"
    exit 1
fi

# Start Docker services
echo "🐳 Starting Docker services..."
docker-compose up -d

# Wait for services
echo "⏳ Waiting for services to be ready..."
sleep 5

# Check health
echo "🏥 Checking backend health..."
curl -s http://localhost:8000/api/v1/health | jq .

echo ""
echo "✅ Development environment is ready!"
echo ""
echo "Services:"
echo "  Backend API: http://localhost:8000"
echo "  API Docs: http://localhost:8000/docs"
echo "  PostgreSQL: localhost:5432"
echo "  Redis: localhost:6379"
echo ""
echo "To stop: docker-compose down"
