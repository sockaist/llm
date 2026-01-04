# VectorDB User Guide (English)

VectorDB v2.0 is a developer-friendly **Universal Vector Database Solution**.
It allows you to vectorize and search any JSON data without complex configurations.

## 📚 Table of Contents

1.  [Getting Started](getting_started.md)
    -   Installation & Basic Setup
    -   Running the Server
2.  [Key Concepts](concepts.md)
    -   Universal JSON Handler (Auto-Flattening)
    -   Unified Config System
3.  [Python SDK Reference](sdk_reference.md)
    -   `VectorDBClient` Usage
    -   Sync/Async Clients
    -   Search & Upsert Examples
4.  [CLI Reference](cli_reference.md)
    -   `server start`
    -   `config show`
5.  [Deployment](deployment.md)
    -   Docker / Kubernetes
    -   Production Setup

## [INFO] Quick Start

```bash
# 1. Install
pip install vectordb

# 2. Run Server
python -m vectordb server start --port 8000

# 3. Use in Python
from vectordb.client import VectorDBClient
client = VectorDBClient()
client.search("AI Trends")
```
