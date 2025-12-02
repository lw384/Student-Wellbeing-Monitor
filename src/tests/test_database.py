# tests/test_database.py
import sys
from pathlib import Path
import sqlite3

import pytest

# --------- 跨包导入：把项目 src 目录加到 sys.path ----------
SRC_DIR = Path(__file__).resolve().parents[1]
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


# ========= 基础 fixture：临时数据库 + 建表 =========
@pytest.fixture
def setup_db(tmp_path, monkeypatch):
    """
    为每个测试创建一个独立的临时 student.db，并初始化 schema。
    所有数据库脚本都会通过 db_core.get_conn() 指向这个文件。
    """
    from student_wellbeing_monitor.database import db_core, schema

    db_file = tmp_path / "student.db"
    # 让 db_core 使用临时 DB 路径
    monkeypatch.setattr(db_core, "DB_PATH", db_file)

    # 初始化表结构
    schema.init_db_schema()

    return db_file


# ========= 填充一份示例数据，用于大多数测试 =========
@pytest.fixture
def sample_data(setup_db):
    """
    插入一个简单但结构完整的数据集，方便各个读写/统计函数使用。

    programme: P1, P2
    students : S1, S2 (P1), S3 (P2)
    modules  : M1, M2 (P1), M3 (P2)
    wellbeing、attendance 数据用于后面的统计函数。
    """
    from student_wellbeing_monitor.database import create

    # Programmes
    create.insert_programme("P1", "Programme 1", "P1")
    create.insert_programme("P2", "Programme 2", "P2")

    # Students
    create.insert_student("S1", "Alice", "P1", "alice@example.com")
    create.insert_student("S2", "Bob", "P1", "bob@example.com")
    create.insert_student("S3", "Carol", "P2", "carol@example.com")

    # Modules
    create.insert_module("M1", "Module 1", "M1", "P1")
    create.insert_module("M2", "Module 2", "M2", "P1")
    create.insert_module("M3", "Module 3", "M3", "P2")

    # Student–Module
    create.insert_student_module("S1", "M1")
    create.insert_student_module("S1", "M2")
    create.insert_student_module("S2", "M1")

    # Wellbeing
    # S1: weeks 1–3
    create.insert_wellbeing("S1", 1, 3, 7.0, "ok")
    create.insert_wellbeing("S1", 2, 4, 5.5, "stressed")
    create.insert_wellbeing("S1", 3, 5, 4.0, "very stressed")
    # S2: weeks 1–2
    create.insert_wellbeing("S2", 1, 2, 8.0)
    create.insert_wellbeing("S2", 2, 4, 5.0)
    # S3: week 1
    create.insert_wellbeing("S3", 1, 5, 4.5)

    # Attendance  (status: 1 present / 0 absent)
    # S1 (M1): 1,0,1  → 2/3
    create.insert_attendance("S1", "M1", 1, 1)
    create.insert_attendance("S1", "M1", 2, 0)
    create.insert_attendance("S1", "M1", 3, 1)
    # S2 (M1): 1,1   → 1.0
    create.insert_attendance("S2", "M1", 1, 1)
    create.insert_attendance("S2", "M1", 2, 1)
    # S3 (M3): 0     → 0.0
    create.insert_attendance("S3", "M3", 1, 0)

    return None


# ========= 基础结构测试 =========
def test_schema_creates_all_tables(setup_db):
    from student_wellbeing_monitor.database import db_core

    conn = db_core.get_conn()
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    table_names = {row[0] for row in cur.fetchall()}
    conn.close()

    # 核心业务相关的几张表
    expected = {
        "programme",
        "student",
        "module",
        "student_module",
        "wellbeing",
        "attendance",
        "submission",
        "user",
    }
    assert expected.issubset(table_names)


# ========= Programme / Student 基础读写 =========
def test_insert_programmes_and_get_programmes(sample_data):
    from student_wellbeing_monitor.database import read

    programmes = read.get_programmes()
    # get_programmes 使用 Row 工厂，可以用列名访问
    codes = [row["programme_code"] for row in programmes]

    assert codes == ["P1", "P2"]
    assert programmes[0]["programme_id"] == "P1"
    assert programmes[0]["programme_name"] == "Programme 1"


def test_insert_students_and_query(sample_data):
    from student_wellbeing_monitor.database import read

    all_students = read.get_all_students()
    assert len(all_students) == 3

    p1_students = read.get_students_by_programme("P1")
    p1_names = {row["name"] for row in p1_students}
    assert p1_names == {"Alice", "Bob"}

    s1 = read.get_student_by_id("S1")
    assert s1["name"] == "Alice"
    assert s1["programme_id"] == "P1"


def test_student_module_unique_constraint(sample_data):
    from student_wellbeing_monitor.database import create

    # 已在 sample_data 中插入过一次 (S1, M1)，再次插入应违反 UNIQUE 约束
    with pytest.raises(sqlite3.IntegrityError):
        create.insert_student_module("S1", "M1")


# ========= Wellbeing 基础读写 =========
def test_wellbeing_count_and_weeks(sample_data):
    from student_wellbeing_monitor.database import read

    assert read.count_wellbeing() == 6
    assert read.get_all_weeks() == [1, 2, 3]


