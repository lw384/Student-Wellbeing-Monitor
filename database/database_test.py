# database_test.py

import os
import sqlite3
import pytest

import db


# 1. 测试数据库环境 fixture

@pytest.fixture(scope="function")
def test_db(tmp_path, monkeypatch):
    """
    每个测试函数都会使用一个全新的数据库文件：
    - 在 tmp_path 下创建一个 test_student.db
    - 创建最小可用的表结构（students / attendance / wellbeing / users）
    - 然后把 db.DB_PATH 指向这个测试数据库
    """
    db_path = tmp_path / "test_student.db"

    # 创建测试用数据库和表结构（你可以复制 1_create_database.py 里的 SQL 到这里）
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # 开启外键
    cur.execute("PRAGMA foreign_keys = ON;")

    # TODO：这里的表结构需要你根据自己的 1_create_database.py 来改一下
    cur.executescript("""
    CREATE TABLE courses (
        course_id   TEXT PRIMARY KEY,
        course_name TEXT NOT NULL,
        department  TEXT NOT NULL
    );

    CREATE TABLE students (
        student_id TEXT PRIMARY KEY,
        name       TEXT NOT NULL,
        email      TEXT,
        course_id  TEXT NOT NULL,
        FOREIGN KEY (course_id) REFERENCES courses(course_id)
    );

    CREATE TABLE attendance (
        attendance_id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id    TEXT NOT NULL,
        week          INTEGER NOT NULL,
        attended      INTEGER NOT NULL,        -- 0 = 缺席, 1 = 出席
        FOREIGN KEY (student_id) REFERENCES students(student_id)
    );

    CREATE TABLE wellbeing (
        survey_id    INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id   TEXT NOT NULL,
        week         INTEGER NOT NULL,
        stress_level INTEGER NOT NULL,         -- 1-5
        hours_slept  REAL NOT NULL,           -- 0-24
        FOREIGN KEY (student_id) REFERENCES students(student_id)
    );

    CREATE TABLE users (
        user_id       INTEGER PRIMARY KEY AUTOINCREMENT,
        username      TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role          TEXT NOT NULL
    );

    CREATE TABLE grades (
        student_id TEXT PRIMARY KEY,
        final_grade REAL NOT NULL,
        FOREIGN KEY (student_id) REFERENCES students(student_id)
    );
    """)

    conn.commit()
    conn.close()

    # 用 monkeypatch 把 db.DB_PATH 改成指向这个测试数据库
    monkeypatch.setattr(db, "DB_PATH", str(db_path))

    # fixture 的返回值，这里我们不需要返回 conn，因为 db.get_conn 每次会新建连接
    yield

    # 测试结束后自动清理


# 2. 学生相关测试（Student）

def test_insert_and_get_student(test_db):
    """
    场景：
    - 插入一条学生记录
    - 再通过查询函数拿出来
    - 检查字段是否正确
    """
    # 准备：先插入一个课程，因为 students 有 course_id 外键
    conn = db.get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO courses (course_id, course_name, department) VALUES (?, ?, ?)",
        ("CS101", "Intro to CS", "CS")
    )
    conn.commit()
    conn.close()

    db.insert_student("S001", "Alice", "alice@example.com", "CS101")

    # 查询函数get_student_information / get_all_students
    # get_student_information(student_id) 返回 dict
    info = db.get_student_information("S001")

    assert info["student_id"] == "S001"
    assert info["name"] == "Alice"
    assert info["email"] == "alice@example.com"
    assert info["course_id"] == "CS101"


# 3. 出勤相关测试（Attendance）


def test_add_attendance_and_get_rate(test_db):
    """
    场景：
    - 给某个学生插入若干周的出勤记录（0/1）
    - 计算出勤率
    - 验证出勤率是否正确
    """
    # 先插课程 + 学生
    conn = db.get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO courses (course_id, course_name, department) VALUES (?, ?, ?)",
        ("CS101", "Intro to CS", "CS")
    )
    cur.execute(
        "INSERT INTO students (student_id, name, email, course_id) VALUES (?, ?, ?, ?)",
        ("S001", "Alice", "alice@example.com", "CS101")
    )
    conn.commit()
    conn.close()

    db.add_attendance("S001", 1, 1)  # week1 到课
    db.add_attendance("S001", 2, 1)  # week2 到课
    db.add_attendance("S001", 3, 0)  # week3 缺课

    # 假设get_attendance_rate(student_id) 返回一个 0-1 之间的浮点数
    rate = db.get_attendance_rate("S001")

    # 应该是 2/3
    assert abs(rate - 2/3) < 1e-6


# 4. Wellbeing 相关测试

