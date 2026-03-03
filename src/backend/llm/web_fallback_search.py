"""
근거 문서가 없을 때 사용하는 외부 웹 검색 fallback 도구.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Dict, List
from urllib.parse import parse_qs, unquote, urlparse

import requests
from bs4 import BeautifulSoup


class WebFallbackSearcher:
    SEARCH_URL = "https://duckduckgo.com/html/"
    BING_RSS_URL = "https://www.bing.com/search"

    def __init__(
        self,
        *,
        timeout_sec: int = 8,
        region: str = "kr-kr",
        debug: bool = False,
    ):
        self.timeout_sec = max(2, int(timeout_sec))
        self.region = (region or "kr-kr").strip() or "kr-kr"
        self.debug = debug
        self.user_agent = (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        )

    @staticmethod
    def _normalize_url(raw_href: str) -> str:
        href = str(raw_href or "").strip()
        if not href:
            return ""

        if href.startswith("//"):
            href = f"https:{href}"

        # DuckDuckGo redirect 형식(/l/?uddg=...)을 실제 URL로 복원
        if href.startswith("/l/?") or "duckduckgo.com/l/?" in href:
            parsed = urlparse(href if "://" in href else f"https://duckduckgo.com{href}")
            uddg = parse_qs(parsed.query).get("uddg", [None])[0]
            if isinstance(uddg, str) and uddg.strip():
                return unquote(uddg.strip())
        return href

    @staticmethod
    def _clean_text(text: str) -> str:
        return " ".join(str(text or "").split()).strip()

    def _search_bing_rss(self, query: str, max_results: int) -> List[Dict[str, str]]:
        try:
            response = requests.get(
                self.BING_RSS_URL,
                params={"q": query, "format": "rss"},
                headers={"User-Agent": self.user_agent},
                timeout=self.timeout_sec,
            )
            response.raise_for_status()
            root = ET.fromstring(response.text)
        except Exception as e:
            if self.debug:
                print(f"⚠️ bing rss 검색 실패: {e}")
            return []

        results: List[Dict[str, str]] = []
        seen_urls = set()
        for item in root.findall("./channel/item"):
            title = self._clean_text(item.findtext("title", default=""))
            url = self._clean_text(item.findtext("link", default=""))
            raw_desc = self._clean_text(item.findtext("description", default=""))
            snippet = self._clean_text(BeautifulSoup(raw_desc, "html.parser").get_text(" ", strip=True))
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)
            results.append(
                {
                    "title": title or url,
                    "url": url,
                    "snippet": snippet,
                }
            )
            if len(results) >= max_results:
                break
        return results

    def search(self, query: str, max_results: int = 5) -> List[Dict[str, str]]:
        cleaned_query = self._clean_text(query)
        if not cleaned_query:
            return []

        safe_max = max(1, min(int(max_results), 10))
        # 1) Bing RSS(무키) 우선 시도
        bing_results = self._search_bing_rss(cleaned_query, safe_max)
        if bing_results:
            return bing_results

        # 2) 실패 시 DuckDuckGo HTML fallback
        try:
            response = requests.get(
                self.SEARCH_URL,
                params={"q": cleaned_query, "kl": self.region},
                headers={"User-Agent": self.user_agent},
                timeout=self.timeout_sec,
            )
            response.raise_for_status()
        except Exception as e:
            if self.debug:
                print(f"⚠️ web fallback 검색 요청 실패: {e}")
            return []

        soup = BeautifulSoup(response.text, "html.parser")
        result_nodes = soup.select("div.result")
        if not result_nodes:
            # ddg 마크업 변형 대비 fallback selector
            result_nodes = soup.select("article")

        results: List[Dict[str, str]] = []
        seen_urls = set()
        for node in result_nodes:
            link_el = node.select_one("a.result__a") or node.select_one("a")
            if link_el is None:
                continue
            title = self._clean_text(link_el.get_text(" ", strip=True))
            raw_href = str(link_el.get("href", "")).strip()
            url = self._normalize_url(raw_href)
            if not url or url in seen_urls:
                continue

            snippet_el = node.select_one(".result__snippet") or node.select_one(".result-snippet")
            snippet = self._clean_text(snippet_el.get_text(" ", strip=True) if snippet_el else "")

            seen_urls.add(url)
            results.append(
                {
                    "title": title or url,
                    "url": url,
                    "snippet": snippet,
                }
            )
            if len(results) >= safe_max:
                break

        return results
