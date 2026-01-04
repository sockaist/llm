#!/bin/bash

echo ">>> Starting VortexDB System Stack..."

# 1. Check/Start Qdrant
if pgrep -x "qdrant" > /dev/null; then
    echo "[OK] Qdrant is already running."
else
    echo "[INFO] Starting Qdrant..."
    ./start_qdrant.sh > qdrant.log 2>&1 &
    sleep 5
fi

# 2. Check/Start Redis
if lsof -i :6379 > /dev/null; then
    echo "[OK] Redis is already running."
else
    echo "[INFO] Starting Redis..."
    # Assuming redis-server is in path or brew service
    redis-server --daemonize yes
    sleep 2
fi

# 3. Start Celery Worker
echo "[INFO] Starting Celery Worker..."
# Kill existing worker if any
pkill -f "celery -A" || true
export PYTHONPATH=.:src
nohup celery -A src.llm_backend.server.vector_server.worker.celery_app.celery_app worker --loglevel=info > celery.log 2>&1 < /dev/null &
sleep 2

# 4. Start Vector Server
echo "[INFO] Starting VortexDB Server..."
# Kill existing server if any
pkill -f "python start.py" || true
export POOL_SIZE=1 
nohup python start.py > vortex_server.log 2>&1 < /dev/null &

echo "[WAIT] Waiting for server to bind port 8000..."
max_retries=60
for i in $(seq 1 $max_retries); do
    if lsof -i :8000 > /dev/null; then
        echo "[OK] VortexDB Server is READY!"
        echo "   > Logs: vortex_server.log"
        echo "   > API: http://localhost:8000"
        exit 0
    fi
    sleep 1
    echo -n "."
done

echo "[ERROR] Server failed to start in 60 seconds. Check vortex_server.log"
