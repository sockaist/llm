#!/bin/bash
# Start Production Stack (App + Monitoring)
set -e

# Ensure .env exists
if [ ! -f ".env" ]; then
    echo "Error: .env file not found. Please run ./setup_env.sh first."
    exit 1
fi

echo "Starting VortexDB Production Stack..."
echo " - Application Services: API, Worker, Redis, Qdrant"
echo " - Monitoring Services: Prometheus, Grafana"

# Docker Compose with multiple files
docker-compose -f docker-compose.yml -f docker-compose.monitor.yml up -d --build

echo ""
echo "=========================================="
echo "🚀 Stack Deployed Successfully!"
echo "=========================================="
echo "📝 API Server:    http://localhost:8000"
echo "📊 Grafana:       http://localhost:3000 (admin/admin)"
echo "📈 Prometheus:    http://localhost:9090"
echo "🗄️  Qdrant UI:     http://localhost:6333/dashboard"
echo "=========================================="
echo "To stop: docker-compose -f docker-compose.yml -f docker-compose.monitor.yml down"
