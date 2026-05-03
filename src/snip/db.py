import os
import sqlite3
from datetime import datetime
from pathlib import Path

from .models import Snippet


SCHEMA = """
CREATE TABLE IF NOT EXISTS snippets (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    code        TEXT    NOT NULL,
    language    TEXT    NOT NULL DEFAULT '',
    description TEXT    NOT NULL DEFAULT '',
    tags        TEXT    NOT NULL DEFAULT '',
    created_at  TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_snippets_created ON snippets(created_at);
"""


class Database:
    def __init__(self, path: Path | None = None):
        self.path = path or Path.home() / ".snip" / "snippets.db"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        is_new = not self.path.exists()
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)
        self.conn.commit()
        # Tighten permissions on POSIX. Windows has no equivalent we care about here.
        if is_new and os.name != "nt":
            try:
                os.chmod(self.path, 0o600)
            except OSError:
                pass

    def add(self, code: str, language: str, description: str, tags: list[str]) -> int:
        cur = self.conn.execute(
            "INSERT INTO snippets (code, language, description, tags, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (code, language, description, ",".join(tags), datetime.utcnow().isoformat()),
        )
        self.conn.commit()
        return cur.lastrowid

    def get(self, snippet_id: int) -> Snippet | None:
        row = self.conn.execute(
            "SELECT * FROM snippets WHERE id = ?", (snippet_id,)
        ).fetchone()
        return self._row_to_snippet(row) if row else None

    def all(self) -> list[Snippet]:
        rows = self.conn.execute(
            "SELECT * FROM snippets ORDER BY created_at DESC"
        ).fetchall()
        return [self._row_to_snippet(r) for r in rows]

    def search(self, query: str) -> list[Snippet]:
        tokens = [t for t in query.lower().split() if t]
        if not tokens:
            return []

        clauses = []
        params: list[str] = []
        for tok in tokens:
            clauses.append(
                "(LOWER(code) LIKE ? OR LOWER(description) LIKE ? "
                " OR LOWER(tags) LIKE ? OR LOWER(language) LIKE ?)"
            )
            like = f"%{tok}%"
            params.extend([like, like, like, like])

        sql = (
            "SELECT * FROM snippets WHERE "
            + " AND ".join(clauses)
            + " ORDER BY created_at DESC"
        )
        rows = self.conn.execute(sql, params).fetchall()
        return [self._row_to_snippet(r) for r in rows]

    def update_code(self, snippet_id: int, code: str) -> bool:
        cur = self.conn.execute(
            "UPDATE snippets SET code = ? WHERE id = ?", (code, snippet_id)
        )
        self.conn.commit()
        return cur.rowcount > 0

    def delete(self, snippet_id: int) -> bool:
        cur = self.conn.execute("DELETE FROM snippets WHERE id = ?", (snippet_id,))
        self.conn.commit()
        return cur.rowcount > 0

    def size_bytes(self) -> int:
        return self.path.stat().st_size if self.path.exists() else 0

    def count(self) -> int:
        return self.conn.execute("SELECT COUNT(*) FROM snippets").fetchone()[0]

    @staticmethod
    def _row_to_snippet(row: sqlite3.Row) -> Snippet:
        tags = [t for t in (row["tags"] or "").split(",") if t]
        return Snippet(
            id=row["id"],
            code=row["code"],
            language=row["language"] or "",
            description=row["description"] or "",
            tags=tags,
            created_at=datetime.fromisoformat(row["created_at"]),
        )
