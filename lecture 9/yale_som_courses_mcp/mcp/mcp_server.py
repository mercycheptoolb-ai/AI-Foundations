"""Yale SOM course catalogue MCP — Lecture 9 starter.

In class you'll add real tools that read ../data/yale_som.db.
Right now there is a placeholder tool plus any tools you add.

Run from this folder (stdio):  python mcp_server.py
Run (HTTP):                    python mcp_server.py --http
HTTP URL:                      http://127.0.0.1:8001/mcp
"""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

from fastmcp import FastMCP

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DB_PATH = ROOT / "data" / "yale_som.db"

mcp = FastMCP("yale-som-courses")


@mcp.tool
def yo() -> str:
    """Placeholder tool — replace with real catalogue tools in class."""
    return "yo"


@mcp.tool
def search_courses_by_professor(name: str) -> list[dict]:
    """Find courses taught by a professor.

    Matches any part of the name, case-insensitive, in either order
    ("Rudi", "Nils Rudi", or "Rudi, Nils" all work).
    """
    words = [w for w in name.replace(",", " ").split() if w]
    if not words:
        return []
    where = " AND ".join("faculty_1 LIKE ?" for _ in words)
    params = [f"%{w}%" for w in words]
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            f"""
            SELECT course_number, course_title, faculty_1, faculty_1_email,
                   course_session, daytimes, room, section, units
            FROM courses
            WHERE {where}
            ORDER BY course_number, section
            """,
            params,
        ).fetchall()
    return [dict(r) for r in rows]


SEARCH_FIELDS = (
    "course_number",
    "course_title",
    "course_description",
    "course_category",
    "faculty_1",
)


@mcp.tool
def search_courses(keywords: str, limit: int = 25) -> list[dict]:
    """Search courses by keyword across title, description, professor,
    course number, and category.

    Case-insensitive. Every word must appear somewhere in the course
    ("pricing strategy" matches courses containing both words, in any field).
    Title matches are listed first. Returns up to `limit` results.
    """
    words = [w for w in keywords.replace(",", " ").split() if w]
    if not words:
        return []
    any_field = "(" + " OR ".join(f"{f} LIKE ?" for f in SEARCH_FIELDS) + ")"
    where = " AND ".join(any_field for _ in words)
    params = [f"%{w}%" for w in words for _ in SEARCH_FIELDS]
    title_hits = " + ".join("(course_title LIKE ?)" for _ in words)
    params += [f"%{w}%" for w in words]
    params.append(max(1, limit))
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            f"""
            SELECT course_number, course_title, course_category, faculty_1,
                   faculty_1_email, course_session, daytimes, room, section,
                   units, course_description
            FROM courses
            WHERE {where}
            ORDER BY {title_hits} DESC, course_number, section
            LIMIT ?
            """,
            params,
        ).fetchall()
    return [dict(r) for r in rows]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Yale SOM courses MCP server")
    parser.add_argument(
        "--http",
        action="store_true",
        help="Serve Streamable HTTP on port 8001 (keeps FastAPI free on 8000)",
    )
    args = parser.parse_args()
    if args.http:
        mcp.run(transport="http", host="127.0.0.1", port=8001)
    else:
        mcp.run()
