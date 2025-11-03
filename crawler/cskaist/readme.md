# KAIST CSWEB Crawler
KAIST 전산학부 공식 웹사이트(cs.kaist.ac.kr)로부터 연구‧소식‧구성원 정보를 자동 수집해 `res/` 폴더에 **항목별 JSON** 파일로 저장하는 파이썬 크롤러 모음입니다.
---

## 디렉터리 구조

```text
.
├── crawler_ai.py          # AI‧연구실적 게시판
├── crawler_calendar.py    # 세미나·행사 캘린더
├── crawler_lab.py         # 연구실(Lab) 정보
├── crawler_mem.py         # 행정팀·연구원(Staff)
├── crawler_news.py        # 학부 News
├── crawler_notice.py      # 일반 공지(Notice)
├── crawler_profs.py       # 교수(Professor) 프로필
├── crawler_room.py        # 세미나·강의실 정보
│
├── csweb_save.py          # 공통 저장/삭제 헬퍼 (id 부여, 파일 분리, purge)
├── main.py                # 전체 크롤링 원-스톱 실행 스크립트
└── res/                   # 결과 JSON 파일이 여기에 생성
```

---

## 의존 패키지

* Python ≥ 3.9
* requests
* beautifulsoup4

```bash
pip install requests beautifulsoup4
```

---

## 결과 파일 규칙

| 필드    | 설명                                                   |
| ----- | ---------------------------------------------------- |
| `tag` | 원본 게시판 / 리소스 식별자 (예: `csweb.news`, `csweb.calendar`) |
| `id`  | **같은 `tag` 내부에서 1부터 증가**하는 unsigned int              |
| 그 외   | 크롤러별로 수집한 메타데이터(제목, 날짜, 내용, 링크 …)                    |

저장 형식은 **`<tag>_<8자리 HEX>.json`**  (예: `csweb.news_0000001A.json`).
`id`가 1 → `00000001`, 26 → `0000001A` 같은 식으로 0-pad, 대문자 hex이며, `tag`별로 유일합니다.

---

## How to use

### 1. 기존 데이터 삭제 + 전체 크롤링

```bash
python main.py
```

`main.py` 동작:

1. **`res/` 폴더 비우기** → `csweb_save.purge()`
2. 각 크롤러 실행 → `save_items()`이 자동으로 `id`를 부여하고 파일로 저장
3. 최종 “crawl complete.” 출력

### 2. 특정 크롤러만 실행

```bash
python crawler_news.py          # 뉴스만
python crawler_lab.py           # 연구실 정보만
```

기존 결과와 병합되며, `tag`별 ID는 이어서 증가합니다.

### 3. 결과 전부 삭제

```bash
python -c "from csweb_save import purge; purge()"
# 또는
python csweb_save.py
```

---

## 내부 구조 요약

### `csweb_save.save_items(items, res_dir="res")`

1. `res_dir` 스캔 → `tag`별 최대 id 파악
2. 새 `items`에 `id = max + 1` 부여
3. `<tag>_<HEX>.json` 개별 파일로 덤프
4. 동일 `tag` 재실행 시 ID가 자동 증가 → (tag, id) 조합 유일 보장

### `csweb_save.purge(directory="res")`

`directory` 내부 파일·하위 폴더 전부 삭제.

### 개별 크롤러 패턴

```python
from csweb_save import save_items

def crawl_all():                # 리스트[dict] 생성
    ...

def crawler_news():
    data = crawl_all()
    save_items(data, res_dir="res")
    print(f"{len(data)} items stored in res for csweb.news/")
```

---

## 팁 & 주의

* 서버 부하를 고려해 각 크롤러에는 `sleep()` 지연이 포함돼 있습니다.
  대량 크롤링이 필요하다면 delay를 조절하세요.
* 구조가 바뀌면 **selector** 만 수정하면 됩니다. `save_items()`는 건드릴 필요 없습니다.

---
