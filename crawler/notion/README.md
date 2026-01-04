# 📄 Notion Data Parser

Notion에서 가져온 게시글 데이터를 구조화하여 저장하고 활용하는 프로젝트입니다.

---

## [INFO] 실행 방법

```bash
python main.py
```

## 📁 데이터 구조
프로그램을 실행하면 notion_data/ 폴더에 다음과 같은 구조로 데이터가 저장됩니다:
```bash
notion_data/
├── marketing/            # 외부 홍보글 개별 데이터
│   ├── post_0.json
│   ├── post_1.json
│   └── ...
├── notice/               # 공지글 개별 데이터
│   ├── post_0.json
│   ├── post_1.json
│   └── ...
├── marketing.json        # marketing 요약 정보
└── notice.json           # notice 요약 정보
```

## 📄 파일 설명
### 📌 marketing.json
- marketing/ 폴더의 홍보글들을 요약한 정보입니다.
- 리스트 형태로, 각 요소는 아래와 같은 형식의 딕셔너리입니다:

```json
[
  {
    "id": 0,
    "url": "https://www.notion.so/kaist-cs/marketing0",
    "title": "홍보글 제목1"
  },
  {
    "id": 1,
    "url": "https://www.notion.so/kaist-cs/marketing1",
    "title": "홍보글 제목2"
  }
]

```

### 📌 notice.json
- notice/ 폴더의 공지글들을 요약한 정보입니다.
- 형식은 marketing.json과 동일합니다:

```json
[
  {
    "id": 0,
    "url": "https://www.notion.so/kaist-cs/notice0",
    "title": "공지 제목1"
  },
  {
    "id": 1,
    "url": "https://www.notion.so/kaist-cs/notice1",
    "title": "공지 제목2"
  }
]

```


### 📌 marketing/post_i.json & notice/post_i.json
- 각 게시글의 상세 정보를 담고 있는 JSON 파일입니다.
- i는 해당 글의 고유 ID입니다.
- 파일 구조는 다음과 같습니다:

```json
{
  "title": "글 제목",
  "start": "2024년 05월 01일",             // 공지 시작일
  "finish": "2024년 05월 10일",            // 공지 종료일
  "contents": "본문 내용입니다.",
  "images": [
    "https://kaist-cs.notion.site/image/image1",
    "https://kaist-cs.notion.site/image/image2"
  ],
  "url": "https://www.notion.so/kaist-cs/post0"
}

```