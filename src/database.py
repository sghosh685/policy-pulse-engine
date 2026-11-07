"""
NetZeroX Policy Pulse — Database Layer
SQLite-backed structured storage for regulatory updates.
"""

import sqlite3
import os
from datetime import datetime
from typing import Optional, List, Dict, Any


DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "policy_pulse.db")


def get_connection() -> sqlite3.Connection:
    """Get a database connection, creating the data dir if needed."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    """Create the schema if it doesn't exist and run schema migrations."""
    conn = get_connection()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS regulatory_updates (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            source_id           TEXT NOT NULL,
            source_name         TEXT NOT NULL,
            country             TEXT NOT NULL,
            title               TEXT NOT NULL,
            url                 TEXT UNIQUE NOT NULL,
            published_date      TEXT,
            raw_content         TEXT,
            summary             TEXT,
            impact_level        TEXT DEFAULT 'MEDIUM',
            action_required     TEXT,
            penalty_exposure    TEXT,
            action_legal        TEXT,
            action_ops          TEXT,
            action_esg          TEXT,
            cross_border_impact TEXT,
            keywords_matched    TEXT,
            tags                TEXT,
            analyzed            INTEGER DEFAULT 0,
            sent_in_report      INTEGER DEFAULT 0,
            created_at          TEXT DEFAULT (datetime('now')),
            updated_at          TEXT DEFAULT (datetime('now'))
        );

        CREATE INDEX IF NOT EXISTS idx_updates_source
            ON regulatory_updates(source_id);
        CREATE INDEX IF NOT EXISTS idx_updates_impact
            ON regulatory_updates(impact_level);
        CREATE INDEX IF NOT EXISTS idx_updates_date
            ON regulatory_updates(created_at);
        CREATE INDEX IF NOT EXISTS idx_updates_country
            ON regulatory_updates(country);

        CREATE TABLE IF NOT EXISTS scrape_log (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            source_id   TEXT NOT NULL,
            started_at  TEXT DEFAULT (datetime('now')),
            finished_at TEXT,
            items_found INTEGER DEFAULT 0,
            items_new   INTEGER DEFAULT 0,
            status      TEXT DEFAULT 'running',
            error       TEXT
        );

        CREATE TABLE IF NOT EXISTS subscribers (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            email       TEXT UNIQUE NOT NULL,
            name        TEXT,
            company     TEXT,
            tier        TEXT DEFAULT 'standard',
            active      INTEGER DEFAULT 1,
            created_at  TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS compliance_calendar (
            id                 INTEGER PRIMARY KEY AUTOINCREMENT,
            event_date         TEXT NOT NULL,
            event_name         TEXT NOT NULL,
            authority          TEXT,
            country            TEXT,
            impact             TEXT DEFAULT 'HIGH',
            statutory_penalty  TEXT,
            notified           INTEGER DEFAULT 0
        );
    """)

    # Gracefully add any new columns to existing databases
    existing_cols = [c[1] for c in conn.execute("PRAGMA table_info(regulatory_updates)").fetchall()]
    new_cols = {
        "penalty_exposure": "TEXT",
        "action_legal": "TEXT",
        "action_ops": "TEXT",
        "action_esg": "TEXT",
        "cross_border_impact": "TEXT"
    }
    for col_name, col_type in new_cols.items():
        if col_name not in existing_cols:
            try:
                conn.execute(f"ALTER TABLE regulatory_updates ADD COLUMN {col_name} {col_type}")
            except Exception:
                pass

    conn.commit()
    conn.close()
    print("✅ Database initialized at:", DB_PATH)


def insert_update(
    source_id: str,
    source_name: str,
    country: str,
    title: str,
    url: str,
    published_date: Optional[str] = None,
    raw_content: Optional[str] = None,
    keywords_matched: Optional[str] = None,
    tags: Optional[str] = None,
) -> Optional[int]:
    """Insert a regulatory update. Returns row ID or None if duplicate."""
    conn = get_connection()
    try:
        cursor = conn.execute(
            """INSERT INTO regulatory_updates
               (source_id, source_name, country, title, url,
                published_date, raw_content, keywords_matched, tags)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (source_id, source_name, country, title, url,
             published_date, raw_content, keywords_matched, tags),
        )
        conn.commit()
        return cursor.lastrowid
    except sqlite3.IntegrityError:
        return None
    finally:
        conn.close()


