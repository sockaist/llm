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


If you want to upsert pdf contents from Google Drive to Qdrant DB, first add columns in drive_list. 
Each row must follow the format: 0000-00-00,https://drive.google.com/file/d/~~~
Then, execute the following line:

```python
python drive2db.py 
```
