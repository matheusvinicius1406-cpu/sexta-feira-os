#!/bin/bash

# Sexta-Feira OS + Jarvis AI Setup & Run Script
# This script sets up the complete AI assistant platform and launches it

set -e

echo "🚀 Sexta-Feira OS + Jarvis AI System"
echo "=================================="
echo ""

# Check if running in backend-core directory
if [ ! -f "app/main.py" ]; then
    echo "❌ Error: This script must be run from the backend-core directory"
    echo "Run: cd backend-core && bash ../scripts/setup-jarvis.sh"
    exit 1
fi

echo "📦 Step 1: Installing dependencies..."
pip install -q -r requirements.txt
echo "✅ Dependencies installed"
echo ""

echo "🗄️  Step 2: Initializing database..."
python init_db.py
echo "✅ Database initialized"
echo ""

echo "🔑 Step 3: Checking configuration..."
if [ -z "$GEMINI_API_KEY" ]; then
    echo "⚠️  GEMINI_API_KEY not set in environment"
    echo "   Get a free API key from: https://makersuite.google.com/app/apikey"
    echo "   Then set it: export GEMINI_API_KEY=your-key-here"
    echo ""
    echo "   The system will still work with mock AI responses."
fi
echo "✅ Configuration checked"
echo ""

echo "🎯 Step 4: Starting Jarvis AI System..."
echo "=================================="
echo ""
echo "Backend will start on: http://localhost:8000"
echo "API Documentation: http://localhost:8000/docs"
echo "Health Check: http://localhost:8000/api/v1/health"
echo "Jarvis Status: http://localhost:8000/api/v1/jarvis/status"
echo ""
echo "Press CTRL+C to stop"
echo ""

# Start the backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
