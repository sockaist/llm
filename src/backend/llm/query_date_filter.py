import json
import os
import re
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any, Optional

import openai


@dataclass
class QueryDateFilter:
    start_date: Optional[date] = None
    end_date: Optional[date] = None

    def has_filter(self) -> bool:
        return self.start_date is not None or self.end_date is not None


DATE_FILTER_SYSTEM_PROMPT = """
너는 사용자 질문에서 검색용 날짜 범위를 추출하는 파서다.

반드시 JSON 객체로만 답하고, 형식은 아래와 같다:
{
  "start_date": "YYYY-MM-DD" 또는 null,
  "end_date": "YYYY-MM-DD" 또는 null
}

규칙:
- 오늘 날짜를 기준으로 상대 시간 표현(최근 n개월/n주/n일/n년, 올해, 작년, 이번 달, 지난달)을 해석한다.
- 날짜가 한 개만 명시되면 start_date와 end_date를 같은 날짜로 둔다.
- 날짜 범위를 판단할 근거가 없으면 둘 다 null로 둔다.
- 설명 문장, 코드블록, 주석 없이 JSON만 출력한다.
""".strip()


def _month_range(year: int, month: int) -> tuple[date, date]:
    start = date(year, month, 1)
    if month == 12:
        end = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        end = date(year, month + 1, 1) - timedelta(days=1)
    return start, end


def _subtract_months(d: date, months: int) -> date:
    y = d.year
    m = d.month - months
    while m <= 0:
        y -= 1
        m += 12
    return date(y, m, 1)


def _parse_iso_date(value: Any) -> Optional[date]:
    if value is None:
        return None
    if isinstance(value, date):
        return value
    if not isinstance(value, str):
        return None

    text = value.strip()
    if not text or text.lower() in {"null", "none"}:
        return None

    # YYYY-MM-DD 또는 뒤에 시간 정보가 붙은 경우까지 허용
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})", text)
    if not m:
        return None

    try:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:
        return None


def _extract_json_object(text: str) -> Optional[dict]:
    raw = (text or "").strip()
    if not raw:
        return None

    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    matched = re.search(r"\{.*\}", raw, flags=re.DOTALL)
    if not matched:
        return None

    try:
        parsed = json.loads(matched.group(0))
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        return None


def _parse_explicit_dates(text: str) -> list[date]:
    dates: list[date] = []

    for m in re.finditer(r"(\d{4})-(\d{1,2})-(\d{1,2})", text):
        y, mo, da = int(m.group(1)), int(m.group(2)), int(m.group(3))
        try:
            dates.append(date(y, mo, da))
        except ValueError:
            pass

    for m in re.finditer(r"(\d{4})\.(\d{1,2})\.(\d{1,2})", text):
        y, mo, da = int(m.group(1)), int(m.group(2)), int(m.group(3))
        try:
            dates.append(date(y, mo, da))
        except ValueError:
            pass

    for m in re.finditer(r"(\d{4})년\s*(\d{1,2})월\s*(\d{1,2})일", text):
        y, mo, da = int(m.group(1)), int(m.group(2)), int(m.group(3))
        try:
            dates.append(date(y, mo, da))
        except ValueError:
            pass

    return dates


class QueryDateFilterExtractor:
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o-mini"):
        self.model = model
        self.client = openai.OpenAI(api_key=api_key) if api_key else None
        self.debug = os.getenv("DEBUG_DATE_FILTER") == "1"

    def _extract_with_llm(self, query: str, base: date) -> Optional[QueryDateFilter]:
        if self.client is None:
            return None

        try:
            today_text = base.isoformat()
            messages = [
                {"role": "system", "content": DATE_FILTER_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        f"오늘 날짜: {today_text}\n"
                        f"사용자 질문: {query}\n"
                        "JSON으로만 답하라."
                    ),
                },
            ]

            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.0,
            )
            raw = (response.choices[0].message.content or "").strip()
            payload = _extract_json_object(raw)
            if not payload:
                if self.debug:
                    print(f"⚠️ 날짜필터 LLM JSON 파싱 실패: {raw}")
                return None

            start_date = _parse_iso_date(payload.get("start_date"))
            end_date = _parse_iso_date(payload.get("end_date"))
            if start_date and end_date and start_date > end_date:
                start_date, end_date = end_date, start_date

            extracted = QueryDateFilter(start_date=start_date, end_date=end_date)
            if self.debug:
                print(
                    "🗓️ 날짜필터 LLM 결과:",
                    {
                        "query": query,
                        "start_date": str(extracted.start_date) if extracted.start_date else None,
                        "end_date": str(extracted.end_date) if extracted.end_date else None,
                    },
                )
            return extracted
        except Exception as e:
            if self.debug:
                print(f"⚠️ 날짜필터 LLM 호출 실패: {e}")
            return None

    def _extract_with_rules(self, text: str, base: date) -> QueryDateFilter:
        explicit = _parse_explicit_dates(text)
        if len(explicit) >= 2:
            return QueryDateFilter(start_date=min(explicit), end_date=max(explicit))
        if len(explicit) == 1:
            return QueryDateFilter(start_date=explicit[0], end_date=explicit[0])

        # 최근 n개월 / n달 / n주 / n일 / n년
        m = re.search(r"최근\s*(\d+)\s*(개월|달)", text)
        if m:
            n = int(m.group(1))
            return QueryDateFilter(start_date=_subtract_months(base, n), end_date=base)

        m = re.search(r"최근\s*(\d+)\s*주", text)
        if m:
            n = int(m.group(1))
            return QueryDateFilter(start_date=base - timedelta(weeks=n), end_date=base)

        m = re.search(r"최근\s*(\d+)\s*일", text)
        if m:
            n = int(m.group(1))
            return QueryDateFilter(start_date=base - timedelta(days=n), end_date=base)

        m = re.search(r"최근\s*(\d+)\s*년", text)
        if m:
            n = int(m.group(1))
            return QueryDateFilter(start_date=date(base.year - n, 1, 1), end_date=base)

        if re.search(r"(최근|최신|요즘|근래)", text):
            return QueryDateFilter(start_date=_subtract_months(base, 3), end_date=base)

        if "올해" in text:
            return QueryDateFilter(start_date=date(base.year, 1, 1), end_date=date(base.year, 12, 31))
        if "작년" in text:
            y = base.year - 1
            return QueryDateFilter(start_date=date(y, 1, 1), end_date=date(y, 12, 31))

        if "이번 달" in text or "이번달" in text:
            s, e = _month_range(base.year, base.month)
            return QueryDateFilter(start_date=s, end_date=e)

        if "지난달" in text or "지난 달" in text:
            prev_month_base = _subtract_months(base, 1)
            s, e = _month_range(prev_month_base.year, prev_month_base.month)
            return QueryDateFilter(start_date=s, end_date=e)

        # 연도만 있는 질의: 2024년
        m = re.search(r"(\d{4})년", text)
        if m:
            y = int(m.group(1))
            return QueryDateFilter(start_date=date(y, 1, 1), end_date=date(y, 12, 31))

        return QueryDateFilter()

    def extract(self, query: str, today: Optional[date] = None) -> QueryDateFilter:
        base = today or date.today()
        text = (query or "").strip()
        if not text:
            return QueryDateFilter()

        llm_result = self._extract_with_llm(text, base)
        if llm_result is not None:
            if llm_result.has_filter():
                return llm_result
            # LLM이 null/null을 준 경우도 규칙 기반으로 한 번 더 보정한다.
            rule_result = self._extract_with_rules(text, base)
            return rule_result if rule_result.has_filter() else llm_result

        return self._extract_with_rules(text, base)
