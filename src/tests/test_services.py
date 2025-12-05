# src/student_wellbeing_monitor/tests/test_services.py
import io
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

import pytest

# ------------------------------------------------------------------------
# 让 pytest 能够 import student_wellbeing_monitor.*
# 参考你项目里的 services/test.py 写法
# ------------------------------------------------------------------------
SRC_DIR = Path(__file__).resolve().parents[2]  # 指向 src 目录
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from student_wellbeing_monitor.services import (
    archive_service,
    attendance_service,
    course_service,
    upload_service,
    wellbeing_service,
)


# =============================================================================
# 工具：简单的 FileStorage 替身
# =============================================================================
class DummyFileStorage:
    """
    模拟 werkzeug.datastructures.FileStorage，只需要提供 .stream 即可。
    """

    def __init__(self, data: bytes):
        self.stream = io.BytesIO(data)


# =============================================================================
# upload_service 测试
# =============================================================================
def test_read_csv_basic():
    csv_bytes = b"student_id,week,stress_level,hours_slept\n1,2,3,4\n"
    fs = DummyFileStorage(csv_bytes)

    rows = upload_service.read_csv(fs)

    assert isinstance(rows, list)
    assert len(rows) == 1
    row = rows[0]
    assert row["student_id"] == "1"
    assert row["week"] == "2"
    assert row["stress_level"] == "3"
    assert row["hours_slept"] == "4"


def test_import_wellbeing_csv(monkeypatch):
    csv_bytes = (
        b"student_id,week,stress_level,hours_slept\n"
        b"1,1,3,7\n"
        b"2,1,4,6\n"
    )
    fs = DummyFileStorage(csv_bytes)

    calls: List[Dict[str, Any]] = []

    def fake_add_wellbeing(student_id, week, stress_level, hours_slept):
        calls.append(
            {
                "student_id": student_id,
                "week": week,
                "stress_level": stress_level,
                "hours_slept": hours_slept,
            }
        )

    monkeypatch.setattr(
        upload_service.create,
        "add_wellbeing",
        fake_add_wellbeing,
        raising=False,
    )


    upload_service.import_wellbeing_csv(fs)

    assert len(calls) == 2
    assert calls[0]["student_id"] == 1
    assert calls[0]["week"] == 1
    assert calls[0]["stress_level"] == 3
    assert calls[0]["hours_slept"] == 7


def test_import_attendance_csv(monkeypatch):
    csv_bytes = (
        b"student_id,module_code,week,attendance_status\n"
        b"1,CS101,1,1\n"
        b"2,CS101,1,0\n"
    )
    fs = DummyFileStorage(csv_bytes)

    calls: List[Dict[str, Any]] = []

    def fake_insert_attendance(student_id, module_code, week, status):
        calls.append(
            {
                "student_id": student_id,
                "module_code": module_code,
                "week": week,
                "status": status,
            }
        )

    monkeypatch.setattr(
        upload_service.create, "insert_attendance", fake_insert_attendance
    )

    upload_service.import_attendance_csv(fs)

    assert len(calls) == 2
    assert calls[0]["module_code"] == "CS101"
    assert calls[0]["status"] == 1
    assert calls[1]["status"] == 0


def test_import_submissions_csv(monkeypatch):
    csv_bytes = (
        b"student_id,module_code,submitted,grade,due_date,submit_date\n"
        b"1,CS101,1,70,2024-01-01,2023-12-31\n"
        b"2,CS101,0,,2024-01-01,\n"
    )
    fs = DummyFileStorage(csv_bytes)

    calls: List[Dict[str, Any]] = []

    def fake_insert_submission(
        student_id, module_code, submitted, grade, due_date, submit_date
    ):
        calls.append(
            {
                "student_id": student_id,
                "module_code": module_code,
                "submitted": submitted,
                "grade": grade,
                "due_date": due_date,
                "submit_date": submit_date,
            }
        )

    monkeypatch.setattr(
        upload_service.create, "insert_submission", fake_insert_submission
    )

    upload_service.import_submissions_csv(fs)

    assert len(calls) == 2
    assert calls[0]["submitted"] == 1
    assert calls[0]["grade"] == "70"
    # 空字符串会转成 None
    assert calls[1]["submitted"] == 0
    assert calls[1]["grade"] is None


