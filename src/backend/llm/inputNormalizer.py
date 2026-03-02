"""
OpenAI 기반 입력 정규화 + 검색 키워드 추출 모듈.

프롬프트와 few-shot 예시는 이 파일 상단에 고정해 두어,
정규화 정책을 한눈에 확인/수정할 수 있도록 구성했다.
"""

import json
import os
import re
import traceback
from typing import Any, Dict, List, Optional

import openai
from .config import soc_words_json


NORMALIZER_SYSTEM_PROMPT = """
당신은 KAIST 전산학부 챗봇의 입력 정규화기입니다.

역할:
1) 사용자의 문장을 의미는 유지한 채 앞으로 검색 및 질문으로써 이해할 수 있는 자연스럽고 명확한 한국어로 정규화한다.
2) 벡터 검색에 사용할 핵심 키워드 1~5개를 추출한다.

규칙:
- 반드시 JSON으로만 답한다.
- output은 질문의 의도를 바꾸지 않되, 더 명확하고 자연스러운 문장으로 표현한다.- output은 답변 문장이 아니라 정규화된 사용자 질문 문장이어야 한다.
- keywords는 문자열 배열이어야 하며, 중복 없이 핵심 표현만 넣는다.
- keywords는 벡터 검색을 위한 검색어이므로, 질문과 직접적으로 관련된 단어나 구를 포함한다.
- 이때, 질문에서 요구되는 시간 범위 (최근, 요즘, 이번 학기 등)의 표현은 따로 필터링이 이루어지므로 keywords에 포함하지 않는다.
- 만약 질문에 줄임말, 은어 등이 포함되어 있다면 아래의 참고 자료를 활용하여 은어를 정규 표현으로 고치고, 정규화된 표현과 핵심 키워드를 도출한다.
- 참고 자료의 word가 입력에 등장하면, 해당 meaning(정규 표현)을 output 또는 keywords에 반드시 반영한다.
- 또한, keyword가 질문의 일부 정보만 담은 짧은 단어이거나 일반적인 단어("수업", "행사") 등인 경우 관련없는 정보가 검색될 수 있으므로, 가능하면 질문의 의도를 잘 드러내는 구체적인 표현을 keywords에 포함한다.
 
참고 자료:
주어진 입력에서 사용된 단어들의 뜻 또는 유의어는 다음과 같다.
__REFERENCE_WORDS__

응답 형식:
{
  "output": "",
  "keywords": []
}
""".strip()

# 예시는 최소/핵심만 유지한다.
FEW_SHOT_EXAMPLES: List[Dict[str, Any]] = [
    {
        "input": "시프 플젝 언제까지야?",
        "output": "시스템 프로그래밍 프로젝트는 언제까지인가요?",
        "keywords": ["시스템 프로그래밍 프로젝트", "시스템 프로그래밍 프로젝트 기한"],
    },
    {
        "input": "최근 3개월 전산학부 행사 알려줘",
        "output": "최근 3개월 전산학부 행사 알려주세요.",
        "keywords": ["전산학부 행사"],
    },
    {
        "input": "허아키 시험범위 궁금해",
        "output": "허 교수님의 전산기조직 시험 범위가 궁금합니다.",
        "keywords": ["허 교수 전산기조직", "전산기조직 시험 범위"],
    },
]


