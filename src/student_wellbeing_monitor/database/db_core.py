# db_core.py
import os
from pathlib import Path
import sqlite3
import hashlib


PROJECT_ROOT = Path(__file__).resolve().parents[3]

DB_PATH = PROJECT_ROOT / "database" / "student.db"


def get_conn(row_factory=sqlite3.Row):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.row_factory = row_factory
    return conn


def _hash_pwd(pwd: str) -> str:
    """Simple SHA-256 password hashing."""
    return hashlib.sha256(pwd.encode("utf-8")).hexdigest()
