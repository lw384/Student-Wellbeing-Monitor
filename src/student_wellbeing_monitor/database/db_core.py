# db_core.py
import os
import sqlite3
import hashlib

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DB_PATH = os.path.join(
    BASE_DIR,
    "..", "..", "..",
    "database", "data", "student.db"
)
DB_PATH = os.path.normpath(DB_PATH)


def get_conn():
    """Return a new SQLite connection."""
    return sqlite3.connect(DB_PATH)


def _hash_pwd(pwd: str) -> str:
    """Simple SHA-256 password hashing."""
    return hashlib.sha256(pwd.encode("utf-8")).hexdigest()
