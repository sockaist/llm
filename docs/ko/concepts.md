# 핵심 개념 (Key Concepts)

VectorDB v2.0의 아키텍처를 이해하기 위한 핵심 개념입니다.

## 1. Universal JSON Handler

VectorDB는 "어떤 JSON이든 던지면 처리한다"는 철학으로 설계되었습니다. 이를 위해 **Universal JSON Handler**가 동작합니다.

### 자동 평탄화 (Auto-Flattening)
Qdrant와 같은 벡터 DB는 깊은 중첩 구조(Deep Nested JSON)를 직접 쿼리하기 어렵습니다. 따라서 Handler가 이를 자동으로 1단계 깊이로 평탄화합니다.

**입력 (Input):**
```json
{
  "product": {
    "name": "Laptop",
    "specs": {
      "cpu": "M1",
      "ram": "16GB"
    }
  },
  "tags": ["apple", "tech"]
}
```

**변환 (Flattened):**
```json
{
  "product_name": "Laptop",
  "product_specs_cpu": "M1",
  "product_specs_ram": "16GB",
  "tags_0": "apple",
  "tags_1": "tech"
}
```

### 텍스트 자동 추출 (Text Extraction)
벡터화를 위해서는 "메인 텍스트"가 필요합니다. Handler는 다음 순서로 텍스트 필드를 자동 탐지합니다:
1.  `title`
2.  `name`
3.  `subject`
4.  `description`
5.  `content`
6.  `message`
7.  `text`
8.  `body`

만약 위 필드가 없다면, 문서 내의 모든 짧은 문자열을 이어 붙여(Concat) 텍스트를 생성합니다.

## 2. Unified Config System

모든 설정은 계층적(Hierarchical)으로 관리됩니다.

1.  **Defaults (`defaults.yaml`)**: 모든 환경의 기본값.
2.  **Environment (`development.yaml` / `production.yaml`)**: 특정 환경에 대한 오버라이드.
3.  **Secrets (`.env`)**: API Key, DB Password 등 민감 정보.
4.  **OS Env Vars**: 컨테이너 환경에서 주입되는 최종 오버라이드 값 (예: `VECTORDB_PORT`).
