#!/bin/bash

# Color codes
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 0. Setup Environment
echo -e "${BLUE}[0/3] Setting up environment...${NC}"
mkdir -p logs
echo "Installing dependencies from requirements.txt..."
pip install -r requirements.txt > logs/install.log 2>&1
if [ $? -ne 0 ]; then
    echo -e "${RED}Dependency installation failed. Check logs/install.log${NC}"
    exit 1
fi
echo -e "${GREEN}Dependencies installed.${NC}"

export PYTHONPATH=$PYTHONPATH:$(pwd)/src

echo -e "${BLUE}[1/3] Starting Infrastructure (Redis)...${NC}"
if ! docker info > /dev/null 2>&1; then
  echo "Error: Docker is not running."
  exit 1
fi
docker-compose up -d redis
if [ $? -ne 0 ]; then
    echo "Error starting Redis container."
    exit 1
fi
echo -e "${GREEN}Redis started.${NC}"

echo -e "${BLUE}[2/3] Starting Celery Worker...${NC}"
# Kill existing workers if any (simple approach)
pkill -f "celery worker" || true

# Start Celery in background
# Check OS for Celery Pool settings
OS_NAME=$(uname)
if [ "$OS_NAME" == "Darwin" ]; then
    echo "Running on macOS: Enforcing Celery solo pool (no forking) for ML stability."
    CELERY_POOL_ARGS="--pool=solo"
else
    # Linux/Production: Default prefork (concurrent)
    CELERY_POOL_ARGS=""
fi

nohup celery -A llm_backend.server.vector_server.worker.celery_app worker --loglevel=info $CELERY_POOL_ARGS > logs/celery_worker.log 2>&1 &
CELERY_PID=$!
echo -e "${GREEN}Celery Worker started (PID: $CELERY_PID). Logs: logs/celery_worker.log${NC}"

echo -e "${BLUE}[3/3] Starting API Server...${NC}"
# start.py is in root
python start.py

# Cleanup when API server stops
echo -e "${BLUE}Stopping Celery Worker...${NC}"
kill $CELERY_PID
