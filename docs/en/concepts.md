# Key Concepts

Understanding the core architecture of VectorDB v2.0.

## 1. Universal JSON Handler

VectorDB follows the philosophy: "Throw any JSON at it, and it works."

### Auto-Flattening
Since Vector DBs like Qdrant struggle with deep nested queries, the Handler automatically flattens structures to depth 1.

**Input:**
```json
{
  "user": {
    "profile": {
      "name": "Alice"
    }
  }
}
```

**Flattened:**
```json
{
  "user_profile_name": "Alice"
}
```

### Text Extraction Strategy
To generate embeddings, we need "Main Text". The Handler auto-detects it in this priority:
`title` > `name` > `description` > `content` > `text` > `body`.

If none are found, it concatenates all string values in the document.

## 2. Unified Config System

Configuration is managed hierarchically:

1.  **Defaults (`defaults.yaml`)**: Base settings.
2.  **Environment (`production.yaml`)**: Per-env overrides.
3.  **Secrets (`.env`)**: Sensitive keys.
4.  **OS Env Vars**: Final runtime overrides (e.g. Docker injects).
