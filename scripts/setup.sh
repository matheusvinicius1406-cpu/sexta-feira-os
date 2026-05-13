#!/bin/bash
# Setup script for local development

set -e

echo "🚀 Setting up Sexta-Feira OS..."

# Backend setup
echo "📦 Setting up backend..."
cd backend-core
python3 -m venv venv
source venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt

echo "✅ Backend dependencies installed"

# Create data directory
mkdir -p data/media
echo "✅ Data directories created"

# Android setup
echo "📱 Android project is ready in mobile-android/"
echo "   Open mobile-android/ in Android Studio to build"

echo ""
echo "🎉 Setup complete!"
echo ""
echo "Next steps:"
echo "1. Create .env file: cp .env.example .env"
echo "2. Edit .env with your configuration"
echo "3. Start backend: cd backend-core && source venv/bin/activate && uvicorn app.main:app --reload"
echo "4. Or use Docker: docker-compose up -d"
echo ""
echo "📚 Documentation:"
echo "   - Setup guide: docs/setup.md"
echo "   - Architecture: docs/architecture.md"
echo "   - API docs: docs/api.md"
echo "   - Vision: docs/vision.md"
