# DB Rebuild Scripts

`rebuild.sh` rebuilds ontology hierarchy from `llm/data` using folder structure only.

## What `rebuild.sh` does

1. Scans all directories under `llm/data`
2. For JSON docs with empty `content`/`contents`/`etc`, auto-builds `content` by joining textual fields with `\n`
3. Upserts parent-child hierarchy into RDB table `ontology_entities`
4. Regenerates `llm/data/ontology.md`, `llm/data/level0.md`, and `llm/data/**/entity.json`

`relations` / `relation_types` are not used by this rebuild flow.

## Run

```bash
./DB/rebuild.sh
```

Optional:

```bash
./DB/rebuild.sh --no-reset
```

## Vector Rebuild (separate)

To (re)fill pgvector rows from `llm/data` with `entity_id` metadata:

```bash
python DB/rebuild_vectors_from_data.py
```

Optional:

```bash
python DB/rebuild_vectors_from_data.py --force-reembed-all
python DB/rebuild_vectors_from_data.py --no-cleanup-stale
```

## Course entity generation (separate)

If you need to create course folders from seed SQL:

```bash
python DB/generate_course_entities.py
```

This is intentionally not part of `rebuild.sh`.
