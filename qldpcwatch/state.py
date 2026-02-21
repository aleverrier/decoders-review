from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path


@dataclass
class VersionRecord:
    arxiv_id: str
    version: str
    updated_date: str
    source_hash: str
    extraction_hash: str | None
    created_at: str


class StateDB:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.conn = sqlite3.connect(str(db_path))
        self.conn.row_factory = sqlite3.Row
        self._init_db()

    def close(self) -> None:
        self.conn.close()

    def _init_db(self) -> None:
        self.conn.executescript(
            """
            PRAGMA journal_mode=WAL;

            CREATE TABLE IF NOT EXISTS state_meta (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS papers (
                arxiv_id TEXT PRIMARY KEY,
                latest_version TEXT NOT NULL,
                latest_source_hash TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                title TEXT NOT NULL,
                primary_category TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS versions (
                arxiv_id TEXT NOT NULL,
                version TEXT NOT NULL,
                updated_date TEXT NOT NULL,
                source_hash TEXT NOT NULL,
                extraction_hash TEXT,
                created_at TEXT NOT NULL,
                PRIMARY KEY (arxiv_id, version)
            );

            CREATE TABLE IF NOT EXISTS runs (
                run_id INTEGER PRIMARY KEY AUTOINCREMENT,
                started_at TEXT NOT NULL,
                finished_at TEXT,
                since_ts TEXT,
                new_papers INTEGER DEFAULT 0,
                updated_papers INTEGER DEFAULT 0,
                notes TEXT
            );
            """
        )
        self.conn.commit()

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(tz=UTC).isoformat()

    def get_meta(self, key: str) -> str | None:
        row = self.conn.execute("SELECT value FROM state_meta WHERE key = ?", (key,)).fetchone()
        if row is None:
            return None
        return str(row["value"])

    def set_meta(self, key: str, value: str) -> None:
        self.conn.execute(
            """
            INSERT INTO state_meta(key, value)
            VALUES(?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (key, value),
        )
        self.conn.commit()

    def get_last_run(self) -> str | None:
        return self.get_meta("last_run")

    def set_last_run(self, timestamp_iso: str) -> None:
        self.set_meta("last_run", timestamp_iso)

    def start_run(self, since_ts: str | None) -> int:
        cur = self.conn.execute(
            "INSERT INTO runs(started_at, since_ts) VALUES(?, ?)",
            (self._now_iso(), since_ts),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def finish_run(
        self,
        run_id: int,
        *,
        new_papers: int,
        updated_papers: int,
        notes: dict | None = None,
    ) -> None:
        self.conn.execute(
            """
            UPDATE runs
            SET finished_at = ?, new_papers = ?, updated_papers = ?, notes = ?
            WHERE run_id = ?
            """,
            (self._now_iso(), new_papers, updated_papers, json.dumps(notes or {}), run_id),
        )
        self.conn.commit()

    def get_paper(self, arxiv_id: str) -> sqlite3.Row | None:
        return self.conn.execute("SELECT * FROM papers WHERE arxiv_id = ?", (arxiv_id,)).fetchone()

    def upsert_paper(
        self,
        *,
        arxiv_id: str,
        latest_version: str,
        latest_source_hash: str,
        title: str,
        primary_category: str,
    ) -> None:
        self.conn.execute(
            """
            INSERT INTO papers(
                arxiv_id, latest_version, latest_source_hash,
                updated_at, title, primary_category
            )
            VALUES(?, ?, ?, ?, ?, ?)
            ON CONFLICT(arxiv_id) DO UPDATE SET
                latest_version = excluded.latest_version,
                latest_source_hash = excluded.latest_source_hash,
                updated_at = excluded.updated_at,
                title = excluded.title,
                primary_category = excluded.primary_category
            """,
            (
                arxiv_id,
                latest_version,
                latest_source_hash,
                self._now_iso(),
                title,
                primary_category,
            ),
        )
        self.conn.commit()

    def record_version(
        self,
        *,
        arxiv_id: str,
        version: str,
        updated_date: str,
        source_hash: str,
        extraction_hash: str | None,
    ) -> None:
        self.conn.execute(
            """
            INSERT INTO versions(
                arxiv_id, version, updated_date,
                source_hash, extraction_hash, created_at
            )
            VALUES(?, ?, ?, ?, ?, ?)
            ON CONFLICT(arxiv_id, version) DO UPDATE SET
                updated_date = excluded.updated_date,
                source_hash = excluded.source_hash,
                extraction_hash = excluded.extraction_hash
            """,
            (arxiv_id, version, updated_date, source_hash, extraction_hash, self._now_iso()),
        )
        self.conn.commit()

    def get_version(self, arxiv_id: str, version: str) -> sqlite3.Row | None:
        return self.conn.execute(
            "SELECT * FROM versions WHERE arxiv_id = ? AND version = ?",
            (arxiv_id, version),
        ).fetchone()

    def get_versions(self, arxiv_id: str) -> list[VersionRecord]:
        rows = self.conn.execute(
            "SELECT * FROM versions WHERE arxiv_id = ?",
            (arxiv_id,),
        ).fetchall()

        def version_key(v: str) -> int:
            try:
                return int(v.removeprefix("v"))
            except ValueError:
                return -1

        sorted_rows = sorted(rows, key=lambda r: version_key(str(r["version"])))
        return [
            VersionRecord(
                arxiv_id=str(r["arxiv_id"]),
                version=str(r["version"]),
                updated_date=str(r["updated_date"]),
                source_hash=str(r["source_hash"]),
                extraction_hash=(str(r["extraction_hash"]) if r["extraction_hash"] else None),
                created_at=str(r["created_at"]),
            )
            for r in sorted_rows
        ]

    def find_version_by_source_hash(
        self, *, arxiv_id: str, source_hash: str
    ) -> VersionRecord | None:
        row = self.conn.execute(
            """
            SELECT * FROM versions
            WHERE arxiv_id = ? AND source_hash = ?
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (arxiv_id, source_hash),
        ).fetchone()
        if row is None:
            return None
        return VersionRecord(
            arxiv_id=str(row["arxiv_id"]),
            version=str(row["version"]),
            updated_date=str(row["updated_date"]),
            source_hash=str(row["source_hash"]),
            extraction_hash=(str(row["extraction_hash"]) if row["extraction_hash"] else None),
            created_at=str(row["created_at"]),
        )

    def list_seen_papers(self) -> list[str]:
        rows = self.conn.execute("SELECT arxiv_id FROM papers ORDER BY arxiv_id").fetchall()
        return [str(r["arxiv_id"]) for r in rows]

    def needs_processing(self, *, arxiv_id: str, version: str, source_hash: str) -> bool:
        row = self.get_version(arxiv_id, version)
        if row is None:
            return True
        return str(row["source_hash"]) != source_hash