class OpenAIInputNormalizer:
    """OpenAI API를 사용한 입력 정규화 클래스"""

    def __init__(self, api_key: str, model: str = "gpt-4o-mini", config_path: str = None):
        """
        Args:
            api_key: OpenAI API 키
            model: 사용할 모델
            config_path: 하위 호환용 파라미터(현재 사용하지 않음)
        """
        self.client = openai.OpenAI(api_key=api_key)
        self.model = model
        self.system_prompt_template = NORMALIZER_SYSTEM_PROMPT
        self.examples = FEW_SHOT_EXAMPLES
        self.source_words = self._load_source_words()

    @staticmethod
    def _load_source_words() -> List[Dict[str, Any]]:
        try:
            loaded = json.loads(soc_words_json)
            return loaded if isinstance(loaded, list) else []
        except Exception:
            return []

    @staticmethod
    def _canonical_from_meaning(meaning: Any) -> str:
        if not isinstance(meaning, str):
            return ""
        text = " ".join(meaning.split()).strip()
        if not text:
            return ""
        text = re.split(r"\s*[,，]", text, maxsplit=1)[0]
        text = re.split(r"\s*\(", text, maxsplit=1)[0]
        return text.strip()

    @staticmethod
    def _alias_in_text(text: str, alias: str) -> bool:
        if not alias:
            return False
        if re.search(r"[A-Za-z0-9]", alias):
            pattern = rf"(?<![A-Za-z0-9가-힣]){re.escape(alias)}(?![A-Za-z0-9가-힣])"
            return re.search(pattern, text or "", flags=re.IGNORECASE) is not None
        return alias in (text or "")

    def _replace_alias_with_canonical(self, text: str, alias: str, canonical: str) -> str:
        if not alias or not canonical:
            return text
        replacement = f"{canonical}({alias})"
        if re.search(r"[A-Za-z0-9]", alias):
            pattern = rf"(?<![A-Za-z0-9가-힣]){re.escape(alias)}(?![A-Za-z0-9가-힣])"
            return re.sub(pattern, replacement, text, flags=re.IGNORECASE)
        return text.replace(alias, replacement)

    def _collect_matched_aliases(self, user_message: str) -> List[Dict[str, str]]:
        text = user_message or ""
        matched: List[Dict[str, str]] = []
        seen: set[str] = set()

        for entry in self.source_words:
            word = entry.get("word", "")
            if not isinstance(word, str):
                continue
            alias = word.strip()
            if not alias:
                continue

            if not self._alias_in_text(text, alias):
                continue

            meaning = str(entry.get("meaning", "")).strip()
            canonical = self._canonical_from_meaning(meaning)
            dedupe_key = f"{alias.lower()}::{canonical}"
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            matched.append(
                {
                    "word": alias,
                    "meaning": meaning,
                    "canonical": canonical,
                }
            )
        return matched

    def _extract_reference_words(self, user_message: str) -> str:
        used_words = self._collect_matched_aliases(user_message)
        return json.dumps(used_words, ensure_ascii=False, indent=2)

    def _build_system_prompt(self, user_message: str) -> str:
        reference_words = self._extract_reference_words(user_message)
        return self.system_prompt_template.replace("__REFERENCE_WORDS__", reference_words)

    @staticmethod
    def _sanitize_keywords(raw_keywords: Any, max_keywords: int = 5) -> List[str]:
        if not isinstance(raw_keywords, list):
            return []

        deduped: List[str] = []
        for keyword in raw_keywords:
            if not isinstance(keyword, str):
                continue
            cleaned = " ".join(keyword.split()).strip()
            if len(cleaned) < 2:
                continue
            if cleaned in deduped:
                continue
            deduped.append(cleaned)
            if len(deduped) >= max_keywords:
                break
        return deduped

    @staticmethod
    def _fallback_keywords(text: str, max_keywords: int = 3) -> List[str]:
        stopwords = {
            "전산학부", "학교", "관련", "정보", "질문", "문의", "사항",
            "알려줘", "알려주세요", "궁금해", "궁금합니다", "해주세요", "해줘",
            "무엇", "뭐", "뭐야", "어떻게", "이번", "최근", "최신",
        }
        tokens = re.findall(r"[A-Za-z0-9가-힣]+", text or "")
        keywords: List[str] = []
        for token in tokens:
            token = token.strip()
            if len(token) < 2:
                continue
            if token in stopwords:
                continue
            if token in keywords:
                continue
            keywords.append(token)
            if len(keywords) >= max_keywords:
                break
        return keywords

    @staticmethod
    def _looks_like_answer(output: str) -> bool:
        answer_markers = [
            "확인할 수 없습니다",
            "알 수 없습니다",
            "죄송",
            "도움이 되",
            "확인해보시기 바랍니다",
            "공식 웹사이트",
            "공지사항을 통해",
        ]
        return any(marker in (output or "") for marker in answer_markers)

    def _apply_alias_rewrites(
        self,
        normalized_output: str,
        original_message: str,
        matched_aliases: Optional[List[Dict[str, str]]] = None,
    ) -> str:
        rewritten = (normalized_output or "").strip()
        for alias_info in (matched_aliases or []):
            alias = alias_info.get("word", "").strip()
            canonical = alias_info.get("canonical", "").strip()
            if not alias or not canonical:
                continue
            if canonical in rewritten:
                continue
            if self._alias_in_text(rewritten, alias):
                rewritten = self._replace_alias_with_canonical(rewritten, alias, canonical)
                continue
            if self._alias_in_text(original_message, alias):
                rewritten = f"{rewritten} ({alias}는 {canonical} 과목 의미)"
        return rewritten

    def _enforce_alias_keywords(
        self,
        keywords: List[str],
        normalized_output: str,
        matched_aliases: Optional[List[Dict[str, str]]] = None,
        max_keywords: int = 5,
    ) -> List[str]:
        priority_keywords: List[str] = []
        include_class_suffix = ("수업" in normalized_output) or ("과목" in normalized_output)
        for alias_info in (matched_aliases or []):
            alias = alias_info.get("word", "").strip()
            canonical = alias_info.get("canonical", "").strip()
            if not canonical:
                continue
            priority_keywords.append(canonical)
            if include_class_suffix:
                priority_keywords.append(f"{canonical} 수업")
            if alias:
                priority_keywords.append(f"{canonical} {alias}")

        merged = priority_keywords + list(keywords)
        return self._sanitize_keywords(merged, max_keywords=max_keywords)

    def _normalize_result_shape(
        self,
        result: Dict[str, Any],
        original_message: str,
        matched_aliases: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        output = result.get("output")
        if not isinstance(output, str) or not output.strip():
            output = original_message
        else:
            output = output.strip()
            if self._looks_like_answer(output):
                output = original_message
        output = self._apply_alias_rewrites(output, original_message, matched_aliases)

        keywords = self._sanitize_keywords(result.get("keywords"))
        if not keywords:
            keywords = self._fallback_keywords(output)
        keywords = self._enforce_alias_keywords(
            keywords=keywords,
            normalized_output=output,
            matched_aliases=matched_aliases,
            max_keywords=5,
        )

        return {
            "output": output,
            "keywords": keywords,
        }

    def _build_messages(self, user_message: str) -> List[Dict[str, str]]:
        system_prompt = self._build_system_prompt(user_message)
        messages: List[Dict[str, str]] = [{"role": "system", "content": system_prompt}]

        for example in self.examples:
            messages.append({"role": "user", "content": example["input"]})
            messages.append(
                {
                    "role": "assistant",
                    "content": json.dumps(
                        {
                            "output": example["output"],
                            "keywords": example["keywords"],
                        },
                        ensure_ascii=False,
                    ),
                }
            )

        messages.append({"role": "user", "content": user_message})
        return messages

    def process_query(self, user_message: str) -> Dict[str, Any]:
        """사용자 쿼리 정규화 + 키워드 추출"""
        try:
            matched_aliases = self._collect_matched_aliases(user_message)
            messages = self._build_messages(user_message)

            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.2,
                max_tokens=220,
            )

            if os.getenv("DEBUG_OPENAI_NORMALIZER") == "1":
                print(f"OpenAI 정규화 응답: {response}")

            result_text = response.choices[0].message.content.strip()

            try:
                result = json.loads(result_text)
                if isinstance(result, dict):
                    return self._normalize_result_shape(result, user_message, matched_aliases)
            except json.JSONDecodeError:
                pass

            return self._normalize_result_shape({"output": result_text}, user_message, matched_aliases)

        except Exception as e:
            print(f"입력 정규화 중 오류: {e}")
            print(f"오류 위치: {traceback.format_exc()}")
            fallback_aliases = self._collect_matched_aliases(user_message)
            return self._normalize_result_shape({"output": user_message}, user_message, fallback_aliases)

    def normalize_input_with_keywords(self, user_message: str) -> Dict[str, Any]:
        """정규화 문장과 검색 키워드를 함께 반환"""
        return self.process_query(user_message)

    def normalize_input(self, user_message: str) -> str:
        """하위 호환: 정규화 문장만 반환"""
        result = self.normalize_input_with_keywords(user_message)
        return result.get("output", user_message)
