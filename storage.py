"""SQLite storage for one luck record per user and day."""

from __future__ import annotations

import sqlite3
from pathlib import Path


class JrrpStore:
    """Store luck records in a local SQLite database.

    Attributes:
        path: Database file path.
    """

    def __init__(self, path: Path) -> None:
        """Open the database and make sure the table exists.

        Args:
            path: Database file path; parent directories are created on demand.
        """
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS jrrp_data (
                user_id TEXT NOT NULL,
                value INTEGER NOT NULL,
                date TEXT NOT NULL
            )
            """
        )
        self._conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS jrrp_user_date "
            "ON jrrp_data (user_id, date)"
        )
        self._conn.commit()

    def add(self, user_id: str, value: int, date: str) -> None:
        """Insert one record, ignoring the day already being recorded.

        Args:
            user_id: Platform sender id.
            value: Luck value of that day.
            date: Date string in ``%y%m%d`` form.
        """
        self._conn.execute(
            "INSERT OR IGNORE INTO jrrp_data (user_id, value, date) VALUES (?, ?, ?)",
            (user_id, value, date),
        )
        self._conn.commit()

    def has(self, user_id: str, date: str) -> bool:
        """Tell whether a record already exists for that day.

        Args:
            user_id: Platform sender id.
            date: Date string in ``%y%m%d`` form.

        Returns:
            ``True`` when the record exists.
        """
        row = self._conn.execute(
            "SELECT 1 FROM jrrp_data WHERE user_id = ? AND date = ? LIMIT 1",
            (user_id, date),
        ).fetchone()
        return row is not None

    def history(self, user_id: str) -> list[tuple[str, int]]:
        """Return every stored record of one user, newest first.

        Args:
            user_id: Platform sender id.

        Returns:
            ``(date, value)`` pairs ordered by date descending.
        """
        rows = self._conn.execute(
            "SELECT date, value FROM jrrp_data WHERE user_id = ? ORDER BY date DESC",
            (user_id,),
        ).fetchall()
        return [(str(date), int(value)) for date, value in rows]

    def close(self) -> None:
        """Close the underlying connection."""
        self._conn.close()
