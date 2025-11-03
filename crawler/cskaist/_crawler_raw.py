from __future__ import annotations
import json, re, time, urllib.parse as up
from collections import deque
from pathlib import Path

import requests
from bs4 import BeautifulSoup

### ───────────────────────────────
# 0. 전역 설정
BASE_DOMAIN = "cs.kaist.ac.kr"
BASE_URL    = f"https://{BASE_DOMAIN}"
HEADERS     = {
    "User-Agent": "KAIST-CS-crawler/0.1 (+your-email@example.com)"
}
OUT_FILE    = Path("kaist_cs_raw.jsonl")
CRAWL_DELAY = 1.0           # polite delay (sec)
MIN_TOKENS  = 50            # 너무 짧은 페이지 스킵

### ───────────────────────────────
# 1. URL 유틸리티
def normalize_url(url: str, parent: str = BASE_URL) -> str:
    """anchor 제거 + 절대경로화"""
    url = url.split("#")[0]
    return up.urljoin(parent, url)

def is_allowed(url: str) -> bool:
    """같은 도메인 & html 확장자만"""
    parsed = up.urlparse(url)
    if not parsed.netloc.endswith(BASE_DOMAIN):
        return False
    return not re.search(r"\.(zip|pdf|png|jpg|jpeg|gif|svg|mp4)$", parsed.path, re.I)

### ───────────────────────────────
# 2. 본문 추출
REMOVE_TAGS = {"script", "style", "noscript", "header", "footer", "nav", "form"}

def extract_visible_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup.find_all(list(REMOVE_TAGS)):
        tag.decompose()
    text = " ".join(chunk.strip() for chunk in soup.stripped_strings)
    # 공백 normalize
    return re.sub(r"\s+", " ", text)

### ───────────────────────────────
# 3. 메인 크롤러
def crawl(start_url: str = BASE_URL) -> None:
    q      : deque[str] = deque([start_url])
    visited: set[str]   = set()
    with OUT_FILE.open("w", encoding="utf-8") as fp:
        while q:
            url = q.popleft()
            if url in visited:
                continue

            try:
                resp = requests.get(url, headers=HEADERS, timeout=10)
                resp.raise_for_status()
            except requests.RequestException as e:
                print(f"[FAIL] {url} → {e}")
                continue

            visited.add(url)
            text = extract_visible_text(resp.text)
            if len(text.split()) >= MIN_TOKENS:
                # Fine-tuning용 JSONL row
                json.dump(
                    {"prompt": text + "\n\n###\n\n", "completion": ""},
                    fp, ensure_ascii=False
                )
                fp.write("\n")

            # 링크 수집
            soup = BeautifulSoup(resp.text, "html.parser")
            for a in soup.find_all("a", href=True):
                nxt = normalize_url(a["href"], url)
                if is_allowed(nxt) and nxt not in visited:
                    q.append(nxt)

            time.sleep(CRAWL_DELAY)

from csweb_save import save_items
def crawler_ai():
    data = crawl_all()
    save_items(data, res_dir="res")
    print(f"{len(data)} items stored in res for csweb.ai/")

if __name__ == "__main__":
    crawler_ai()