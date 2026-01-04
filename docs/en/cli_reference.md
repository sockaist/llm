# CLI Reference (English)

The `vectordb` CLI is a tool for server management and configuration inspection.

## Basic Usage

```bash
python -m vectordb [GROUP] [COMMAND] --option value
```

## 1. Config Group

Manage and inspect configuration.

### `config show`
Outputs the currently loaded configuration in JSON format.

```bash
# Show default (development) config
python -m vectordb config show

# Show production config
python -m vectordb config show --env production
```

## 2. Server Group

Runs the VectorDB server.

### `server start`
Starts the FastAPI server (Uvicorn).

**Options:**
- `--port`: Port number (Default: `server.port` in `defaults.yaml`)
- `--env`: Environment (`development` / `production`)

**Examples:**
```bash
# Dev Mode (Port 8000, Hot Reload)
python -m vectordb server start --env development

# Production Mode (Port 9090, Optimized)
python -m vectordb server start --env production --port 9090
```

> [!IMPORTANT]
> Using `--env production` applies settings from `config/production.yaml` (e.g., Workers=8, Debug=False).
