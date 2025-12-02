# test_database.py - updated for modularised database package

import os
import sqlite3
import pytest
import sys   #导入sys模块
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SRC_DIR))

from student_wellbeing_monitor.database import db_core, create, read, update, delete


# ---------------------------------------------------------------------------
# 1. 每个测试用一个全新的临时数据库
# ---------------------------------------------------------------------------

@pytest.fixture(scope="function")
def test_db(tmp_path, monkeypatch):
    """
    对每个测试：
    - 把 db_core.DB_PATH 指到 tmp_path 下面
    - 创建所有需要用到的表
    - 测试结束后尝试删除这个临时 db 文件（Windows 下忽略正在占用的错误）
    """
    # 1) 把 DB_PATH 改到临时目录
    db_file = tmp_path / "test_student.db"
    monkeypatch.setattr(db_core, "DB_PATH", str(db_file))

    # 2) 建表
    conn = sqlite3.connect(db_core.DB_PATH)
    cur = conn.cursor()
    cur.executescript(
        """
        PRAGMA foreign_keys = ON;

        CREATE TABLE students (
            student_id   INTEGER PRIMARY KEY AUTOINCREMENT,
            name         TEXT NOT NULL,
            email        TEXT UNIQUE
        );

        CREATE TABLE wellbeing (
            survey_id     INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id    INTEGER NOT NULL,
            week          INTEGER NOT NULL,
            stress_level  INTEGER CHECK(stress_level BETWEEN 1 AND 5),
            hours_slept   REAL,
            FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE,
            UNIQUE(student_id, week)
        );

        CREATE TABLE attendance (
            attendance_id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id    INTEGER NOT NULL,
            week          INTEGER NOT NULL,
            status        TEXT NOT NULL,
            FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE,
            UNIQUE(student_id, week)
        );

        CREATE TABLE submissions (
            submission_id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id    INTEGER NOT NULL,
            assignment_id TEXT NOT NULL,
            due_date      TEXT,
            submit_date   TEXT,
            grade         REAL,
            FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE
        );

        CREATE TABLE grades (
            student_id  INTEGER PRIMARY KEY,
            final_grade REAL CHECK(final_grade BETWEEN 0 AND 100),
            FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE
        );

        CREATE TABLE users (
            user_id       INTEGER PRIMARY KEY AUTOINCREMENT,
            username      TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role          TEXT NOT NULL
        );
        """
    )
    conn.commit()
    conn.close()

    # 交给具体测试用例执行
    yield

    # 3) 测试结束后尝试删除临时数据库文件
    try:
        if os.path.exists(db_core.DB_PATH):
            os.remove(db_core.DB_PATH)
    except PermissionError:
        # Windows 下若还有连接占用文件，就忽略这个错误
        pass


# ---------------------------------------------------------------------------
# 2. 基础 CRUD 测试
# ---------------------------------------------------------------------------

def test_insert_student_and_read_back(test_db):
    # 通过 create.insert_student 插入
    sid = create.insert_student("Alice", "alice@example.com")
    assert isinstance(sid, int)

    # read.get_all_students / get_student_information 读回
    students = read.get_all_students()
    assert len(students) == 1
    row = students[0]          # (student_id, name, email)
    assert row[0] == sid
    assert row[1] == "Alice"
    assert row[2] == "alice@example.com"

    info = read.get_student_information(sid)  # (student_id, name)
    assert info[0] == sid
    assert info[1] == "Alice"


def test_attendance_and_rate(test_db):
    sid = create.insert_student("Alice", "alice@example.com")

    # 三周：出勤、出勤、缺勤 -> 出勤率 2/3
    create.add_attendance(sid, 1, "present")
    create.add_attendance(sid, 2, "present")
    create.add_attendance(sid, 3, "absent")

    rate = read.get_attendance_rate(sid)
    assert abs(rate - 2 / 3) < 1e-6


def test_wellbeing_summary_basic(test_db):
    sid = create.insert_student("Alice", "alice@example.com")

    # week 1 & 2 wellbeing
    create.add_wellbeing(sid, 1, stress=3, sleep_hours=7.0)
    create.add_wellbeing(sid, 2, stress=5, sleep_hours=5.0)

    # [(week, avg_stress, avg_sleep, count), ...]
    summary = read.weekly_wellbeing_summary(1, 2)
    assert len(summary) == 2

    data = {week: (avg_s, avg_h, cnt) for week, avg_s, avg_h, cnt in summary}

    w1 = data[1]
    assert abs(w1[0] - 3.0) < 1e-6
    assert abs(w1[1] - 7.0) < 1e-6
    assert w1[2] == 1

    w2 = data[2]
    assert abs(w2[0] - 5.0) < 1e-6
    assert abs(w2[1] - 5.0) < 1e-6
    assert w2[2] == 1


