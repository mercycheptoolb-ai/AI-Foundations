"""Agent tools: search_courses (local JSON) and web_search (OpenAI native web search)."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from pydantic_ai.capabilities import WebSearch

from models import Course, SearchResult

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DATA_PATH = ROOT / "data" / "yale_som_classes.json"

MAX_RESULTS = 15


@lru_cache(maxsize=1)
def load_courses() -> tuple[Course, ...]:
    rows = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    return tuple(Course.model_validate(row) for row in rows)


def _norm(text: str) -> str:
    return " ".join(text.lower().split())


def _compact(text: str) -> str:
    return text.lower().replace(" ", "")


def search_courses(
    query: str = "",
    faculty: str = "",
    category: str = "",
    day: str = "",
    session: str = "",
    limit: int = MAX_RESULTS,
) -> SearchResult:
    """Case-insensitive search over the course catalog.

    query    -> every word must appear in title, number, description, faculty, category, or type
    faculty  -> substring of the instructor name ("Simonsohn")
    category -> substring of Course Category or Course Type ("finance", "core", "elective")
    day      -> substring of Daytimes / Timings Day ("W", "Tu", "Monday" -> "M")
    session  -> exact session: "fall", "fall-1", or "fall-2"
    """
    limit = max(1, min(int(limit or MAX_RESULTS), MAX_RESULTS))
    words = _norm(query).split()
    fac = _norm(faculty)
    cat = _norm(category)
    day_q = _norm(day)
    day_q = {"monday": "m", "tuesday": "tu", "wednesday": "w", "thursday": "th", "friday": "f"}.get(day_q, day_q)
    sess = _norm(session)

    matches: list[Course] = []
    for c in load_courses():
        haystack = _norm(" ".join([c.title, c.number, c.description, c.faculty, c.category, c.course_type]))
        compact_hay = _compact(haystack)
        if words and not all(w in haystack or _compact(w) in compact_hay for w in words):
            continue
        if fac and fac not in _norm(c.faculty):
            continue
        if cat and cat not in _norm(f"{c.category} {c.course_type}"):
            continue
        if day_q and day_q not in _norm(f"{c.daytimes} {c.day}"):
            continue
        if sess and sess != _norm(c.session):
            continue
        matches.append(c)

    used = {k: v for k, v in {"query": query, "faculty": faculty, "category": category, "day": day, "session": session}.items() if v}
    return SearchResult(
        query=used,
        total_matches=len(matches),
        returned=min(len(matches), limit),
        truncated=len(matches) > limit,
        courses=matches[:limit],
    )


# OpenAI's native (server-side) web search via the Responses API. No DuckDuckGo fallback.
web_search = WebSearch(local=False)
