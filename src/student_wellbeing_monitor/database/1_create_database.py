# 1_create_database.py
# 作用：创建一张全新的、完美的 student.db，包含所有老师爱看的表
# 1_create_database.py 
import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(
    BASE_DIR,
    "..", "..", "..",
    "database", "data", "student.db"
)
DB_PATH = os.path.normpath(DB_PATH)

DATA_DIR = os.path.dirname(DB_PATH)


if os.path.exists(DB_PATH):
    os.remove(DB_PATH)


os.makedirs(DATA_DIR, exist_ok=True)
conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

sql = """
PRAGMA foreign_keys = ON;

-- 1. 课程表
CREATE TABLE courses (
    course_id   TEXT PRIMARY KEY,
    course_name TEXT NOT NULL,
    department  TEXT
);

-- 2. 学生表 
CREATE TABLE students (
    student_id  TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    email       TEXT UNIQUE,
    course_id   TEXT NOT NULL,
    FOREIGN KEY (course_id) REFERENCES courses(course_id)
);

-- 3. 其他表
CREATE TABLE attendance (
    attendance_id  INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id     TEXT NOT NULL,
    week           INTEGER NOT NULL,
    attended       INTEGER NOT NULL,
    FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE,
    UNIQUE(student_id, week)
);

CREATE TABLE wellbeing (
    survey_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id     TEXT NOT NULL,
    week           INTEGER NOT NULL,
    stress_level   INTEGER CHECK(stress_level BETWEEN 1 AND 5),
    hours_slept    REAL,
    FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE,
    UNIQUE(student_id, week)
);

CREATE TABLE grades (
    student_id     TEXT PRIMARY KEY,
    final_grade    REAL CHECK(final_grade BETWEEN 0 AND 100),
    FOREIGN KEY (student_id) REFERENCES students(student_id)
);

CREATE TABLE users (
    user_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    username       TEXT UNIQUE NOT NULL,
    password_hash  TEXT NOT NULL,
    role           TEXT NOT NULL
);
"""

cur.executescript(sql)
conn.commit()
conn.close()
print("第一步 完美数据库结构创建成功！）")