def update_analysis(
    row_id: int,
    summary: str,
    impact_level: str,
    action_required: str,
    penalty_exposure: Optional[str] = None,
    action_legal: Optional[str] = None,
    action_ops: Optional[str] = None,
    action_esg: Optional[str] = None,
    cross_border_impact: Optional[str] = None
):
    """Update a row with enriched AI analysis results."""
    conn = get_connection()
    conn.execute(
        """UPDATE regulatory_updates
           SET summary = ?, impact_level = ?, action_required = ?,
               penalty_exposure = ?, action_legal = ?, action_ops = ?, action_esg = ?, cross_border_impact = ?,
               analyzed = 1, updated_at = datetime('now')
           WHERE id = ?""",
        (summary, impact_level, action_required, penalty_exposure, action_legal, action_ops, action_esg, cross_border_impact, row_id),
    )
    conn.commit()
    conn.close()


def get_unanalyzed(limit: int = 50) -> List[Dict[str, Any]]:
    """Get items that haven't been analyzed by AI yet."""
    conn = get_connection()
    rows = conn.execute(
        """SELECT * FROM regulatory_updates
           WHERE analyzed = 0
           ORDER BY created_at DESC
           LIMIT ?""",
        (limit,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_all_updates() -> List[Dict[str, Any]]:
    """Get all regulatory updates ordered by severity and date."""
    conn = get_connection()
    impact_order = "CASE impact_level WHEN 'CRITICAL' THEN 1 WHEN 'HIGH' THEN 2 WHEN 'MEDIUM' THEN 3 ELSE 4 END"
    rows = conn.execute(
        f"""SELECT * FROM regulatory_updates
           ORDER BY {impact_order}, published_date DESC, created_at DESC"""
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_top_updates(days: int = 30, limit: int = 10) -> List[Dict[str, Any]]:
    """Get the top updates by impact level from the past N days."""
    conn = get_connection()
    impact_order = "CASE impact_level WHEN 'CRITICAL' THEN 1 WHEN 'HIGH' THEN 2 WHEN 'MEDIUM' THEN 3 ELSE 4 END"
    rows = conn.execute(
        f"""SELECT * FROM regulatory_updates
           WHERE analyzed = 1
           ORDER BY {impact_order}, published_date DESC, created_at DESC
           LIMIT ?""",
        (limit,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def mark_as_sent(ids: list[int]):
    """Mark items as included in a sent report."""
    conn = get_connection()
    placeholders = ",".join("?" * len(ids))
    conn.execute(
        f"UPDATE regulatory_updates SET sent_in_report = 1 WHERE id IN ({placeholders})",
        ids,
    )
    conn.commit()
    conn.close()


def log_scrape(source_id: str) -> int:
    """Start a scrape log entry. Returns log ID."""
    conn = get_connection()
    cursor = conn.execute(
        "INSERT INTO scrape_log (source_id) VALUES (?)", (source_id,)
    )
    conn.commit()
    log_id = cursor.lastrowid
    conn.close()
    return log_id


def finish_scrape(log_id: int, items_found: int, items_new: int, status: str = "done", error: Optional[str] = None):
    """Complete a scrape log entry."""
    conn = get_connection()
    conn.execute(
        """UPDATE scrape_log
           SET finished_at = datetime('now'), items_found = ?, items_new = ?,
               status = ?, error = ?
           WHERE id = ?""",
        (items_found, items_new, status, error, log_id),
    )
    conn.commit()
    conn.close()


def get_stats() -> dict:
    """Get dashboard stats."""
    conn = get_connection()
    total = conn.execute("SELECT COUNT(*) FROM regulatory_updates").fetchone()[0]
    analyzed = conn.execute("SELECT COUNT(*) FROM regulatory_updates WHERE analyzed = 1").fetchone()[0]
    by_country = conn.execute(
        "SELECT country, COUNT(*) as cnt FROM regulatory_updates GROUP BY country"
    ).fetchall()
    by_impact = conn.execute(
        "SELECT impact_level, COUNT(*) as cnt FROM regulatory_updates WHERE analyzed = 1 GROUP BY impact_level"
    ).fetchall()
    conn.close()
    return {
        "total_items": total,
        "analyzed": analyzed,
        "unanalyzed": total - analyzed,
        "by_country": {r["country"]: r["cnt"] for r in by_country},
        "by_impact": {r["impact_level"]: r["cnt"] for r in by_impact},
    }
