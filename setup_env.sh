#!/bin/bash
# Setup .env file for VectorDB

BASE_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$BASE_DIR"
ENV_EXAMPLE="$PROJECT_ROOT/.env.example"
ENV_FILE="$PROJECT_ROOT/.env"

if [ -f "$ENV_FILE" ]; then
    read -p ".env file already exists. Overwrite? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Aborted."
        exit 1
    fi
fi

if [ ! -f "$ENV_EXAMPLE" ]; then
    echo "Error: .env.example not found at $ENV_EXAMPLE"
    exit 1
fi

echo "Creating .env from .env.example..."
cp "$ENV_EXAMPLE" "$ENV_FILE"

# Generate Secrets
echo "Generating secure keys..."
VECTOR_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(48))")
LOG_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(48))")

# Replace in .env
# We use perl for cross-platform compatibility (sed differences on Mac vs Linux) or python
# Let's use simple sed, assuming Mac/Linux standard
# Mac sed requires '' extension for -i
if [[ "$OSTYPE" == "darwin"* ]]; then
    SED_CMD="sed -i ''"
else
    SED_CMD="sed -i"
fi

# Replace placeholder values
# Matches "VECTOR_API_KEY=dev-key-please-change"
$SED_CMD "s/VECTOR_API_KEY=dev-key-please-change/VECTOR_API_KEY=$VECTOR_KEY/" "$ENV_FILE"
$SED_CMD "s/LOG_KEY=change-this-secret-log-key/LOG_KEY=$LOG_KEY/" "$ENV_FILE"

echo "Success! .env file created with new secure keys."
echo "VECTOR_API_KEY=$VECTOR_KEY"
echo "LOG_KEY=$LOG_KEY"