def test_get_wellbeing_records_filters(sample_data):
    from student_wellbeing_monitor.database import read

    all_rows = read.get_wellbeing_records(1, 3)
    assert len(all_rows) == 6

    p1_rows = read.get_wellbeing_records(1, 3, programme_id="P1")
    # P1: S1(3 周) + S2(2 周) -> 5
    assert len(p1_rows) == 5
    assert {r["student_id"] for r in p1_rows} <= {"S1", "S2"}

    s1_rows = read.get_wellbeing_records(1, 3, student_id="S1")
    assert len(s1_rows) == 3
    assert {r["week"] for r in s1_rows} == {1, 2, 3}


def test_get_wellbeing_page(sample_data):
    from student_wellbeing_monitor.database import read

    page1 = read.get_wellbeing_page(limit=2, offset=0)
    page2 = read.get_wellbeing_page(limit=2, offset=2)
    page3 = read.get_wellbeing_page(limit=2, offset=4)

    assert len(page1) == 2
    assert len(page2) == 2
    assert len(page3) == 2

    # 三页合起来应该有 6 条，并且没有重复
    all_rows = page1 + page2 + page3
    assert len({(r["student_id"], r["week"]) for r in all_rows}) == 6


def test_update_wellbeing_stress(sample_data):
    from student_wellbeing_monitor.database import read, update

    # 修改前
    before = read.get_wellbeing_records(1, 3, student_id="S1")
    week2 = [r for r in before if r["week"] == 2][0]
    assert week2["stress_level"] == 4

    # 更新
    update.update_wellbeing_stress("S1", 2, 1)

    after = read.get_wellbeing_records(1, 3, student_id="S1")
    week2_after = [r for r in after if r["week"] == 2][0]
    assert week2_after["stress_level"] == 1

"""
# ========= Attendance 相关 =========
def test_get_attendance_by_student_and_rate(sample_data):
    from student_wellbeing_monitor.database import read

    rows = read.get_attendance_by_student("S1")
    assert len(rows) == 3
    weeks = [r[0] for r in rows]
    assert weeks == [1, 2, 3]

    # 逻辑上：S1 出勤率 = 2/3
    rate = read.get_attendance_rate("S1")
    assert rate == pytest.approx(2 / 3)

    # 没有记录的学生应返回 None
    assert read.get_attendance_rate("S999") is None
"""



# ========= Wellbeing 统计函数 =========
def test_weekly_wellbeing_summary_and_high_stress(sample_data):
    from student_wellbeing_monitor.database import read

    summary = read.weekly_wellbeing_summary(1, 3)
    # 转成 dict: week -> (avg_stress, avg_sleep, count)
    by_week = {row[0]: row[1:] for row in summary}

    # week 1: stress = (3 + 2 + 5) / 3 = 10/3
    assert by_week[1][0] == pytest.approx(10 / 3)
    # week 2: stress = (4 + 4) / 2 = 4
    assert by_week[2][0] == pytest.approx(4.0)
    # week 3: stress = 5
    assert by_week[3][0] == pytest.approx(5.0)

    high = read.find_high_stress_weeks(threshold=4)
    high_weeks = {row[0] for row in high}
    assert high_weeks == {2, 3}


def test_get_at_risk_students(sample_data):
    from student_wellbeing_monitor.database import read

    at_risk = read.get_at_risk_students()
    # S1: week 2 & 3 均满足 stress>=4 & sleep<6 → at risk
    assert "S1" in at_risk
    assert at_risk["S1"] == [2, 3]
    # S2: 只有 week2 满足条件；S3: 只有 week1
    assert "S2" not in at_risk
    assert "S3" not in at_risk

"""
# ========= Attendance & Wellbeing 关联统计 =========
def test_stress_vs_attendance(sample_data):
   
    根据插入的数据，预期：
    week 1: avg_stress = (3+2+5)/3 = 10/3, attendance = 2/3
    week 2: avg_stress = 4,            attendance = 0.5
    week 3: avg_stress = 5,            attendance = 1.0
    
    from student_wellbeing_monitor.database import read

    rows = read.stress_vs_attendance()
    by_week = {row[0]: row[1:] for row in rows}

    assert by_week[1][0] == pytest.approx(10 / 3)
    assert by_week[1][1] == pytest.approx(2 / 3)

    assert by_week[2][0] == pytest.approx(4.0)
    assert by_week[2][1] == pytest.approx(0.5)

    assert by_week[3][0] == pytest.approx(5.0)
    assert by_week[3][1] == pytest.approx(1.0)

"""
"""
def test_attendance_trend_and_low_attendance(sample_data):
    
    根据插入的出勤数据：
    week1: statuses = [1,1,0] → 2/3
    week2: [0,1]             → 0.5
    week3: [1]               → 1.0

    学生出勤率：
    S1: [1,0,1] → 2/3 < 0.7  → 低出勤
    S2: [1,1]   → 1.0        → 正常
    S3: [0]     → 0.0 < 0.7  → 低出勤
    
    from student_wellbeing_monitor.database import read

    trend = read.attendance_trend()
    by_week = {row[0]: row[1] for row in trend}
    assert by_week[1] == pytest.approx(2 / 3)
    assert by_week[2] == pytest.approx(0.5)
    assert by_week[3] == pytest.approx(1.0)

    low = read.low_attendance(threshold=0.7)
    low_dict = {row[0]: row[1] for row in low}

    assert "S1" in low_dict
    assert low_dict["S1"] == pytest.approx(2 / 3)

    assert "S3" in low_dict
    assert low_dict["S3"] == pytest.approx(0.0)

    # S2 出勤率 1.0，应不在低出勤名单中
    assert "S2" not in low_dict
"""