def test_import_csv_by_type_and_invalid(monkeypatch):
    # 只需要验证它能路由到对应函数 / 抛异常即可
    called = {"wellbeing": False, "attendance": False, "submissions": False}

    def fake_wellbeing(fs):
        called["wellbeing"] = True

    def fake_attendance(fs):
        called["attendance"] = True

    def fake_submissions(fs):
        called["submissions"] = True

    monkeypatch.setattr(upload_service, "import_wellbeing_csv", fake_wellbeing)
    monkeypatch.setattr(upload_service, "import_attendance_csv", fake_attendance)
    monkeypatch.setattr(upload_service, "import_submissions_csv", fake_submissions)

    dummy_fs = DummyFileStorage(b"")  # 内容无所谓

    upload_service.import_csv_by_type("wellbeing", dummy_fs)
    upload_service.import_csv_by_type("attendance", dummy_fs)
    upload_service.import_csv_by_type("submissions", dummy_fs)

    assert called["wellbeing"]
    assert called["attendance"]
    assert called["submissions"]

    with pytest.raises(ValueError):
        upload_service.import_csv_by_type("unknown_type", dummy_fs)


# =============================================================================
# wellbeing_service 测试
# =============================================================================
@pytest.fixture
def wb_students():
    # student_id, name, email, programme_id
    return [
        (1, "Alice", "alice@example.com", "P1"),
        (2, "Bob", "bob@example.com", "P1"),
        (3, "Cara", "cara@example.com", "P2"),
        (4, "Dan", "dan@example.com", "P2"),
    ]


def test_wellbeing_get_student_count(monkeypatch, wb_students):
    # patch get_all_students / get_students_by_programme
    def fake_get_all_students():
        return wb_students

    def fake_get_students_by_programme(pid):
        return [r for r in wb_students if r[3] == pid]

    monkeypatch.setattr(wellbeing_service, "get_all_students", fake_get_all_students)
    monkeypatch.setattr(
        wellbeing_service, "get_students_by_programme", fake_get_students_by_programme
    )

    service = wellbeing_service.WellbeingService()
    assert service._get_student_count(None) == len(wb_students)
    assert service._get_student_count("P1") == 2
    assert service._get_student_count("P2") == 2


def test_wellbeing_dashboard_summary(monkeypatch, wb_students):
    def fake_get_all_students():
        return wb_students

    def fake_get_students_by_programme(pid):
        return [r for r in wb_students if r[3] == pid]

    rows = [
        # student_id, week, stress, sleep, programme_id
        (1, 1, 3, 7, "P1"),
        (2, 1, 5, 5, "P1"),
        (1, 2, 4, 8, "P1"),
        (3, 1, None, 6, "P2"),
    ]

    def fake_get_wellbeing_records(start_week, end_week, programme_id=None):
        return rows

    monkeypatch.setattr(wellbeing_service, "get_all_students", fake_get_all_students)
    monkeypatch.setattr(
        wellbeing_service, "get_students_by_programme", fake_get_students_by_programme
    )
    monkeypatch.setattr(
        wellbeing_service, "get_wellbeing_records", fake_get_wellbeing_records
    )

    service = wellbeing_service.WellbeingService()
    result = service.get_dashboard_summary(1, 4)

    assert pytest.approx(result["avgStressLevel"]) == 4.0
    assert pytest.approx(result["avgHoursSlept"]) == 6.5
    assert result["surveyResponses"]["studentCount"] == 3
    # 3 / 4 = 0.75 → round(0.75, 2) * 100 = 75.0
    assert pytest.approx(result["surveyResponses"]["responseRate"]) == 75.0

    with pytest.raises(ValueError):
        service.get_dashboard_summary(5, 2)


def test_wellbeing_stress_sleep_trend(monkeypatch):
    rows = [
        (1, 1, 3, 7, "P1"),
        (2, 1, 5, 5, "P1"),
        (1, 2, 4, 8, "P1"),
        (3, 2, None, 6, "P2"),
    ]

    def fake_get_wellbeing_records(start_week, end_week, programme_id=None):
        return rows

    monkeypatch.setattr(
        wellbeing_service, "get_wellbeing_records", fake_get_wellbeing_records
    )

    service = wellbeing_service.WellbeingService()
    res = service.get_stress_sleep_trend(1, 4)

    assert res["weeks"] == [1, 2]
    # week 1 avg stress: (3+5)/2 = 4
    assert pytest.approx(res["stress"][0]) == 4.0
    # week 2 avg stress: 4
    assert pytest.approx(res["stress"][1]) == 4.0
    # week 1 sleep: (7+5)/2=6; week 2: (8+6)/2=7
    assert pytest.approx(res["sleep"][0]) == 6.0
    assert pytest.approx(res["sleep"][1]) == 7.0

    with pytest.raises(ValueError):
        service.get_stress_sleep_trend(5, 1)


