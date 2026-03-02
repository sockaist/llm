"""Common schemas/constants for crawled and formatted data."""

from __future__ import annotations

from typing import Literal, TypedDict

CswebTag = Literal[
    "csweb.admin",
    "csweb.ai",
    "csweb.calendar",
    "csweb.news",
    "csweb.notice",
    "csweb.profs",
    "csweb.research",
]

CANONICAL_FIELDS: tuple[str, ...] = (
    "Computing Theory",
    "Systems-Networks",
    "Software Design",
    "Secure Computing",
    "Visual Computing",
    "AI-Information Service",
    "Social Computing",
    "Interactive Computing",
)

# Crawled/legacy variants -> canonical fields used in DB.
FIELD_NORMALIZATION_MAP: dict[str, str] = {
    "전산이론": "Computing Theory",
    "Computing Theory": "Computing Theory",
    "시스템·네트워크": "Systems-Networks",
    "Systems-Networks": "Systems-Networks",
    "소프트웨어 디자인": "Software Design",
    "소프트웨어디자인": "Software Design",
    "Software Design": "Software Design",
    "시큐어 컴퓨팅": "Secure Computing",
    "시큐어컴퓨팅": "Secure Computing",
    "Secure Computing": "Secure Computing",
    "비주얼 컴퓨팅": "Visual Computing",
    "비주얼컴퓨팅": "Visual Computing",
    "Visual Computing": "Visual Computing",
    "인공지능·정보서비스": "AI-Information Service",
    "AI-Information Service": "AI-Information Service",
    "소셜 컴퓨팅": "Social Computing",
    "소셜컴퓨팅": "Social Computing",
    "Social Computing": "Social Computing",
    "인터랙티브 컴퓨팅": "Interactive Computing",
    "인터랙티브컴퓨팅": "Interactive Computing",
    "Interactive Computing": "Interactive Computing",
}


class CswebRawPost(TypedDict):
    title: str
    date: str
    link: str
    tag: Literal["csweb.ai", "csweb.calendar", "csweb.news", "csweb.notice"]
    id: int
    content: str


class CswebRawCalendar(TypedDict):
    title: str
    date: str
    location: str
    link: str
    content: str
    tag: Literal["csweb.calendar"]
    id: int


class CswebRawAdmin(TypedDict):
    name: str
    position: str
    mail: str
    phone: str
    office: str
    work: str
    etc: str
    tag: Literal["csweb.admin"]
    id: int


class CswebRawProfessor(TypedDict):
    name: str
    field: str
    major: str
    degree: str
    web: str
    mail: str
    phone: str
    office: str
    etc: str
    tag: Literal["csweb.profs"]
    id: int


class CswebRawResearch(TypedDict):
    name: str
    professor: str
    field: str
    web: str
    email: str
    phone: str
    office: str
    intro: str
    etc: str
    tag: Literal["csweb.research"]
    id: int


# Formatted schema (llm/data/format.py 적용 후): same + content guaranteed.
class CswebFormattedProfessor(CswebRawProfessor):
    content: str


class CswebFormattedResearch(CswebRawResearch):
    content: str
