# schema.py
# create database schema
from student_wellbeing_monitor.database.db_core import get_conn


def init_db_schema():
    """Create all SQLite tables for the system."""
    conn = get_conn()
    cur = conn.cursor()

    # --------------------
    # programme
    # --------------------
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS programme (
            programme_id     TEXT PRIMARY KEY,
            programme_name   TEXT NOT NULL,
            programme_code   TEXT UNIQUE
        )
    """
    )

    # --------------------
    # student
    # --------------------
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS student (
            student_id TEXT PRIMARY KEY,
            name       TEXT NOT NULL,
            email      TEXT,
            programme_id TEXT NOT NULL,
            FOREIGN KEY (programme_id) REFERENCES programme(programme_id)
        )
    """
    )

    # --------------------
    # module
    # --------------------
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS module (
            module_id    TEXT PRIMARY KEY,
            module_code  TEXT UNIQUE,
            module_name  TEXT NOT NULL,
            programme_id TEXT NOT NULL,
            FOREIGN KEY (programme_id) REFERENCES programme(programme_id)
        )
    """
    )

    # --------------------
    # student_module (relation table)
    # --------------------
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS student_module (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id  TEXT NOT NULL,
            module_id   TEXT NOT NULL,
            FOREIGN KEY(student_id) REFERENCES student(student_id),
            FOREIGN KEY(module_id) REFERENCES module(module_id),
            UNIQUE(student_id, module_id)
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
            student_id    TEXT NOT NULL,
            week          INTEGER NOT NULL,
            stress_level  INTEGER CHECK(stress_level BETWEEN 1 AND 5),
            hours_slept   REAL CHECK(hours_slept BETWEEN 0 AND 12),
            comment       TEXT,
            FOREIGN KEY(student_id) REFERENCES student(student_id),
            UNIQUE(student_id, week)
        );
        """
    )

    # --------------------
    # attendance
    # --------------------
    cur.execute(
        """
       CREATE TABLE IF NOT EXISTS attendance (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id      TEXT NOT NULL,
            module_id       TEXT NOT NULL,
            week            INTEGER NOT NULL,
            session_number  INTEGER NOT NULL DEFAULT 1,   -- default 1 lesson every week
            status          INTEGER NOT NULL CHECK(status IN (0, 1)),   -- 0 absent; 1 present
            FOREIGN KEY (student_id) REFERENCES student(student_id),
            FOREIGN KEY (module_id) REFERENCES module(module_id),
            UNIQUE(student_id, module_id, week, session_number)
        );
        """
    )

    # --------------------
    # submission
    # --------------------
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS submission (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id   TEXT NOT NULL,
            module_id    TEXT NOT NULL,
            submitted    INTEGER NOT NULL CHECK(submitted IN (0, 1)),   -- 1 submitted; 0 no
            grade        REAL CHECK(grade BETWEEN 0 AND 100), 
            assignment_no  INTEGER NOT NULL DEFAULT 1, 
            due_date     TEXT NOT NULL,                -- YYYY-MM-DD
            submit_date  TEXT,                         -- NULL if not submitted
            FOREIGN KEY(student_id) REFERENCES student(student_id)
            FOREIGN KEY(module_id)  REFERENCES module(module_id),  
            UNIQUE(student_id, module_id, assignment_no)       
        )
    """
    )

    # --------------------
    # user accounts
    # --------------------
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS user (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            role          TEXT NOT NULL
        )
    """
    )

    conn.commit()
    conn.close()
    print("Database schema initialized.")
