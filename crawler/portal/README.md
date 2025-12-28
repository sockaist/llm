## Seoho Kim made

---
### How to re-use?

- edit ```kaistId``` as your **kaist id**.
- edit ```url``` as url of board what you want to collect.
- edit ```postCount``` as number of post that you want to collect.

```bash
# in root dir
python crawler/portal/main.py --kaistId="YourKaistId" --savePath="data/portal/**" --articleId="articleId"

# Example
python crawler/portal/main.py --kaistId="seohokim" --savePath="data/portal/job" --articleId=33
```