def test_continuous_high_stress_students(test_db):
    """
    Alice: week1,2,3 都 >=4  -> 应该被检出
    Bob:   week1,3 高压，中间断掉 -> 不应该被检出
    """
    sid_alice = create.insert_student("Alice", "alice@example.com")
    sid_bob = create.insert_student("Bob", "bob@example.com")

    # Alice 1-3 周连续高压
    create.add_wellbeing(sid_alice, 1, 4, 7.0)
    create.add_wellbeing(sid_alice, 2, 4, 6.0)
    create.add_wellbeing(sid_alice, 3, 5, 5.0)

    # Bob 1、3 周高压但不连续
    create.add_wellbeing(sid_bob, 1, 4, 7.0)
    create.add_wellbeing(sid_bob, 3, 5, 5.0)

    result = read.get_continuous_high_stress_students()
    sids = {row["student_id"] for row in result}
    assert sid_alice in sids
    assert sid_bob not in sids


# ---------------------------------------------------------------------------
# 3. 用户 / 登录 / 权限相关测试
# ---------------------------------------------------------------------------

def test_create_user_and_login(test_db):
    uid = create.create_user("swo", "123", "swo")
    assert uid is not None

    assert read.check_login("swo", "123") is True
    assert read.check_login("swo", "wrong") is False

    role = read.get_user_role("swo")
    assert role == "swo"


def test_get_student_info_for_roles(test_db):
    # 准备一个学生 + 一些数据
    sid = create.insert_student("Alice", "alice@example.com")
    create.add_attendance(sid, 1, "present")
    create.add_attendance(sid, 2, "absent")
    create.add_wellbeing(sid, 1, 4, 7.0)
    create.add_submission(sid, "A1", "2024-01-01", "2024-01-01", 70.0)

    # 两个不同角色的用户
    create.create_user("cd_user", "123", "cd")
    create.create_user("swo_user", "123", "swo")

    # CD 视角: (student_id, name, attendance_rate)
    cd_view = read.get_student_info("cd_user", sid)
    assert cd_view[0] == sid
    assert cd_view[1] == "Alice"
    assert 0.0 <= cd_view[2] <= 1.0

    # SWO 视角: [basic_info, attendance_list, wellbeing_list, submissions_list]
    swo_view = read.get_student_info("swo_user", sid)
    assert isinstance(swo_view, list)
    assert len(swo_view) == 4

    basic, att, wb, subs = swo_view
    assert basic[0] == sid
    assert basic[1] == "Alice"
    assert len(att) == 2
    assert len(wb) == 1
    assert len(subs) == 1


# ---------------------------------------------------------------------------
# 4. Update / Delete 测试
# ---------------------------------------------------------------------------

def test_update_wellbeing_and_grade(test_db):
    sid = create.insert_student("Alice", "alice@example.com")
    create.add_wellbeing(sid, 1, 3, 7.0)

    # 更新压力值
    update.update_wellbeing_stress(sid, 1, 5)
    records = read.get_wellbeing_by_student(sid)
    assert len(records) == 1
    # get_wellbeing_by_student 返回: (week, stress_level, hours_slept)
    assert records[0][1] == 5

    # 插入一条成绩，再用 update_final_grade 更新
    conn = db_core.get_conn()
    cur = conn.cursor()
    cur.execute("INSERT INTO grades (student_id, final_grade) VALUES (?, ?)", (sid, 60.0))
    conn.commit()
    conn.close()

    update.update_final_grade(sid, 80.0)

    conn = db_core.get_conn()
    cur = conn.cursor()
    cur.execute("SELECT final_grade FROM grades WHERE student_id = ?", (sid,))
    grade = cur.fetchone()[0]
    conn.close()
    assert grade == 80.0


def test_delete_student(test_db):
    # 先插入一个学生和一些关联记录
    sid = create.insert_student("Alice", "alice@example.com")
    create.add_wellbeing(sid, 1, 3, 7.0)
    create.add_attendance(sid, 1, "present")
    create.add_submission(sid, "A1", "2024-01-01", "2024-01-01", 70.0)

    # 调用待测函数
    delete.delete_student(sid)

    students = read.get_all_students()
    assert students == []
