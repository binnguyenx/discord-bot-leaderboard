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


def _table_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return {str(r["name"]) for r in rows}


def init_db() -> None:
    with get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS offers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                offerer_id INTEGER NOT NULL,
                offeree_id INTEGER NOT NULL,
                company TEXT,
                term TEXT,
                note TEXT,
                count INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )
        cols = _table_columns(conn, "offers")
        if "company" not in cols:
            conn.execute("ALTER TABLE offers ADD COLUMN company TEXT")
        if "term" not in cols:
            conn.execute("ALTER TABLE offers ADD COLUMN term TEXT")
        if "count" not in cols:
            conn.execute("ALTER TABLE offers ADD COLUMN count INTEGER NOT NULL DEFAULT 1")
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_offers_guild ON offers (guild_id)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_offers_offerer ON offers (guild_id, offerer_id)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_offers_term ON offers (guild_id, term)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_offers_match ON offers (guild_id, offerer_id, offeree_id, company, term)"
        )


def add_or_increment_offer(
    guild_id: int,
    offerer_id: int,
    offeree_id: int,
    company: str,
    term: str,
    note: str | None,
) -> dict[str, Any]:
    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT id, count
            FROM offers
            WHERE guild_id = ? AND offerer_id = ? AND offeree_id = ?
              AND COALESCE(company, '') = ? AND COALESCE(term, '') = ?
            LIMIT 1
            """,
            (guild_id, offerer_id, offeree_id, company, term),
        ).fetchone()
        if row is None:
            cur = conn.execute(
                """
                INSERT INTO offers (guild_id, offerer_id, offeree_id, company, term, note, count)
                VALUES (?, ?, ?, ?, ?, ?, 1)
                """,
                (guild_id, offerer_id, offeree_id, company, term, note),
            )
            oid = int(cur.lastrowid)
            return {"id": oid, "count": 1, "created": True}

        new_count = int(row["count"] or 0) + 1
        if note and note.strip():
            conn.execute(
                """
                UPDATE offers
                SET count = ?, note = ?
                WHERE id = ?
                """,
                (new_count, note, int(row["id"])),
            )
        else:
            conn.execute(
                """
                UPDATE offers
                SET count = ?
                WHERE id = ?
                """,
                (new_count, int(row["id"])),
            )
        return {"id": int(row["id"]), "count": new_count, "created": False}


def get_offer(guild_id: int, offer_id: int) -> dict[str, Any] | None:
    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT id, guild_id, offerer_id, offeree_id, company, term, note, count, created_at
            FROM offers
            WHERE id = ? AND guild_id = ?
            """,
            (offer_id, guild_id),
        ).fetchone()
    return dict(row) if row else None


def delete_offer(guild_id: int, offer_id: int) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "DELETE FROM offers WHERE id = ? AND guild_id = ?",
            (offer_id, guild_id),
        )
        return int(cur.rowcount or 0)


def leaderboard(guild_id: int, term: str, limit: int = 10) -> list[dict[str, Any]]:
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT offerer_id, SUM(COALESCE(count, 1)) AS cnt
            FROM offers
            WHERE guild_id = ? AND COALESCE(term, '') = ?
            GROUP BY offerer_id
            ORDER BY cnt DESC
            LIMIT ?
            """,
            (guild_id, term, limit),
        ).fetchall()
    return [{"offerer_id": r["offerer_id"], "count": r["cnt"]} for r in rows]


def offerer_offer_breakdown(
    guild_id: int,
    offerer_id: int,
    term: str,
    limit: int = 20,
) -> list[dict[str, Any]]:
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT
                COALESCE(company, '—') AS company,
                COALESCE(term, '—') AS term,
                SUM(COALESCE(count, 1)) AS cnt
            FROM offers
            WHERE guild_id = ? AND offerer_id = ? AND COALESCE(term, '') = ?
            GROUP BY company, term
            ORDER BY cnt DESC, company ASC
            LIMIT ?
            """,
            (guild_id, offerer_id, term, limit),
        ).fetchall()
    return [dict(r) for r in rows]


def history(
    guild_id: int,
    offerer_id: int | None = None,
    term: str | None = None,
    limit: int = 15,
) -> list[dict[str, Any]]:
    with get_conn() as conn:
        if offerer_id is None:
            if term is None:
                rows = conn.execute(
                    """
                    SELECT id, offerer_id, offeree_id, company, term, note, count, created_at
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
                    SELECT id, offerer_id, offeree_id, company, term, note, count, created_at
                    FROM offers
                    WHERE guild_id = ? AND COALESCE(term, '') = ?
                    ORDER BY id DESC
                    LIMIT ?
                    """,
                    (guild_id, term, limit),
                ).fetchall()
        else:
            if term is None:
                rows = conn.execute(
                    """
                    SELECT id, offerer_id, offeree_id, company, term, note, count, created_at
                    FROM offers
                    WHERE guild_id = ? AND offerer_id = ?
                    ORDER BY id DESC
                    LIMIT ?
                    """,
                    (guild_id, offerer_id, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT id, offerer_id, offeree_id, company, term, note, count, created_at
                    FROM offers
                    WHERE guild_id = ? AND offerer_id = ? AND COALESCE(term, '') = ?
                    ORDER BY id DESC
                    LIMIT ?
                    """,
                    (guild_id, offerer_id, term, limit),
                ).fetchall()
    return [dict(r) for r in rows]


def stats(guild_id: int, term: str | None = None) -> dict[str, Any]:
    with get_conn() as conn:
        if term is None:
            total = conn.execute(
                "SELECT COALESCE(SUM(count), 0) AS c FROM offers WHERE guild_id = ?",
                (guild_id,),
            ).fetchone()["c"]
            total_records = conn.execute(
                "SELECT COUNT(*) AS c FROM offers WHERE guild_id = ?",
                (guild_id,),
            ).fetchone()["c"]
            top = conn.execute(
                """
                SELECT offerer_id, SUM(COALESCE(count, 1)) AS cnt
                FROM offers
                WHERE guild_id = ?
                GROUP BY offerer_id
                ORDER BY cnt DESC
                LIMIT 1
                """,
                (guild_id,),
            ).fetchone()
        else:
            total = conn.execute(
                "SELECT COALESCE(SUM(count), 0) AS c FROM offers WHERE guild_id = ? AND COALESCE(term, '') = ?",
                (guild_id, term),
            ).fetchone()["c"]
            total_records = conn.execute(
                "SELECT COUNT(*) AS c FROM offers WHERE guild_id = ? AND COALESCE(term, '') = ?",
                (guild_id, term),
            ).fetchone()["c"]
            top = conn.execute(
                """
                SELECT offerer_id, SUM(COALESCE(count, 1)) AS cnt
                FROM offers
                WHERE guild_id = ? AND COALESCE(term, '') = ?
                GROUP BY offerer_id
                ORDER BY cnt DESC
                LIMIT 1
                """,
                (guild_id, term),
            ).fetchone()
    return {
        "total_offers": int(total),
        "total_records": int(total_records),
        "top_offerer_id": int(top["offerer_id"]) if top else None,
        "top_count": int(top["cnt"]) if top else 0,
    }