def _setup_wellbeing_risk_data(monkeypatch, wb_students):
    # 1 高风险：三周连续 stress>=4.5 & sleep<6
    # 2 潜在风险：某一周满足条件
    # 3 正常
    rows = [
        # sid, week, stress, sleep, programme
        (1, 1, 5, 5, "P1"),
        (1, 2, 5, 5, "P1"),
        (1, 3, 5, 5, "P1"),
        (2, 1, 3, 7, "P1"),
        (2, 2, 5, 5, "P1"),  # 只这一周触发
        (3, 1, 3, 7, "P2"),
        (3, 2, 3, 7, "P2"),
    ]

    def fake_get_all_students():
        return wb_students

    def fake_get_students_by_programme(pid):
        return [r for r in wb_students if r[3] == pid]

    def fake_get_wellbeing_records(start_week, end_week, programme_id=None):
        return rows

    monkeypatch.setattr(wellbeing_service, "get_all_students", fake_get_all_students)
    monkeypatch.setattr(
        wellbeing_service, "get_students_by_programme", fake_get_students_by_programme
    )
    monkeypatch.setattr(
        wellbeing_service, "get_wellbeing_records", fake_get_wellbeing_records
    )


def test_wellbeing_get_risk_students_all(monkeypatch, wb_students):
    _setup_wellbeing_risk_data(monkeypatch, wb_students)
    service = wellbeing_service.WellbeingService()

    res = service.get_risk_students(1, 4)
    items = {item["studentId"]: item for item in res["items"]}

    assert "1" in items and "2" in items
    assert items["1"]["riskType"] == "high_risk"
    assert items["2"]["riskType"] == "potential_risk"
    # 正常学生不会出现在列表里
    assert "3" not in items


def test_wellbeing_get_risk_students_single_normal(monkeypatch, wb_students):
    _setup_wellbeing_risk_data(monkeypatch, wb_students)
    service = wellbeing_service.WellbeingService()

    res = service.get_risk_students(1, 4, student_id="3")
    assert res["items"]
    assert res["items"][0]["studentId"] == "3"
    assert res["items"][0]["riskType"] == "normal"


def test_wellbeing_get_risk_students_no_data(monkeypatch, wb_students):
    _setup_wellbeing_risk_data(monkeypatch, wb_students)
    service = wellbeing_service.WellbeingService()

    # 学生 4 存在但 wellbeing 没有记录
    res = service.get_risk_students(1, 4, student_id="4")
    assert res["items"] == []
    assert res["status"] == "no_data"


def test_wellbeing_get_risk_students_not_found(monkeypatch, wb_students):
    _setup_wellbeing_risk_data(monkeypatch, wb_students)
    service = wellbeing_service.WellbeingService()

    res = service.get_risk_students(1, 4, student_id="999")
    assert res["items"] == []
    assert res["status"] == "not_found"


# =============================================================================
# attendance_service 测试
# =============================================================================
def test_attendance_get_trends(monkeypatch):
    # rows: (module_id, module_name, student_id, student_name, week, status)
    rows = [
        ("CS101", "Intro CS", 1, "Alice", 1, 1),
        ("CS101", "Intro CS", 2, "Bob", 1, 0),
        ("CS101", "Intro CS", 3, "Cara", 2, 1),
    ]

    def fake_attendance_for_course(
        programme_id=None, module_id=None, week_start=None, week_end=None
    ):
        return rows

    monkeypatch.setattr(
        attendance_service, "attendance_for_course", fake_attendance_for_course
    )

    service = attendance_service.AttendanceService()
    res = service.get_attendance_trends("CS101", week_start=1, week_end=3)

    assert res["courseId"] == "CS101"
    assert res["courseName"] == "Intro CS"
    points = {p["week"]: p for p in res["points"]}
    # week 1: 1 present / 2 total => 0.5
    assert pytest.approx(points[1]["attendanceRate"]) == 0.5
    # week 2: 1 / 1
    assert pytest.approx(points[2]["attendanceRate"]) == 1.0


