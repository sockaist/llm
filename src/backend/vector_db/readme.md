This folder consists functions for handling PostgreSQL + pgvector.

Set PostgreSQL/OpenAI envs first:

```bash
export OPENAI_API_KEY=...
export POSTGRES_DSN="host=localhost port=5432 dbname=postgres user=postgres password=..."
```

Also make sure pgvector extension is available in your DB:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

If you are to initialize vector DB, do:

```python
python vector_db_main.py 
```

It will do:
- Read all folders with names in key of FORMATS of config.py
- Under such folders, parse all json files
- Embed with OpenAI embedding model
- Insert chunked rows into PostgreSQL table (`documents` by default)


If you want to upsert pdf contents from Google Drive, first add columns in drive_list.
Each row must follow the format: 0000-00-00,https://drive.google.com/file/d/~~~
Then, execute the following line:

```python
python drive2db.py 
```
