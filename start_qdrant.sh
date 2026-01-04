#!/bin/bash
# start_qdrant.sh

# 1. Load Environment Variables
if [ -f .env ]; then
  export $(grep -v '^#' .env | xargs)
else
  echo "[ERROR] .env file not found!"
  exit 1
fi

# 2. Check for functionality
if [ -z "$QDRANT_API_KEY" ]; then
  echo "[ERROR] QDRANT_API_KEY not set in .env"
  exit 1
fi

# 3. Launch Qdrant
echo "[INFO] Starting Qdrant with Secure API Key..."
export QDRANT__SERVICE__API_KEY=$QDRANT_API_KEY
./bin/qdrant