def test_attendance_get_trends_empty(monkeypatch):
    def fake_attendance_for_course(**kwargs):
        return []

    monkeypatch.setattr(
        attendance_service, "attendance_for_course", fake_attendance_for_course
    )

    service = attendance_service.AttendanceService()
    res = service.get_attendance_trends("CS999")
    assert res["courseId"] == "CS999"
    assert res["courseName"] is None
    assert res["points"] == []


def test_attendance_get_low_attendance_students(monkeypatch):
    # rows: (module_id, module_name, student_id, student_name, email, week, status)
    rows = [
        ("CS101", "Intro CS", 1, "Alice", "alice@example.com", 1, 1),
        ("CS101", "Intro CS", 1, "Alice", "alice@example.com", 2, 0),
        ("CS101", "Intro CS", 2, "Bob", "bob@example.com", 1, 0),
        ("CS101", "Intro CS", 2, "Bob", "bob@example.com", 2, 0),
    ]

    def fake_attendance_detail_for_students(
        module_id=None, programme_id=None, week_start=None, week_end=None
    ):
        return rows

    monkeypatch.setattr(
        attendance_service,
        "attendance_detail_for_students",
        fake_attendance_detail_for_students,
    )

    service = attendance_service.AttendanceService()
    res = service.get_low_attendance_students(
        "CS101", threshold_rate=0.8, min_absences=2
    )

    assert res["courseId"] == "CS101"
    students = {s["studentId"]: s for s in res["students"]}
    # Alice：1 present / 2 total => 0.5，absent=1，不满足 min_absences=2，因此不会被选中
    # Bob：0 present / 2 total => 0.0，absent=2，应该被选中
    students = {str(s["studentId"]): s for s in res["students"]}
    assert "2" in students
    assert students["2"]["absentSessions"] == 2
    assert pytest.approx(students["2"]["attendanceRate"]) == 0.0


# =============================================================================
# course_service 测试
# =============================================================================
def test_course_leader_summary(monkeypatch):
    # 新版本 get_course_leader_summary 使用 status 为 "present"/"absent"
    def fake_get_attendance_filtered(programme_id, module_code, week_start, week_end):
        return [
            {"student_id": 1, "module_code": module_code, "week": 1, "status": "present"},
            {"student_id": 2, "module_code": module_code, "week": 1, "status": "absent"},
        ]

    def fake_get_submissions_filtered(programme_id, module_code):
        return [
            {"student_id": 1, "module_code": module_code, "submitted": 1, "grade": 60},
            {"student_id": 2, "module_code": module_code, "submitted": 0, "grade": None},
        ]

    monkeypatch.setattr(
        course_service, "get_attendance_filtered", fake_get_attendance_filtered
    )
    monkeypatch.setattr(
        course_service, "get_submissions_filtered", fake_get_submissions_filtered
    )

    service = course_service.CourseService()
    res = service.get_course_leader_summary(
        programme_id="P1", module_code="CS101", week_start=1, week_end=10
    )

    assert pytest.approx(res["avg_attendance_rate"]) == 0.5
    assert pytest.approx(res["avg_submission_rate"]) == 0.5
    assert pytest.approx(res["avg_grade"]) == 60.0


def test_course_submission_summary(monkeypatch):
    # rows: (module_id, module_name, student_id, submitted)
    rows = [
        ("CS101", "Intro CS", 1, True),
        ("CS101", "Intro CS", 2, False),
        ("CS101", "Intro CS", 3, True),
    ]

    def fake_submissions_for_course(module_id, assignment_no, programme_id):
        return rows

    monkeypatch.setattr(
        course_service, "submissions_for_course", fake_submissions_for_course
    )

    service = course_service.CourseService()
    res = service.get_submission_summary(
        programme_id="P1", course_id="CS101", assignment_no=1
    )

    assert res["courseId"] == "CS101"
    assert res["courseName"] == "Intro CS"
    assert res["totalStudents"] == 3
    assert res["submit"] == 2
    assert res["unsubmit"] == 1


