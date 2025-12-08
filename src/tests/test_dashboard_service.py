# tests/test_dashboard_service.py

from student_wellbeing_monitor.services import dashboard_service


class FakeArgs:
    def __init__(self, data=None):
        self._data = data or {}

    def get(self, key, type=None, default=None):
        if key not in self._data or self._data[key] is None:
            return default
        value = self._data[key]
        if type is not None:
            try:
                return type(value)
            except (ValueError, TypeError):
                return default
        return value


def test_resolve_week_range_default(monkeypatch):
    monkeypatch.setattr(dashboard_service, "get_all_weeks", lambda: [1, 2, 3])

    args = FakeArgs()  # 没有 start_week / end_week
    result = dashboard_service.resolve_week_range(args)

    assert result["weeks"] == [1, 2, 3]
    assert result["start_week"] == 1
    assert result["end_week"] == 3


def test_resolve_week_range_with_args(monkeypatch):
    monkeypatch.setattr(dashboard_service, "get_all_weeks", lambda: [1, 2, 3])

    args = FakeArgs({"start_week": "2", "end_week": "3"})
    result = dashboard_service.resolve_week_range(args)

    assert result["start_week"] == 2
    assert result["end_week"] == 3


def test_resolve_week_range_no_weeks(monkeypatch):
    monkeypatch.setattr(dashboard_service, "get_all_weeks", lambda: [])

    args = FakeArgs()
    result = dashboard_service.resolve_week_range(args)

    assert result["weeks"] == [1]
    assert result["start_week"] == 1
    assert result["end_week"] == 1


def test_resolve_programme_and_module_for_wellbeing(monkeypatch):
    monkeypatch.setattr(
        dashboard_service,
        "get_programmes",
        lambda: [
            {
                "programme_id": "P1",
                "programme_code": "DS",
                "programme_name": "Data Science",
            }
        ],
    )

    args = FakeArgs()  # 没有 programme / module
    ctx = dashboard_service.resolve_programme_and_module(args, role="wellbeing")

    assert ctx["programmes"][0]["id"] == "P1"
    assert ctx["current_programme"] is None
    assert ctx["current_module"] is None


def test_resolve_programme_and_module_default_for_course_leader(monkeypatch):
    monkeypatch.setattr(
        dashboard_service,
        "get_programmes",
        lambda: [
            {
                "programme_id": "P1",
                "programme_code": "DS",
                "programme_name": "Data Science",
            },
            {
                "programme_id": "P2",
                "programme_code": "CS",
                "programme_name": "Computer Science",
            },
        ],
    )

    args = FakeArgs()  # 没有指定 programme_id
    ctx = dashboard_service.resolve_programme_and_module(args, role="course_leader")

    assert ctx["current_programme"] == "P1"  # 自动选第一个


def test_resolve_programme_and_module_with_args(monkeypatch):
    monkeypatch.setattr(
        dashboard_service,
        "get_programmes",
        lambda: [
            {
                "programme_id": "P1",
                "programme_code": "DS",
                "programme_name": "Data Science",
            },
        ],
    )

    args = FakeArgs({"programme_id": "P1", "module_id": "M1"})
    ctx = dashboard_service.resolve_programme_and_module(args, role="course_leader")

    assert ctx["current_programme"] == "P1"
    assert ctx["current_module"] == "M1"


def test_load_modules_by_programme(monkeypatch):
    monkeypatch.setattr(
        dashboard_service,
        "get_all_modules",
        lambda: [
            {
                "programme_id": "P1",
                "module_id": "M1",
                "module_code": "CS101",
                "module_name": "Intro CS",
            },
            {
                "programme_id": "P1",
                "module_id": "M2",
                "module_code": "CS102",
                "module_name": "Algo",
            },
            {
                "programme_id": "P2",
                "module_id": "M3",
                "module_code": "DS101",
                "module_name": "Intro DS",
            },
        ],
    )

    result = dashboard_service.load_modules_by_programme()
    assert set(result.keys()) == {"P1", "P2"}
    assert len(result["P1"]) == 2
    assert result["P1"][0]["id"] == "M1"


