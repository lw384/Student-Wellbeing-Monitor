# db_core.py
import os
from pathlib import Path
import sqlite3
import hashlib


PROJECT_ROOT = Path(__file__).resolve().parents[3]

DB_PATH = PROJECT_ROOT / "database" / "data" / "student.db"


def get_conn(row_factory=None):
    """Get SQLite connection with optional row_factory."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")

    if row_factory is not None:
        conn.row_factory = row_factory

    return conn


def _hash_pwd(pwd: str) -> str:
    """Simple SHA-256 password hashing."""
    return hashlib.sha256(pwd.encode("utf-8")).hexdigest()
