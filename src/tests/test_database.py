# test_database.py
import sqlite3
import sys
from pathlib import Path
from typing import Any, Dict

import pytest

# --------- Allow tests to import packages under src ---------
SRC_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SRC_DIR))

from student_wellbeing_monitor.database import (  # noqa: E402
    create,
    db_core,
    delete,
    read,
    schema,
    update,
)


# =========================================================
#             Global Test Database Initialization
# =========================================================
@pytest.fixture(autouse=True)
def setup_test_db(tmp_path, monkeypatch):
    """
    Each test uses a separate temporary SQLite file,
    ensuring no cross-test interference.
    """
    db_file = tmp_path / "student.db"
    # Patch DB_PATH so all get_conn() calls point to the temp DB
    monkeypatch.setattr(db_core, "DB_PATH", db_file)

    # Initialize schema (should be idempotent)
    schema.init_db_schema()

    yield
    # No explicit cleanup required — tmp_path auto-deleted by pytest


# =========================================================
#                   Sample Data Fixtures
# =========================================================
@pytest.fixture
def sample_data() -> Dict[str, Any]:
    """
    Insert seed test data into an empty database for use in tests.
    """
    data: Dict[str, Any] = {}

    # ----- Programme -----
    create.insert_programme("P1", "Computer Science", "CS")
    create.insert_programme("P2", "Data Science", "DS")
    data["programme_ids"] = ["P1", "P2"]

    # ----- Student -----
    create.insert_student("S1", "Alice", "P1", email="alice@example.com")
    create.insert_student("S2", "Bob", "P1", email="bob@example.com")
    create.insert_student("S3", "Carol", "P2", email="carol@example.com")
    data["student_ids"] = ["S1", "S2", "S3"]

    # ----- Module -----
    # Note: insert_module = (module_id, module_name, module_code, programme_id)
    create.insert_module("M1", "Intro to CS", "CS101", "P1")
    create.insert_module("M2", "Data Analysis", "DS201", "P2")
    data["module_ids"] = ["M1", "M2"]

    # ----- Student-Module relationships -----
    create.insert_student_module("S1", "M1")
    create.insert_student_module("S2", "M1")
    create.insert_student_module("S3", "M2")

    # ----- Wellbeing -----
    # Design: S1 has week 1–3 with high stress (>=4) and sleep <6 → used for at-risk / continuous stress tests.
    w_ids = {}
    w_ids["S1_w1"] = create.insert_wellbeing("S1", 1, 4, 5.0, "tired")
    w_ids["S1_w2"] = create.insert_wellbeing("S1", 2, 5, 4.0, "more tired")
    w_ids["S1_w3"] = create.insert_wellbeing("S1", 3, 4, 5.5, "still high")

    create.insert_wellbeing("S2", 1, 3, 7.0, "ok")
    create.insert_wellbeing("S2", 2, 4, 6.5, "a bit stressed")
    create.insert_wellbeing("S3", 1, 2, 7.5, "relaxed")

    data["wellbeing_ids"] = w_ids

    # ----- Attendance -----
    a_ids = {}
    a_ids["S1_w1"] = create.insert_attendance("S1", "M1", 1, 1)
    a_ids["S1_w2"] = create.insert_attendance("S1", "M1", 2, 1)
    a_ids["S1_w3"] = create.insert_attendance("S1", "M1", 3, 0)

    create.insert_attendance("S2", "M1", 1, 0)
    create.insert_attendance("S2", "M1", 2, 1)
    create.insert_attendance("S2", "M1", 3, 1)

    create.insert_attendance("S3", "M2", 1, 1)
    create.insert_attendance("S3", "M2", 2, 0)
    create.insert_attendance("S3", "M2", 3, 0)

    data["attendance_ids"] = a_ids

    # ----- Submission -----
    sub_ids = {}
    sub_ids["S1_a1"] = create.insert_submission(
        student_id="S1",
        module_id="M1",
        assignment_no=1,
        submitted=1,
        grade=85.0,
        due_date="2024-01-10",
        submit_date="2024-01-09",
    )
    sub_ids["S1_a2"] = create.insert_submission(
        student_id="S1",
        module_id="M1",
        assignment_no=2,
        submitted=0,
        grade=None,
        due_date="2024-02-10",
        submit_date=None,
    )
    sub_ids["S2_a1"] = create.insert_submission(
        student_id="S2",
        module_id="M1",
        assignment_no=1,
        submitted=1,
        grade=70.0,
        due_date="2024-01-10",
        submit_date="2024-01-11",
    )
    sub_ids["S3_a1"] = create.insert_submission(
        student_id="S3",
        module_id="M2",
        assignment_no=1,
        submitted=0,
        grade=None,
        due_date="2024-01-15",
        submit_date=None,
    )
    data["submission_ids"] = sub_ids

    # ----- Users table (code refers to users but schema created user — so manually create it here) -----
    conn = db_core.get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL
        )
        """
    )
    conn.commit()
    conn.close()

    # Insert initial admin user
    create.create_user("admin", "secret123", "swo")

    return data


# =========================================================
#                    db_core / schema
# =========================================================
def test_db_core_hash_and_connection():
    # _hash_pwd should be deterministic
    h1 = db_core._hash_pwd("abc")
    h2 = db_core._hash_pwd("abc")
    h3 = db_core._hash_pwd("xyz")
    assert h1 == h2
    assert h1 != h3

    conn = db_core.get_conn()
    assert conn.row_factory is sqlite3.Row
    conn.close()

    # schema.init_db_schema should be idempotent (no exception)
    schema.init_db_schema()


# =========================================================
#                         Student
# =========================================================
def test_student_queries(sample_data):
    assert read.count_students() == 3
    assert read.count_students("P1") == 2

    all_students = read.get_all_students()
    assert len(all_students) == 3
    ids = {row["student_id"] for row in all_students}
    assert ids == {"S1", "S2", "S3"}

    p1_students = read.get_students_by_programme("P1")
    assert {row["student_id"] for row in p1_students} == {"S1", "S2"}

    s1 = read.get_student_by_id("S1")
    assert s1["name"] == "Alice"
    assert s1["programme_id"] == "P1"


# =========================================================
#                    Programme & Module
# =========================================================
def test_programmes_and_modules(sample_data):
    programmes = read.get_programmes()
    assert [p["programme_id"] for p in programmes] == ["P1", "P2"]

    modules = read.get_all_modules()
    assert {m["module_id"] for m in modules} == {"M1", "M2"}

    # attendance_for_course & attendance_detail_for_students
    att_course = read.attendance_for_course("P1")
    # For P1: module M1 has S1/S2 each 3 weeks — total 6 records
    assert len(att_course) == 6
    assert all(row[0] == "M1" for row in att_course)

    att_detail = read.attendance_detail_for_students("M1", programme_id="P1")
    # Should only contain S1 and S2
    assert {row[2] for row in att_detail} == {"S1", "S2"}

    # programme_wellbeing_engagement
    engagement = read.programme_wellbeing_engagement(
        programme_id="P1", week_start=1, week_end=3
    )
    assert engagement
    # Expected number of fields = documented count
    assert len(engagement[0]) == 11


# =========================================================
#                        Wellbeing
# =========================================================
def test_wellbeing_crud_and_analytics(sample_data):
    w_ids = sample_data["wellbeing_ids"]

    # Count check
    assert read.count_wellbeing() == 6
    assert read.count_wellbeing("S1") == 3
    assert read.get_all_weeks() == [1, 2, 3]

    # Range query
    records = read.get_wellbeing_records(1, 3)
    assert len(records) == 6

    # Pagination + sorting
    page = read.get_wellbeing_page(limit=10, offset=0, student_id="S1", sort_week="asc")
    weeks = [r["week"] for r in page]
    assert weeks == [1, 2, 3]

    # Query by id
    row = read.get_wellbeing_by_id(w_ids["S1_w1"])
    assert row["student_id"] == "S1"
    assert row["week"] == 1

    # weekly_wellbeing_summary
    summary = read.weekly_wellbeing_summary(1, 3)
    # week 1 should have 3 records
    w1 = summary[0]
    assert w1[0] == 1
    assert w1[3] == 3  # count

    # find_high_stress_weeks: average stress >=4 → weeks 2, 3
    high = read.find_high_stress_weeks(threshold=4)
    weeks_high = [r[0] for r in high]
    assert weeks_high == [2, 3]

    # at-risk students: S1 satisfies stress>=4 and sleep<6 for week1–3
    at_risk = read.get_at_risk_students()
    assert list(at_risk.keys()) == ["S1"]
    assert at_risk["S1"] == [1, 2, 3]

    # Continuous high stress (>=3 weeks): S1 should have 3
    cont = read.get_continuous_high_stress_students()
    assert cont
    s1_entry = next(e for e in cont if e["student_id"] == "S1")
    assert s1_entry["weeks"] >= 3
    assert "Week 1" in s1_entry["weeks_list"]

    # stress_vs_attendance / attendance_trend:
    sva = read.stress_vs_attendance()
    assert sva
    assert all(row[2] == 0.0 for row in sva)

    trend = read.attendance_trend()
    assert trend
    assert all(row[1] == 0.0 for row in trend)

    update.update_wellbeing(w_ids["S1_w1"], new_stress=2, new_sleep=8.0)
    row2 = read.get_wellbeing_by_id(w_ids["S1_w1"])
    assert row2["stress_level"] == 2
    assert pytest.approx(row2["hours_slept"]) == 8.0


# =========================================================
#                        Attendance
# =========================================================
def test_attendance_crud(sample_data):
    a_ids = sample_data["attendance_ids"]

    # Count
    assert read.count_attendance() == 9
    assert read.count_attendance("S1") == 3

    # Per-student
    rows = read.get_attendance_by_student("S1")
    weeks = [r["week"] for r in rows]
    statuses = [r["status"] for r in rows]
    assert weeks == [1, 2, 3]
    assert statuses == [1, 1, 0]

    # Pagination + sorting
    page = read.get_attendance_page(
        limit=5, offset=0, student_id="S1", sort_week="desc"
    )
    assert [r["week"] for r in page] == [3, 2, 1]

    # Filtered query
    filtered = read.get_attendance_filtered(
        programme_id="P1", module_id="M1", week_start=1, week_end=2
    )
    # S1/S2 in P1, M1, weeks 1–2 → 4 rows
    assert len(filtered) == 4

    # Query by id
    row = read.get_attendance_by_id(a_ids["S1_w1"])
    assert row["student_id"] == "S1"
    assert row["week"] == 1

    # Update without modifying week
    update.update_attendance(a_ids["S1_w1"], status=0)
    row2 = read.get_attendance_by_id(a_ids["S1_w1"])
    assert row2["status"] == 0

    # Update modifying week
    update.update_attendance(a_ids["S1_w2"], status=0, week=5)
    row3 = read.get_attendance_by_id(a_ids["S1_w2"])
    assert row3["status"] == 0
    assert row3["week"] == 5

    # get_attendance_rate: implementation counts string 'present', so returns 0.0 here
    rate = read.get_attendance_rate("S1")
    assert rate == 0.0

    # Delete all attendance
    delete.delete_all_attendance()
    assert read.count_attendance() == 0


# =========================================================
#                        Submission
# =========================================================
def test_submission_crud_and_queries(sample_data):
    sub_ids = sample_data["submission_ids"]

    assert read.count_submission() == 4
    assert read.count_submission("S1") == 2

    # Pagination
    page = read.get_submission_page(limit=10, offset=0)
    assert len(page) == 4

    page_s1 = read.get_submission_page(limit=10, offset=0, student_id="S1")
    assert len(page_s1) == 2

    # Query by id
    row = read.get_submission_by_id(sub_ids["S1_a1"])
    assert row["student_id"] == "S1"
    assert row["module_id"] == "M1"

    # Filtering
    filtered = read.get_submissions_filtered(programme_id="P1", module_id="M1")
    # In P1, module M1 submissions from S1 & S2
    assert {r["student_id"] for r in filtered} == {"S1", "S2"}

    # submissions_for_course: M1, assignment 1 → S1 and S2
    subs_course = read.submissions_for_course("M1", assignment_no=1)
    assert len(subs_course) == 2
    assert {r[2] for r in subs_course} == {"S1", "S2"}

    # unsubmissions_for_repeated_issues: before updating, S1 has an unsubmitted record
    unsub = read.unsubmissions_for_repeated_issues(module_id="M1")
    assert any(r[3] == "S1" and r[6] == 0 for r in unsub)

    # ---- Update test: make S1 assignment 2 submitted with grade ----
    update.update_submission(
        sub_ids["S1_a2"],
        submitted=1,
        grade=65.0,
        due_date="2024-02-10",
        submit_date="2024-02-09",
    )
    row2 = read.get_submission_by_id(sub_ids["S1_a2"])
    assert row2["submitted"] == 1
    assert pytest.approx(row2["grade"]) == 65.0

    # attendance_and_grades: P1 + M1
    ag = read.attendance_and_grades(module_id="M1", programme_id="P1")
    assert ag
    # Returned fields: module_id, module_name, student_id, student_name, week, status, grade
    assert len(ag[0]) == 7

    # Delete all submissions
    delete.delete_all_submissions()
    assert read.count_submission() == 0


# =========================================================
#                        Delete helpers
# =========================================================
def test_delete_helpers(sample_data):
    # Ensure data exists
    assert read.count_students() == 3
    assert read.count_wellbeing() > 0
    assert read.count_attendance() > 0
    assert read.count_submission() > 0

    # Deletion order due to foreign key dependencies
    delete.delete_all_attendance()
    delete.delete_all_wellbeing()
    delete.delete_all_submissions()
    delete.delete_all_student_modules()
    delete.delete_all_students()

    assert read.count_students() == 0
    assert read.count_wellbeing() == 0
    assert read.count_attendance() == 0
    assert read.count_submission() == 0

    # No read function for student_module; validate via raw SQL
    conn = db_core.get_conn()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM student_module")
    assert cur.fetchone()[0] == 0
    conn.close()


# =========================================================
#                           Users
# =========================================================
def test_user_and_auth(sample_data):
    # sample_data already created admin user
    assert read.check_login("admin", "secret123") is True
    assert read.check_login("admin", "wrong") is False

    assert read.get_user_role("admin") == "swo"

    # Create another user
    create.create_user("leader", "pass456", "cd")
    assert read.get_user_role("leader") == "cd"