def test_get_target_modules_all():
    modules_by_programme = {
        "P1": [
            {"id": "M1", "code": "CS101"},
            {"id": "M2", "code": "CS102"},
        ]
    }
    target = dashboard_service.get_target_modules(
        modules_by_programme, "P1", module_id=None
    )
    assert len(target) == 2


def test_get_target_modules_single():
    modules_by_programme = {
        "P1": [
            {"id": "M1", "code": "CS101"},
            {"id": "M2", "code": "CS102"},
        ]
    }
    target = dashboard_service.get_target_modules(
        modules_by_programme, "P1", module_id="M2"
    )
    assert len(target) == 1
    assert target[0]["id"] == "M2"


def test_build_summary_for_wellbeing(monkeypatch):
    def fake_get_dashboard_summary(start, end, programme_id=None):
        return {
            "surveyResponses": {"studentCount": 10, "responseRate": 0.5},
            "avgHoursSlept": 6.5,
            "avgStressLevel": 3.2,
        }

    monkeypatch.setattr(
        dashboard_service.wellbeing_service,
        "get_dashboard_summary",
        fake_get_dashboard_summary,
    )

    summary = dashboard_service.build_summary(
        role="wellbeing",
        start_week=1,
        end_week=5,
        current_programme="P1",
        current_module=None,
    )

    assert summary == {
        "response_count": 10,
        "response_rate": 0.5,
        "avg_sleep": 6.5,
        "avg_stress": 3.2,
    }


def test_build_summary_for_course_leader(monkeypatch):
    called = {}

    def fake_get_course_leader_summary(programme_id, module_id, week_start, week_end):
        called["programme_id"] = programme_id
        called["module_id"] = module_id
        called["week_start"] = week_start
        called["week_end"] = week_end
        return {"dummy": True}

    monkeypatch.setattr(
        dashboard_service.course_service,
        "get_course_leader_summary",
        fake_get_course_leader_summary,
    )

    summary = dashboard_service.build_summary(
        role="course_leader",
        start_week=2,
        end_week=4,
        current_programme="P1",
        current_module="M1",
    )

    assert summary == {"dummy": True}
    assert called == {
        "programme_id": "P1",
        "module_id": "M1",
        "week_start": 2,
        "week_end": 4,
    }


def test_build_charts_for_wellbeing(monkeypatch):
    monkeypatch.setattr(
        dashboard_service.wellbeing_service,
        "get_stress_sleep_trend",
        lambda start, end, programme_id=None: {
            "weeks": [1, 2, 3],
            "stress": [3.0, 3.5, 4.0],
            "sleep": [7.0, 6.5, 6.0],
        },
    )

    monkeypatch.setattr(
        dashboard_service.course_service,
        "get_programme_wellbeing_engagement",
        lambda programme_id=None, week_start=None, week_end=None: {
            "programmes": [
                {
                    "programmeId": "P1",
                    "programmeName": "Data Science",
                    "avgStress": 3.5,
                    "attendanceRate": 0.8,
                    "submissionRate": 0.7,
                    "avgGrade": 68.0,
                }
            ]
        },
    )

    charts = dashboard_service.build_charts_for_wellbeing(
        start_week=1,
        end_week=3,
        current_programme="P1",
    )

    assert charts["weeks_for_chart"] == [1, 2, 3]
    assert charts["avg_stress"] == [3.0, 3.5, 4.0]
    assert charts["avg_sleep"] == [7.0, 6.5, 6.0]

    stats = charts["programme_stats"]
    assert stats["labels"] == ["Data Science"]
    assert stats["avgStress"] == [3.5]
    assert stats["attendanceRate"] == [0.8]
    assert stats["submissionRate"] == [0.7]
    assert stats["avgGrade"] == [68.0]


