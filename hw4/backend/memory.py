"""Customer memory: logged-in shoppers' chat history in the chat_messages table.

Every query here is filtered by user_id, which always comes from the session
cookie (never from the browser or the model), so one shopper can never read or
change another shopper's messages. Guests have no user_id, so nothing is saved.
"""

import json
import re
import sqlite3

from db import db
from models import CustomerProfile

SEARCH_STOPWORDS = {
    "the", "and", "you", "for", "that", "this", "what", "was", "were", "with", "about", "did",
    "do", "we", "me", "my", "i", "a", "an", "of", "to", "in", "it", "is", "last", "time",
    "talk", "talked", "said", "say", "ask", "asked", "earlier", "before", "remember", "chat",
    "yale", "you", "suggested", "recommended", "showed", "show", "one", "that", "those",
}


def load_customer(user_id: int) -> CustomerProfile | None:
    with db() as conn:
        row = conn.execute(
            "SELECT id, name, first_name, last_name, email, created_at FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
    if row is None:
        return None
    first = row["first_name"] or row["name"].split(" ")[0]
    last = row["last_name"] or " ".join(row["name"].split(" ")[1:])
    return CustomerProfile(
        user_id=row["id"],
        first_name=first,
        last_name=last,
        email=row["email"],
        member_since=(row["created_at"] or "")[:10],
    )


def recent_messages(user_id: int, limit: int) -> list[sqlite3.Row]:
    """The shopper's latest messages, oldest first."""
    with db() as conn:
        rows = conn.execute(
            "SELECT id, role, content, products_json, page_context_json, page_search_json, created_at "
            "FROM chat_messages WHERE user_id = ? ORDER BY id DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
    return list(reversed(rows))


def save_exchange(
    user_id: int,
    message: str,
    reply: str,
    cards: list[dict],
    page_context: dict | None,
    page_search: dict | None,
) -> None:
    """Store one shopper message and the assistant's reply (in one transaction)."""
    with db(write=True) as conn:
        conn.execute(
            "INSERT INTO chat_messages (user_id, role, content, page_context_json) VALUES (?, 'user', ?, ?)",
            (user_id, message, json.dumps(page_context) if page_context else None),
        )
        conn.execute(
            "INSERT INTO chat_messages (user_id, role, content, products_json, page_search_json) "
            "VALUES (?, 'assistant', ?, ?, ?)",
            (
                user_id,
                reply,
                json.dumps(cards) if cards else None,
                json.dumps(page_search) if page_search else None,
            ),
        )


def search_messages(user_id: int, query: str, limit: int) -> list[sqlite3.Row]:
    """The shopper's own messages matching the query, best match first.

    Messages are ranked by how many of the query's words they contain (in the text or in
    the products shown with them), then by recency. So "that jacket you suggested for my
    dad" finds the old message mentioning both, not just the newest one saying "jacket".
    """
    words = [w for w in re.findall(r"[a-z0-9]+", query.lower()) if len(w) >= 3 and w not in SEARCH_STOPWORDS]
    haystack = "lower(content || ' ' || coalesce(products_json, ''))"
    sql = "SELECT role, content, products_json, created_at FROM chat_messages WHERE user_id = ?"
    params: list = [user_id]
    if words:
        likes = [f"({haystack} LIKE ?)" for _ in words]
        sql += " AND (" + " OR ".join(likes) + ")"
        sql += " ORDER BY (" + " + ".join(likes) + ") DESC, id DESC"
        params += [f"%{w}%" for w in words] * 2
    else:
        sql += " ORDER BY id DESC"
    sql += " LIMIT ?"
    params.append(limit)
    with db() as conn:
        return conn.execute(sql, params).fetchall()


def message_stats(user_id: int) -> tuple[int, str | None]:
    with db() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS n, MIN(created_at) AS first FROM chat_messages WHERE user_id = ?",
            (user_id,),
        ).fetchone()
    return row["n"], row["first"]


def clear_history(user_id: int) -> int:
    with db(write=True) as conn:
        return conn.execute("DELETE FROM chat_messages WHERE user_id = ?", (user_id,)).rowcount


def ids_from_products_json(raw: str | None) -> list[str]:
    """products_json holds product dicts (seed data) or product cards (ours); keep just the ids."""
    if not raw:
        return []
    try:
        items = json.loads(raw)
    except json.JSONDecodeError:
        return []
    return [i["product_id"] for i in items if isinstance(i, dict) and i.get("product_id")]


def load_json(raw: str | None) -> dict | None:
    if not raw:
        return None
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, dict) else None
