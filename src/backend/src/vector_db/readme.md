This folder consists functions for handling Qdrant DB.

Qdrant DB is stored as config.py format currently.

If you are to initialize Qdrant vector DB, do follow:

```python
python vector_db_main.py 
```

It will do:
- Read all folders with names in key of FORMATS of config.py
- Under such folders, parse all json folders
- put the datas in DB with payload as FORMATS


So, you have to keep in mind:


