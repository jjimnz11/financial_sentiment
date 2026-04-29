"""
src/utils/storage.py
Helpers para persistencia: SQLite (cache de headlines) y Parquet (series temporales).
"""

import json
import sqlite3
import hashlib
from datetime import datetime
from pathlib import Path

import pandas as pd

from src.utils.config_loader import get_path
from src.utils.logger import get_logger

logger = get_logger(__name__)


# ─────────────────────────────────────────────
# SQLite cache — evita re-scrapear URLs ya vistas
# ─────────────────────────────────────────────

class HeadlineCache:
    """Cache SQLite para titulares ya scrapeados."""

    def __init__(self, db_path: Path | None = None):
        self.db_path = db_path or get_path("data", "cache") / "headlines.db"
        self._init_db()

    def _init_db(self):
        with self._conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS headlines (
                    id          TEXT PRIMARY KEY,
                    source      TEXT NOT NULL,
                    title       TEXT NOT NULL,
                    url         TEXT,
                    published   TEXT,
                    scraped_at  TEXT NOT NULL,
                    raw_json    TEXT
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_published ON headlines(published)")

    def _conn(self):
        return sqlite3.connect(self.db_path)

    @staticmethod
    def _make_id(title: str, source: str) -> str:
        return hashlib.md5(f"{source}::{title}".encode()).hexdigest()

    def exists(self, title: str, source: str) -> bool:
        id_ = self._make_id(title, source)
        with self._conn() as conn:
            row = conn.execute("SELECT 1 FROM headlines WHERE id=?", (id_,)).fetchone()
        return row is not None

    def insert(self, headline: dict) -> bool:
        """Inserta un titular. Devuelve True si es nuevo, False si ya existía."""
        id_ = self._make_id(headline["title"], headline["source"])
        if self.exists(headline["title"], headline["source"]):
            return False
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO headlines VALUES (?,?,?,?,?,?,?)",
                (
                    id_,
                    headline["source"],
                    headline["title"],
                    headline.get("url"),
                    headline.get("published"),
                    datetime.utcnow().isoformat(),
                    json.dumps(headline),
                ),
            )
        return True

    def get_since(self, since: datetime, source: str | None = None) -> pd.DataFrame:
        """Recupera headlines desde una fecha. Opcionalmente filtra por fuente."""
        query = "SELECT * FROM headlines WHERE published >= ?"
        params = [since.isoformat()]
        if source:
            query += " AND source = ?"
            params.append(source)
        with self._conn() as conn:
            df = pd.read_sql_query(query, conn, params=params, parse_dates=["published", "scraped_at"])
        return df

    def count(self) -> int:
        with self._conn() as conn:
            return conn.execute("SELECT COUNT(*) FROM headlines").fetchone()[0]


# ─────────────────────────────────────────────
# Parquet — series temporales procesadas
# ─────────────────────────────────────────────

def save_parquet(df: pd.DataFrame, name: str, subfolder: str = "processed") -> Path:
    """Guarda un DataFrame como Parquet en data/{subfolder}/{name}.parquet"""
    path = get_path("data", subfolder) / f"{name}.parquet"
    df.to_parquet(path, index=True, compression="snappy")
    logger.info(f"Saved {len(df):,} rows → {path.name}")
    return path


def load_parquet(name: str, subfolder: str = "processed") -> pd.DataFrame:
    """Carga un Parquet desde data/{subfolder}/{name}.parquet"""
    path = get_path("data", subfolder) / f"{name}.parquet"
    if not path.exists():
        raise FileNotFoundError(f"Parquet not found: {path}")
    df = pd.read_parquet(path)
    logger.info(f"Loaded {len(df):,} rows ← {path.name}")
    return df
