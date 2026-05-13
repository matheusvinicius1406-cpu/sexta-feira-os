#!/bin/bash
# Stop development environment

echo "⏹️  Stopping Sexta-Feira OS Development Environment..."

docker-compose down

echo "✅ Development environment stopped"
echo ""
echo "To view logs: docker-compose logs -f"
echo "To restart: bash scripts/start-dev.sh"
