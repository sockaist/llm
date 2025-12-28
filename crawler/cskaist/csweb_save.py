# csweb_save.py
"""
◼️ tag 단위로 unique id를 붙이고
◼️ <tag>_<8-digit HEX>.json  파일명을 만들어
◼️ res/ 아래에 저장한다.
"""

import os, re, json
from pathlib import Path
from typing import List, Dict

HEX_WIDTH = 8          # 0x00000001 형식

def _scan_existing(res_dir: Path) -> dict[str, int]:
    """
    이미 저장된 파일을 훑어 tag별 최대 id를 반환
    파일명 패턴: <tag>_<8HEX>.json  (tag에 '.' 포함 허용)
    """
    pat = re.compile(r"^(?P<tag>.+)_([0-9A-F]{%d})\.json$" % HEX_WIDTH, re.I)
    max_ids: dict[str, int] = {}
    for fname in os.listdir(res_dir):
        m = pat.match(fname)
        if not m:
            continue
        tag, id_hex = m.group("tag"), m.group(2)
        max_ids[tag] = max(max_ids.get(tag, 0), int(id_hex, 16))
    return max_ids

def save_items(items: List[Dict], res_dir: str | os.PathLike = "res") -> None:
    """
    items: 크롤러에서 얻은 dict 리스트(각 dict에는 최소 'tag'가 있어야 함)
    res_dir: 결과 저장 폴더
    """
    res_dir = Path(res_dir)
    res_dir.mkdir(parents=True, exist_ok=True)

    max_ids = _scan_existing(res_dir)

    for item in items:
        tag = item.get("tag", "untagged")
        next_id = max_ids.get(tag, 0) + 1
        max_ids[tag] = next_id
        item["id"]  = next_id

        fname = f"{tag}_{next_id:0{HEX_WIDTH}X}.json"
        with open(res_dir / fname, "w", encoding="utf-8") as f:
            json.dump(item, f, ensure_ascii=False, indent=2)

#!/usr/bin/env python3
"""
purge_res.py
────────────
‣ res/ 안의 모든 파일과 하위 디렉터리까지 깔끔하게 삭제
"""

from pathlib import Path
import shutil

RES_DIR = Path("res")          # 필요하면 다른 경로로 변경

def purge(directory: Path = RES_DIR) -> None:
    if not directory.exists():
        print(f"[INFO] {directory} does not exist – nothing to do.")
        return

    for child in directory.iterdir():
        if child.is_file():
            child.unlink()          # 단일 파일 삭제
        else:
            shutil.rmtree(child)    # 하위 디렉터리 재귀 삭제

    print(f"Cleared {directory.resolve()}")

if __name__ == "__main__":
    purge(RES_DIR)
