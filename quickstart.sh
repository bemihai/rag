#!/bin/bash
# Quick start script for Wine RAG Docker deployment

set -e

echo "🍷 Pour Decisions Wine RAG - Docker Setup"
echo "=========================================="

# Check if .env exists
if [ ! -f .env ]; then
    echo "⚠️  No .env file found. Copying from .env.example..."
    cp .env.example .env
    echo "📝 Please edit .env and add your GOOGLE_API_KEY"
    echo "   Get your key from: https://makersuite.google.com/app/apikey"
    echo ""
    read -p "Press Enter after you've updated .env with your API key..."
fi

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker Desktop and try again."
    exit 1
fi

echo "✅ Docker is running"

# Check if Google API key is set
if grep -q "your_google_api_key_here" .env; then
    echo "❌ Please set your GOOGLE_API_KEY in .env file"
    exit 1
fi

echo "✅ Environment variables configured"

# Build and start services
echo ""
echo "🔨 Building Docker images..."
docker-compose build

echo ""
echo "🚀 Starting services..."
docker-compose up -d

echo ""
echo "⏳ Waiting for services to be healthy..."
sleep 5

# Check ChromaDB health
if docker-compose exec -T chromadb curl -f --max-time 5 http://localhost:8000/api/v1/heartbeat > /dev/null 2>&1; then
    echo "✅ ChromaDB is healthy"
else
    echo "⚠️  ChromaDB may still be starting up..."
fi

echo ""
echo "=========================================="
echo "🎉 Deployment complete!"
echo ""
echo "📍 Access your app at: http://localhost:8501"
echo ""
echo "Useful commands:"
echo "  • View logs:        docker-compose logs -f app"
echo "  • Stop services:    docker-compose down"
echo "  • Restart:          docker-compose restart"
echo "  • View status:      docker-compose ps"
echo ""
echo "📚 See DEPLOYMENT.md for more information"
echo "=========================================="