def test_course_submission_summary_empty(monkeypatch):
    def fake_submissions_for_course(module_id, assignment_no, programme_id):
        return []

    monkeypatch.setattr(
        course_service, "submissions_for_course", fake_submissions_for_course
    )

    service = course_service.CourseService()
    res = service.get_submission_summary(
        programme_id="P1", course_id="CS999", assignment_no=1
    )

    assert res["courseId"] == "CS999"
    assert res["courseName"] is None
    assert res["totalStudents"] == 0


def test_course_repeated_missing_students(monkeypatch):
    # rows: (module_id, module_name, assignment_no, student_id, student_name, email, submitted)
    rows = [
        ("CS101", "Intro CS", 1, "1", "Alice", "alice@example.com", 0),
        ("CS102", "Algo", 1, "1", "Alice", "alice@example.com", 0),
        ("CS103", "DB", 1, "2", "Bob", "bob@example.com", 0),
    ]

    def fake_unsubmissions_for_repeated_issues(
        module_id=None, programme_id=None, week_start=None, week_end=None
    ):
        return rows

    monkeypatch.setattr(
        course_service,
        "unsubmissions_for_repeated_issues",
        fake_unsubmissions_for_repeated_issues,
    )

    service = course_service.CourseService()
    res = service.get_repeated_missing_students(min_offending_modules=2)

    students = {s["studentId"]: s for s in res["students"]}
    assert "1" in students
    assert students["1"]["offendingModuleCount"] == 2
    # Bob 只在一门课未交，不应出现
    assert "2" not in students


def test_course_attendance_vs_grades(monkeypatch):
    # rows: (module_id, module_name, student_id, student_name, week, status, grade)
    rows = [
        ("CS101", "Intro CS", "1", "Alice", 1, 1, 70),
        ("CS101", "Intro CS", "1", "Alice", 2, 1, 80),
        ("CS101", "Intro CS", "2", "Bob", 1, 0, 60),
    ]

    def fake_attendance_and_grades(
        module_id=None, programme_id=None, week_start=None, week_end=None
    ):
        return rows

    monkeypatch.setattr(
        course_service, "attendance_and_grades", fake_attendance_and_grades
    )

    service = course_service.CourseService()
    res = service.get_attendance_vs_grades(
        course_id="CS101", week_start=1, week_end=3
    )

    assert res["courseId"] == "CS101"
    assert res["courseName"] == "Intro CS"
    points = {p["studentId"]: p for p in res["points"]}

    # Alice: present 2 / total 2 = 1.0; grade avg (70+80)/2=75
    assert pytest.approx(points["1"]["attendanceRate"]) == 1.0
    assert pytest.approx(points["1"]["avgGrade"]) == 75.0
    # Bob: present 0 / total 1
    assert pytest.approx(points["2"]["attendanceRate"]) == 0.0


def test_course_programme_wellbeing_engagement(monkeypatch):
    # rows: (module_id, module_name,
    #        student_id,
    #        programme_id, programme_name,
    #        week,
    #        stress_level,
    #        hours_slept,
    #        attendance_status,
    #        submission_status,
    #        grade)
    rows = [
        ("CS101", "Intro CS", "1", "P1", "Prog 1", 1, 4, 7, 1, "submit", 70),
        ("CS101", "Intro CS", "2", "P1", "Prog 1", 1, 2, 8, 0, "unsubmit", 60),
        ("CS102", "Algo", "3", "P2", "Prog 2", 1, 3, 7, 1, "submit", 80),
    ]

    def fake_programme_wellbeing_engagement(
        programme_id=None, week_start=None, week_end=None
    ):
        return rows

    monkeypatch.setattr(
        course_service,
        "programme_wellbeing_engagement",
        fake_programme_wellbeing_engagement,
    )

    service = course_service.CourseService()
    res = service.get_programme_wellbeing_engagement()

    assert res["programmeId"] is None
    programmes = {p["programmeId"]: p for p in res["programmes"]}

    p1 = programmes["P1"]
    assert p1["studentCount"] == 2
    # P1 stress avg: (4+2)/2 =3
    assert pytest.approx(p1["avgStress"]) == 3.0
    # attendance: present 1 / total 2 = 0.5
    assert pytest.approx(p1["attendanceRate"]) == 0.5
    # submission: submit 1 / total 2 = 0.5
    assert pytest.approx(p1["submissionRate"]) == 0.5