def test_weekly_wellbeing_summary_basic(test_db):
    """
    场景：
    - 插入某几周的 wellbeing 记录
    - 计算 week1~week2 的平均压力、平均睡眠
    - 检查结果是否符合手工计算
    """
    # 插课程 + 学生
    conn = db.get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO courses (course_id, course_name, department) VALUES (?, ?, ?)",
        ("CS101", "Intro to CS", "CS")
    )
    cur.execute(
        "INSERT INTO students (student_id, name, email, course_id) VALUES (?, ?, ?, ?)",
        ("S001", "Alice", "alice@example.com", "CS101")
    )
    conn.commit()
    conn.close()

    # 假设 add_wellbeing(student_id, week, stress_level, hours_slept)
    db.add_wellbeing("S001", 1, 3, 7.0)
    db.add_wellbeing("S001", 1, 5, 5.0)
    db.add_wellbeing("S001", 2, 4, 6.0)

    # weekly_wellbeing_summary(start_week, end_week)
    # 返回结构类似：{ week: {"avg_stress": x, "avg_sleep": y, "count": n}, ... }
    summary = db.weekly_wellbeing_summary(1, 2)

    # week1: stress = (3+5)/2 = 4, sleep = (7+5)/2 = 6, count = 2
    assert 1 in summary
    assert abs(summary[1]["avg_stress"] - 4.0) < 1e-6
    assert abs(summary[1]["avg_sleep"] - 6.0) < 1e-6
    assert summary[1]["count"] == 2

    # week2: stress = 4, sleep = 6, count = 1
    assert 2 in summary
    assert abs(summary[2]["avg_stress"] - 4.0) < 1e-6
    assert abs(summary[2]["avg_sleep"] - 6.0) < 1e-6
    assert summary[2]["count"] == 1


# 5. 高压力 / 风险学生测试

def test_get_continuous_high_stress_students(test_db):
    """
    场景：
    - 为两个学生插入多周的压力数据
    - 其中一个连续 3 周压力高，另一个只有零散高
    - 只应该识别出连续 3 周高压的那个学生
    """
    conn = db.get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO courses (course_id, course_name, department) VALUES (?, ?, ?)",
        ("CS101", "Intro to CS", "CS")
    )
    cur.execute("INSERT INTO students (student_id, name, email, course_id) VALUES (?, ?, ?, ?)",
                ("S001", "Alice", "alice@example.com", "CS101"))
    cur.execute("INSERT INTO students (student_id, name, email, course_id) VALUES (?, ?, ?, ?)",
                ("S002", "Bob", "bob@example.com", "CS101"))
    conn.commit()
    conn.close()

    # Alice：week1,2,3 压力都很高（>=4）
    db.add_wellbeing("S001", 1, 4, 6.0)
    db.add_wellbeing("S001", 2, 5, 5.0)
    db.add_wellbeing("S001", 3, 4, 7.0)

    # Bob：只有 week1 和 week3 压力高，中间断掉
    db.add_wellbeing("S002", 1, 4, 7.0)
    db.add_wellbeing("S002", 3, 5, 5.0)

    # 假设 get_continuous_high_stress_students() 返回一个列表，每个元素是 dict，包含 student_id
    result = db.get_continuous_high_stress_students()

    sids = {row["student_id"] for row in result}
    assert "S001" in sids
    assert "S002" not in sids


# 6. 用户 / 登录 / 权限测试

def test_create_user_and_login(test_db):
    """
    场景：
    - 用 create_user 创建一个用户（密码明文 123）
    - 用 check_login(username, "123") 检查是否能登录
    - 再检查角色获取是否正确
    """
    # 创建用户
    uid = db.create_user("swo", "123", "swo")
    assert uid is not None

    # 登录应该成功
    ok = db.check_login("swo", "123")
    assert ok is True

    # 假设 get_user_role(username) 返回 role 字符串
    role = db.get_user_role("swo")
    assert role == "swo"


def test_get_student_info_by_role(test_db):
    """
    场景：
    - 同一个学生
    - 用 course director 登录看信息
    - 用 wellbeing officer 登录看信息
    - 假设他们看到的字段不同（例如 CD 看不到敏感字段）
    """
    # 准备：插课程+学生
    conn = db.get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO courses (course_id, course_name, department) VALUES (?, ?, ?)",
        ("CS101", "Intro to CS", "CS")
    )
    cur.execute(
        "INSERT INTO students (student_id, name, email, course_id) VALUES (?, ?, ?, ?)",
        ("S001", "Alice", "alice@example.com", "CS101")
    )
    conn.commit()
    conn.close()
"""
 # 创建两个用户：cd 和 swo
    db.create_user("cd_user", "123", "cd")
    db.create_user("swo_user", "123", "swo")

    # 假设你有 get_student_info(username, student_id) 函数，
    # 根据角色返回不同信息（下面只是一个示例断言，你需要根据自己实现来改）
    cd_view = db.get_student_info("cd_user", "S001")
    swo_view = db.get_student_info("swo_user", "S001")

    # 举例：cd 不能看到 email，而 swo 可以看到
    assert "email" not in cd_view
    assert "email" in swo_view
    assert swo_view["email"] == "alice@example.com"
"""
   