def test_build_charts_for_course_leader_with_programme_and_module(monkeypatch):
    monkeypatch.setattr(
        dashboard_service.attendance_service,
        "get_attendance_trends",
        lambda course_id, programme_id, week_start, week_end: {
            "points": [
                {"week": 1, "attendanceRate": 0.9, "avgGrade": 70},
                {"week": 2, "attendanceRate": 0.8, "avgGrade": 65},
            ]
        },
    )

    monkeypatch.setattr(
        dashboard_service.course_service,
        "get_attendance_vs_grades",
        lambda course_id, programme_id, week_start, week_end: {
            "points": [{"studentId": "S1", "attendanceRate": 0.9, "grade": 70}]
        },
    )

    def fake_get_submission_summary(programme_id, course_id, assignment_no):
        return {"submit": 10, "unsubmit": 5}

    monkeypatch.setattr(
        dashboard_service.course_service,
        "get_submission_summary",
        fake_get_submission_summary,
    )

    modules_by_programme = {
        "P1": [
            {"id": "M1", "code": "CS101"},
            {"id": "M2", "code": "CS102"},
        ]
    }

    charts = dashboard_service.build_charts_for_course_leader(
        start_week=1,
        end_week=2,
        current_programme="P1",
        current_module=None,  # → 应该对 P1 的两个 module 都做 bar
        modules_by_programme=modules_by_programme,
    )

    assert charts["weeks_for_chart"] == [1, 2]
    assert charts["attendance_trend"] == [0.9, 0.8]
    assert charts["grade_trend"] == [70, 65]

    # bar
    assert charts["submission_labels"] == ["CS101", "CS102"]
    assert charts["submission_submitted"] == [10, 10]
    assert charts["submission_unsubmitted"] == [5, 5]

    # scatter
    assert charts["scatter_points"] == [
        {"studentId": "S1", "attendanceRate": 0.9, "grade": 70}
    ]


def test_build_risks_for_wellbeing_without_ai(monkeypatch):
    monkeypatch.setattr(
        dashboard_service.wellbeing_service,
        "get_risk_students",
        lambda start, end, programme_id=None: {
            "items": [
                {
                    "studentId": "5000001",
                    "name": "Alice",
                    "email": "alice@example.com",
                    "reason": "high_stress",
                    "details": "Stress >= 4 for 3 weeks",
                }
            ]
        },
    )

    risks = dashboard_service.build_risks_for_wellbeing(
        start_week=1, end_week=5, current_programme="P1", run_ai=False
    )

    assert len(risks["students_to_contact"]) == 1
    assert risks["ai_result"] is None


def test_build_risks_for_wellbeing_with_ai(monkeypatch):
    monkeypatch.setattr(
        dashboard_service.wellbeing_service,
        "get_risk_students",
        lambda start, end, programme_id=None: {"items": []},
    )

    monkeypatch.setattr(
        dashboard_service.course_service,
        "analyze_high_stress_sleep_with_ai",
        lambda programme_id, week_start, week_end: {"summary": "dummy ai analysis"},
    )

    risks = dashboard_service.build_risks_for_wellbeing(
        start_week=1, end_week=5, current_programme="P1", run_ai=True
    )

    assert "ai_result" in risks
    assert risks["ai_result"] is None


def test_build_risks_for_course_leader(monkeypatch):
    modules_by_programme = {
        "P1": [
            {"id": "M1", "code": "CS101"},
        ]
    }

    monkeypatch.setattr(
        dashboard_service.attendance_service,
        "get_low_attendance_students",
        lambda course_id, programme_id, week_start, week_end, threshold_rate, min_absences: {
            "students": [
                {
                    "studentId": "S1",
                    "name": "Alice",
                    "email": "alice@example.com",
                    "attendanceRate": 0.6,
                    "absentSessions": 4,
                }
            ]
        },
    )

    monkeypatch.setattr(
        dashboard_service.course_service,
        "get_repeated_missing_students",
        lambda course_id, programme_id, start_week, end_week, min_offending_modules: {
            "students": [
                {
                    "studentId": "S2",
                    "name": "Bob",
                    "email": "bob@example.com",
                    "offendingModuleCount": 2,
                    "details": [],
                }
            ]
        },
    )

    risks = dashboard_service.build_risks_for_course_leader(
        start_week=1,
        end_week=5,
        current_programme="P1",
        current_module=None,
        modules_by_programme=modules_by_programme,
    )

    assert len(risks["attendance_risk_students"]) == 1
    assert risks["attendance_risk_students"][0]["module_code"] == "CS101"

    assert len(risks["submission_risk_students"]) == 1
    assert risks["submission_risk_students"][0]["student_id"] == "S2"