def test_course_high_stress_sleep_engagement_analysis(monkeypatch):
    # 一组高压少睡，一组正常
    rows = [
        # high group student 1
        ("CS101", "Intro CS", "1", "P1", "Prog 1", 1, 5, 5, 1, "submit", 70),
        ("CS101", "Intro CS", "1", "P1", "Prog 1", 2, 5, 5, 1, "submit", 75),
        # other group student 2
        ("CS101", "Intro CS", "2", "P1", "Prog 1", 1, 2, 7, 1, "submit", 60),
        ("CS101", "Intro CS", "2", "P1", "Prog 1", 2, 3, 7, 0, "unsubmit", 65),
    ]

    def fake_programme_wellbeing_engagement(
        programme_id=None, week_start=None, week_end=None
    ):
        return rows

    monkeypatch.setattr(
        course_service,
        "programme_wellbeing_engagement",
        fake_programme_wellbeing_engagement,
    )

    service = course_service.CourseService()
    res = service.get_high_stress_sleep_engagement_analysis(
        programme_id="P1", week_start=1, week_end=2, stress_threshold=4.0, sleep_threshold=6.0, min_weeks=1
    )

    groups = res["groups"]
    high = groups["highStressLowSleep"]
    others = groups["others"]

    assert high["studentCount"] == 1
    assert others["studentCount"] == 1
    # 高压组平均成绩应该高于 70
    assert high["avgGrade"] >= 70
    # 其他组平均成绩在 60~65 之间
    assert 60 <= others["avgGrade"] <= 65


def test_course_analyze_high_stress_sleep_with_ai(monkeypatch):
    # 不测试复杂逻辑，只测试它能调用外部 AI 并返回 text
    service = course_service.CouseService if False else course_service.CourseService()

    # 1) mock 基础统计
    base_result = {
        "params": {},
        "groups": {},
        "students": {"highStressLowSleep": [], "others": []},
    }

    def fake_base_analysis(
        self, programme_id, week_start, week_end, stress_threshold, sleep_threshold, min_weeks
    ):
        return base_result

    monkeypatch.setattr(
        course_service.CourseService,
        "get_high_stress_sleep_engagement_analysis",
        fake_base_analysis,
        raising=False,
    )

    # 2) mock google.genai.Client
    class DummyModels:
        def generate_content(self, model, contents):
            class R:
                text = "AI analysis text"

            return R()

    class DummyClient:
        def __init__(self, api_key):
            self.api_key = api_key
            self.models = DummyModels()

    import types

    monkeypatch.setattr(
        course_service, "genai", types.SimpleNamespace(Client=DummyClient), raising=False
    )

    # 3) 设置环境变量
    monkeypatch.setenv("GEMINI_API_KEY", "dummy-key")

    res = service.analyze_high_stress_sleep_with_ai(
        programme_id="P1", week_start=1, week_end=2
    )

    assert res["baseStats"] == base_result
    assert res["aiAnalysis"]["status"] == "ok"
    assert "AI analysis text" in res["aiAnalysis"]["text"]


# =============================================================================
# archive_service 测试
# =============================================================================
def test_archive_export_wellbeing_summary(tmp_path, monkeypatch):
    rows = [
        (1, 1, 3, 7, "P1"),
        (2, 1, 5, 5, "P1"),
        (3, 2, None, 6, "P1"),
    ]

    def fake_get_wellbeing_records(start_week, end_week, programme_id=None, student_id=None):
        return rows

    monkeypatch.setattr(
        archive_service, "get_wellbeing_records", fake_get_wellbeing_records
    )

    out_dir = tmp_path
    archive_service.export_wellbeing_summary(str(out_dir))

    csv_path = out_dir / "wellbeing_summary.csv"
    assert csv_path.exists()

    content = csv_path.read_text(encoding="utf-8").splitlines()
    # header + 2 rows
    assert len(content) == 3
    header = content[0].split(",")
    assert header == [
        "programme_id",
        "week",
        "avg_stress",
        "avg_hours_slept",
        "record_count",
    ]


