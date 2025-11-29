# schema.py
from student_wellbeing_monitor.database.db_core import get_conn


def init_db_schema():
    """Create all SQLite tables for the system."""
    conn = get_conn()
    cur = conn.cursor()

    # --------------------
    # students
    # --------------------
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS students (
            student_id TEXT PRIMARY KEY,
            name       TEXT NOT NULL,
            email      TEXT
        )
    """
    )

    # --------------------
    # programme
    # --------------------
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS programme (
            programme_id     TEXT PRIMARY KEY,
            programme_name   TEXT NOT NULL,
            programme_code   TEXT
        )
    """
    )

    # --------------------
    # modules
    # --------------------
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS modules (
            module_id    INTEGER
            module_code  TEXT PRIMARY KEY,
            module_name  TEXT NOT NULL
        )
    """
    )

    # --------------------
    # wellbeing
    # --------------------
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS wellbeing (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id    INTEGER NOT NULL,
            week          INTEGER NOT NULL,
            stress_level  INTEGER,
            hours_slept   INTEGER,
            comment       TEXT,
            FOREIGN KEY(student_id) REFERENCES students(student_id)
        )
    """
    )

    # # --------------------
    # # attendance
    # # --------------------
    # cur.execute(
    #     """
    #     CREATE TABLE IF NOT EXISTS attendance (
    #         id          INTEGER PRIMARY KEY AUTOINCREMENT,
    #         student_id  INTEGER NOT NULL,
    #         module_code TEXT NOT NULL,
    #         week        INTEGER NOT NULL,
    #         status      TEXT NOT NULL,
    #         FOREIGN KEY(student_id) REFERENCES students(student_id)
    #     )
    # """
    # )

    # # --------------------
    # # submissions
    # # --------------------
    # cur.execute(
    #     """
    #     CREATE TABLE IF NOT EXISTS submissions (
    #         id           INTEGER PRIMARY KEY AUTOINCREMENT,
    #         student_id   INTEGER NOT NULL,
    #         module_code  TEXT NOT NULL,
    #         submitted    INTEGER NOT NULL,   -- 0/1
    #         grade        REAL,               -- allow NULL
    #         FOREIGN KEY(student_id) REFERENCES students(student_id)
    #     )
    # """
    # )

    # # --------------------
    # # student_modules (relation table)
    # # --------------------
    # cur.execute(
    #     """
    #     CREATE TABLE IF NOT EXISTS student_modules (
    #         id          INTEGER PRIMARY KEY AUTOINCREMENT,
    #         student_id  INTEGER NOT NULL,
    #         module_code TEXT NOT NULL,
    #         FOREIGN KEY(student_id) REFERENCES students(student_id),
    #         FOREIGN KEY(module_code) REFERENCES modules(module_code)
    #     )
    # """
    # )

    # # --------------------
    # # user accounts
    # # --------------------
    # cur.execute(
    #     """
    #     CREATE TABLE IF NOT EXISTS users (
    #         id            INTEGER PRIMARY KEY AUTOINCREMENT,
    #         username      TEXT UNIQUE NOT NULL,
    #         password_hash TEXT NOT NULL,
    #         role          TEXT NOT NULL
    #     )
    # """
    # )

    conn.commit()
    conn.close()
    print("Database schema initialized.")
