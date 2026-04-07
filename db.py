"""SQLite persistence for offers."""
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any

DB_PATH = Path(__file__).resolve().parent / "data" / "khao.db"


@contextmanager
def get_conn():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    with get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS offers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                offerer_id INTEGER NOT NULL,
                offeree_id INTEGER NOT NULL,
                amount REAL,
                note TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_offers_guild ON offers (guild_id)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_offers_offerer ON offers (guild_id, offerer_id)"
        )


def add_offer(
    guild_id: int,
    offerer_id: int,
    offeree_id: int,
    amount: float | None,
    note: str | None,
) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO offers (guild_id, offerer_id, offeree_id, amount, note)
            VALUES (?, ?, ?, ?, ?)
            """,
            (guild_id, offerer_id, offeree_id, amount, note),
        )
        return int(cur.lastrowid)


def leaderboard(guild_id: int, limit: int = 10) -> list[dict[str, Any]]:
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT offerer_id, COUNT(*) AS cnt
            FROM offers
            WHERE guild_id = ?
            GROUP BY offerer_id
            ORDER BY cnt DESC
            LIMIT ?
            """,
            (guild_id, limit),
        ).fetchall()
    return [{"offerer_id": r["offerer_id"], "count": r["cnt"]} for r in rows]


def history(
    guild_id: int,
    offerer_id: int | None = None,
    limit: int = 15,
) -> list[dict[str, Any]]:
    with get_conn() as conn:
        if offerer_id is None:
            rows = conn.execute(
                """
                SELECT id, offerer_id, offeree_id, amount, note, created_at
                FROM offers
                WHERE guild_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (guild_id, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT id, offerer_id, offeree_id, amount, note, created_at
                FROM offers
                WHERE guild_id = ? AND offerer_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (guild_id, offerer_id, limit),
            ).fetchall()
    return [dict(r) for r in rows]


def stats(guild_id: int) -> dict[str, Any]:
    with get_conn() as conn:
        total = conn.execute(
            "SELECT COUNT(*) AS c FROM offers WHERE guild_id = ?",
            (guild_id,),
        ).fetchone()["c"]
        top = conn.execute(
            """
            SELECT offerer_id, COUNT(*) AS cnt
            FROM offers
            WHERE guild_id = ?
            GROUP BY offerer_id
            ORDER BY cnt DESC
            LIMIT 1
            """,
            (guild_id,),
        ).fetchone()
    return {
        "total_offers": int(total),
        "top_offerer_id": int(top["offerer_id"]) if top else None,
        "top_count": int(top["cnt"]) if top else 0,
    }