def test_archive_export_attendance_summary(tmp_path, monkeypatch):
    def fake_count_attendance():
        return 4

    rows = [
        {"module_id": "CS101", "week": 1, "status": 1},
        {"module_id": "CS101", "week": 1, "status": 0},
        {"module_id": "CS101", "week": 2, "status": 1},
        {"module_id": "CS101", "week": 2, "status": 1},
    ]

    def fake_get_attendance_page(limit, offset):
        assert limit == 4
        return rows

    monkeypatch.setattr(
        archive_service, "count_attendance", fake_count_attendance
    )
    monkeypatch.setattr(
        archive_service, "get_attendance_page", fake_get_attendance_page
    )

    out_dir = tmp_path
    archive_service.export_attendance_summary(str(out_dir))

    csv_path = out_dir / "attendance_summary.csv"
    assert csv_path.exists()
    lines = csv_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 3  # header + 2 weeks


def test_archive_export_submission_summary(tmp_path, monkeypatch):
    def fake_count_submission():
        return 3

    rows = [
        {
            "module_id": "CS101",
            "due_date": "2024-01-01",
            "submitted": 1,
            "grade": 70,
        },
        {
            "module_id": "CS101",
            "due_date": "2024-01-01",
            "submitted": 1,
            "grade": 80,
        },
        {
            "module_id": "CS101",
            "due_date": "2024-01-01",
            "submitted": 0,
            "grade": None,
        },
    ]

    def fake_get_submission_page(limit, offset):
        assert limit == 3
        return rows

    monkeypatch.setattr(
        archive_service, "count_submission", fake_count_submission
    )
    monkeypatch.setattr(
        archive_service, "get_submission_page", fake_get_submission_page
    )

    out_dir = tmp_path
    archive_service.export_submission_summary(str(out_dir))

    csv_path = out_dir / "submission_summary.csv"
    assert csv_path.exists()
    lines = csv_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2  # header + 1 aggregated row


def test_archive_delete_all_data_order(monkeypatch):
    called = []

    def make_recorder(name):
        def inner():
            called.append(name)

        return inner

    monkeypatch.setattr(
        archive_service, "delete_all_wellbeing", make_recorder("wellbeing")
    )
    monkeypatch.setattr(
        archive_service, "delete_all_attendance", make_recorder("attendance")
    )
    monkeypatch.setattr(
        archive_service, "delete_all_submissions", make_recorder("submissions")
    )
    monkeypatch.setattr(
        archive_service,
        "delete_all_student_modules",
        make_recorder("student_modules"),
    )
    monkeypatch.setattr(
        archive_service, "delete_all_students", make_recorder("students")
    )

    archive_service.delete_all_data()

    assert called == [
        "wellbeing",
        "attendance",
        "submissions",
        "student_modules",
        "students",
    ]


def test_archive_run_archive_dry_run(monkeypatch, tmp_path):
    # 只验证在 delete_confirm=False 时不会调用 delete_all_data
    called_exports = []
    called_delete = {"flag": False}

    def fake_export_w(*args, **kwargs):
        called_exports.append("w")

    def fake_export_a(*args, **kwargs):
        called_exports.append("a")

    def fake_export_s(*args, **kwargs):
        called_exports.append("s")

    def fake_delete_all_data():
        called_delete["flag"] = True

    monkeypatch.setattr(
        archive_service, "export_wellbeing_summary", fake_export_w
    )
    monkeypatch.setattr(
        archive_service, "export_attendance_summary", fake_export_a
    )
    monkeypatch.setattr(
        archive_service, "export_submission_summary", fake_export_s
    )
    monkeypatch.setattr(
        archive_service, "delete_all_data", fake_delete_all_data
    )

    archive_service.run_archive(str(tmp_path), delete_confirm=False)

    assert called_exports == ["w", "a", "s"]
    assert not called_delete["flag"]


def test_archive_run_archive_with_delete(monkeypatch, tmp_path):
    called_delete = {"flag": False}

    def fake_export(*args, **kwargs):
        pass

    def fake_delete_all_data():
        called_delete["flag"] = True

    monkeypatch.setattr(
        archive_service, "export_wellbeing_summary", fake_export
    )
    monkeypatch.setattr(
        archive_service, "export_attendance_summary", fake_export
    )
    monkeypatch.setattr(
        archive_service, "export_submission_summary", fake_export
    )
    monkeypatch.setattr(
        archive_service, "delete_all_data", fake_delete_all_data
    )

    # 模拟输入 "DELETE"
    monkeypatch.setattr("builtins.input", lambda prompt="": "DELETE")

    archive_service.run_archive(str(tmp_path), delete_confirm=True)
    assert called_delete["flag"]
