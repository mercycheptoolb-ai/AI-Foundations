"""SQLite helpers for data/campus_customs.db."""

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

HW4_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = HW4_DIR / "data"
DB_PATH = DATA_DIR / "campus_customs.db"


@contextmanager
def db(write: bool = False) -> Iterator[sqlite3.Connection]:
    """Open a connection, commit on success (write mode), and always close it.

    Read-only by default so catalogue/inventory endpoints can never modify data.
    """
    if write:
        conn = sqlite3.connect(DB_PATH, timeout=10)
        conn.execute("PRAGMA foreign_keys = ON")
    else:
        conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        if write:
            conn.commit()
    except Exception:
        if write:
            conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    """Create tables the seed database doesn't ship with."""
    with db(write=True) as conn:
        # Login sessions. Only a SHA-256 of the session token is stored, so a
        # leaked database can't be used to hijack anyone's logged-in session.
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                token_hash TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                expires_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id)")
        conn.execute("DELETE FROM sessions WHERE expires_at <= datetime('now')")

        # Customer memory (Problem 8): chat_messages ships with the seed database. Add two
        # optional columns so a reloaded conversation keeps its context:
        #   page_context_json - (user turns) which page the shopper was on when they asked
        #   page_search_json  - (assistant turns) the product grid the reply put on the page
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(chat_messages)")}
        for col in ("page_context_json", "page_search_json"):
            if col not in cols:
                conn.execute(f"ALTER TABLE chat_messages ADD COLUMN {col} TEXT")
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_chat_messages_user ON chat_messages(user_id, id)"
        )
