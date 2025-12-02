# tests/test_services.py
import sys
from pathlib import Path
import io
import pytest

# --- 处理跨包导入：把 src 加到 sys.path ---
SRC_DIR = Path(__file__).resolve().parents[1]
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

# 现在可以正常导入包
import student_wellbeing_monitor.services.wellbeing_service as wb_mod
import student_wellbeing_monitor.services.attendance_service as att_mod
import student_wellbeing_monitor.services.upload_service as up_mod


# =========================================================
# 工具类：模拟 werkzeug FileStorage （只用到 .stream）
# =========================================================
class DummyFileStorage:
    def __init__(self, content: str):
        # upload_service 中使用 TextIOWrapper(file_storage.stream)
        self.stream = io.BytesIO(content.encode("utf-8"))


# =========================================================
# WellbeingService 测试
# =========================================================
def test_get_dashboard_summary_basic(monkeypatch):
    """测试仪表盘汇总逻辑（平均值 & 响应率）"""

    def fake_get_wellbeing_records(start_week, end_week, programme_id):
        assert start_week == 1 and end_week == 3
        assert programme_id is None
        # student_id, week, stress_level, hours_slept, programme_id
        return [
            (1, 1, 3, 8, "P1"),
            (2, 1, 5, 6, "P1"),
            (1, 2, 4, 7, "P1"),
            (3, 3, None, 7, "P1"),  # 没有压力值
        ]

    def fake_get_all_students():
        # student_id, name, email, programme_id
        return [
            (1, "Alice", "a@example.com", "P1"),
            (2, "Bob", "b@example.com", "P1"),
            (3, "Carol", "c@example.com", "P1"),
            (4, "Dave", "d@example.com", "P1"),
        ]

    monkeypatch.setattr(wb_mod, "get_wellbeing_records", fake_get_wellbeing_records)
    monkeypatch.setattr(wb_mod, "get_all_students", fake_get_all_students)

    svc = wb_mod.WellbeingService()
    result = svc.get_dashboard_summary(1, 3)

    # 平均压力：(3+5+4)/3 = 4.0
    assert result["avgStressLevel"] == 4.0
    # 平均睡眠：(8+6+7+7)/4 = 7.0
    assert result["avgHoursSlept"] == 7.0
    # 应答学生数量：{1,2,3} = 3
    assert result["surveyResponses"]["studentCount"] == 3
    # 总学生数 4 → 响应率 0.75 → round(0.75,2)*100 = 75.0
    assert result["surveyResponses"]["responseRate"] == 75.0


def test_get_dashboard_summary_programme_uses_programme_students(monkeypatch):
    """带 programme_id 时应调用 get_students_by_programme"""

    flags = {"by_prog": False, "all": False}

    def fake_get_wellbeing_records(start_week, end_week, programme_id):
        return []  # 不关心具体值

    def fake_get_students_by_programme(pid):
        flags["by_prog"] = True
        return [(1, "Alice", "a@example.com", pid)]

    def fake_get_all_students():
        flags["all"] = True
        return []

    monkeypatch.setattr(wb_mod, "get_wellbeing_records", fake_get_wellbeing_records)
    monkeypatch.setattr(
        wb_mod, "get_students_by_programme", fake_get_students_by_programme
    )
    monkeypatch.setattr(wb_mod, "get_all_students", fake_get_all_students)

    svc = wb_mod.WellbeingService()
    svc.get_dashboard_summary(1, 1, programme_id="P1")

    assert flags["by_prog"] is True
    # _get_student_count 在传入 programme_id 时不应调用 get_all_students
    assert flags["all"] is False


def test_get_dashboard_summary_invalid_weeks():
    svc = wb_mod.WellbeingService()
    with pytest.raises(ValueError):
        svc.get_dashboard_summary(5, 3)


def test_get_stress_sleep_trend(monkeypatch):
    """测试每周压力 / 睡眠趋势计算"""

    def fake_get_wellbeing_records(start_week, end_week, programme_id):
        return [
            (1, 1, 3, 8, "P1"),
            (2, 1, 5, 6, "P1"),
            (1, 2, None, 7, "P1"),  # 缺失压力
            (2, 2, 4, None, "P1"),  # 缺失睡眠
        ]

    monkeypatch.setattr(wb_mod, "get_wellbeing_records", fake_get_wellbeing_records)

    svc = wb_mod.WellbeingService()
    result = svc.get_stress_sleep_trend(1, 2)

    assert result["weeks"] == [1, 2]
    # week1: (3+5)/2 = 4.0；week2: 4/1 = 4.0
    assert result["stress"] == [4.0, 4.0]
    # week1: (8+6)/2 = 7.0；week2: 7/1 = 7.0
    assert result["sleep"] == [7.0, 7.0]


def test_get_stress_sleep_trend_invalid_weeks():
    svc = wb_mod.WellbeingService()
    with pytest.raises(ValueError):
        svc.get_stress_sleep_trend(4, 1)


def test_get_risk_students_high_and_potential(monkeypatch):
    """同时产生 high_risk 与 potential_risk"""

    def fake_get_wellbeing_records(start_week, end_week, programme_id):
        return [
            # 学生1：连续 3 周满足条件 → high_risk
            ("1", 1, 4.5, 5.0, "WM9QF"),
            ("1", 2, 4.6, 5.5, "WM9QF"),
            ("1", 3, 5.0, 5.0, "WM9QF"),
            # 学生2：只有一周满足条件 → potential_risk
            ("2", 1, 4.8, 5.5, "WM9QF"),
            ("2", 2, 3.0, 7.0, "WM9QF"),
        ]

    def fake_get_students_by_programme(pid):
        return [
            ("1", "Alice", "a@example.com", pid),
            ("2", "Bob", "b@example.com", pid),
        ]

    def fake_get_all_students():
        return fake_get_students_by_programme("WM9QF")

    monkeypatch.setattr(wb_mod, "get_wellbeing_records", fake_get_wellbeing_records)
    monkeypatch.setattr(
        wb_mod, "get_students_by_programme", fake_get_students_by_programme
    )
    monkeypatch.setattr(wb_mod, "get_all_students", fake_get_all_students)

    svc = wb_mod.WellbeingService()
    res = svc.get_risk_students(1, 3, programme_id="WM9QF")
    items = {item["studentId"]: item for item in res["items"]}

    assert items["1"]["riskType"] == "high_risk"
    assert "3 consecutive weeks" in items["1"]["reason"]
    assert items["1"]["modules"] == ["WM9QF"]

    assert items["2"]["riskType"] == "potential_risk"
    assert "Stress ≥" in items["2"]["reason"]
    assert items["2"]["modules"] == ["WM9QF"]


def test_get_risk_students_single_student_normal(monkeypatch):
    """指定 student_id 且无风险时，应返回 normal"""

    def fake_get_wellbeing_records(start_week, end_week, programme_id):
        # 只有该学生的数据，但都不满足风险条件
        return [
            ("3", 1, 3.0, 7.0, "WM9QF"),
            ("3", 2, 4.0, 7.5, "WM9QF"),
        ]

    def fake_get_all_students():
        return [("3", "Charlie", "c@example.com", "WM9QF")]

    monkeypatch.setattr(wb_mod, "get_wellbeing_records", fake_get_wellbeing_records)
    monkeypatch.setattr(wb_mod, "get_all_students", fake_get_all_students)

    svc = wb_mod.WellbeingService()
    res = svc.get_risk_students(1, 2, student_id="3")
    assert len(res["items"]) == 1
    item = res["items"][0]
    assert item["studentId"] == "3"
    assert item["riskType"] == "normal"
    assert item["name"] == "Charlie"
    assert "No risk detected" in item["reason"]


def test_get_risk_students_student_exists_but_no_data(monkeypatch):
    """学生存在但指定时间范围内没有 wellbeing 数据"""

    def fake_get_wellbeing_records(start_week, end_week, programme_id):
        # 不返回目标学生的数据
        return []

    def fake_get_all_students():
        return [
            ("9", "Nine", "nine@example.com", "P1"),
        ]

    monkeypatch.setattr(wb_mod, "get_wellbeing_records", fake_get_wellbeing_records)
    monkeypatch.setattr(wb_mod, "get_all_students", fake_get_all_students)

    svc = wb_mod.WellbeingService()
    res = svc.get_risk_students(1, 4, student_id="9")
    assert res["status"] == "no_data"
    assert "exists but has no wellbeing data" in res["message"]


def test_get_risk_students_student_not_found(monkeypatch):
    """学生在数据库中不存在"""

    def fake_get_wellbeing_records(start_week, end_week, programme_id):
        return []

    def fake_get_all_students():
        return [
            ("1", "Alice", "a@example.com", "P1"),
        ]

    monkeypatch.setattr(wb_mod, "get_wellbeing_records", fake_get_wellbeing_records)
    monkeypatch.setattr(wb_mod, "get_all_students", fake_get_all_students)

    svc = wb_mod.WellbeingService()
    res = svc.get_risk_students(1, 4, student_id="999")
    assert res["status"] == "not_found"
    assert "not found" in res["message"]


def test_get_risk_students_invalid_weeks():
    svc = wb_mod.WellbeingService()
    with pytest.raises(ValueError):
        svc.get_risk_students(10, 1)


# =========================================================
# AttendanceService 测试
# =========================================================
def test_get_attendance_by_module(monkeypatch):
    """测试模块出勤率统计"""

    def fake_get_attendance_by_module_weeks(start_week, end_week):
        assert start_week == 1 and end_week == 3
        # course_id, week, attended(0/1)
        return [
            ("WM9QF", 1, 1),
            ("WM9QF", 2, 0),
            ("WM9QF", 3, 1),
            ("CS101", 1, 1),
            ("CS101", 2, 1),
        ]

    monkeypatch.setattr(
    att_mod,
    "get_attendance_by_module_weeks",
    fake_get_attendance_by_module_weeks,
    raising=False,
)
    svc = att_mod.AttendanceService()
    res = svc.get_attendance_by_module(1, 3)
    items = {item["moduleCode"]: item for item in res["items"]}

    # WM9QF 出勤率：(1+0+1)/3 = 0.6667 → round(2) = 0.67
    assert items["WM9QF"]["attendanceRate"] == 0.67
    # CS101 出勤率：(1+1)/2 = 1.0
    assert items["CS101"]["attendanceRate"] == 1.0


def test_get_attendance_by_module_invalid_weeks():
    svc = att_mod.AttendanceService()
    with pytest.raises(ValueError):
        svc.get_attendance_by_module(5, 1)


# =========================================================
# UploadService 测试
# =========================================================
def test_read_csv_basic():
    """read_csv 应正确解析 CSV 为字典列表"""
    csv_content = "student_id,week,stress_level,hours_slept\n1,1,3,7\n"
    fs = DummyFileStorage(csv_content)
    rows = up_mod.read_csv(fs)
    assert rows == [
        {
            "student_id": "1",
            "week": "1",
            "stress_level": "3",
            "hours_slept": "7",
        }
    ]


def test_import_wellbeing_csv(monkeypatch):
    """import_wellbeing_csv 应调用 create.add_wellbeing 且传入 int 参数"""
    csv_content = (
        "student_id,week,stress_level,hours_slept\n"
        "1,1,3,7\n"
        "2,2,4,6\n"
    )
    fs = DummyFileStorage(csv_content)

    calls = []

    def fake_add_wellbeing(student_id, week, stress_level, hours_slept):
        calls.append((student_id, week, stress_level, hours_slept))

    # 覆盖数据库插入函数
    monkeypatch.setattr(
        up_mod.create, "add_wellbeing", fake_add_wellbeing, raising=False
    )

    up_mod.import_wellbeing_csv(fs)

    assert calls == [
        (1, 1, 3, 7),
        (2, 2, 4, 6),
    ]


def test_import_attendance_csv(monkeypatch):
    """import_attendance_csv 应调用 create.insert_attendance"""
    csv_content = (
        "student_id,module_code,week,attendance_status\n"
        "1,WM9QF,1,1\n"
        "2,WM9QF,1,0\n"
    )
    fs = DummyFileStorage(csv_content)

    calls = []

    def fake_insert_attendance(student_id, module_code, week, status):
        calls.append((student_id, module_code, week, status))

    monkeypatch.setattr(
        up_mod.create, "insert_attendance", fake_insert_attendance, raising=False
    )

    up_mod.import_attendance_csv(fs)

    assert calls == [
        (1, "WM9QF", 1, 1),
        (2, "WM9QF", 1, 0),
    ]


def test_import_submissions_csv(monkeypatch):
    """import_submissions_csv 应调用 create.insert_submission"""

    csv_content = (
        "student_id,module_code,submitted,grade,due_date,submit_date\n"
        "1,WM9QF,1,80,2024-01-01,2023-12-31\n"
        "2,WM9QF,0,,2024-01-01,\n"
    )
    fs = DummyFileStorage(csv_content)

    calls = []

    def fake_insert_submission(
        student_id, module_code, submitted, grade, due_date, submit_date
    ):
        calls.append(
            (
                student_id,
                module_code,
                submitted,
                grade,
                due_date,
                submit_date,
            )
        )

    monkeypatch.setattr(
        up_mod.create, "insert_submission", fake_insert_submission, raising=False
    )

    up_mod.import_submissions_csv(fs)

    # 第二行 grade 是空串，应转为 None；日期按原样传入
    assert calls == [
        (1, "WM9QF", 1, "80", "2024-01-01", "2023-12-31"),
        (2, "WM9QF", 0, None, "2024-01-01", ""),
    ]


def test_import_csv_by_type_dispatch(monkeypatch):
    """统一入口 import_csv_by_type 应正确分发"""

    fs = DummyFileStorage("dummy\n")

    flags = {"well": 0, "att": 0, "sub": 0}

    def fake_well(fs_arg):
        flags["well"] += 1
        assert fs_arg is fs

    def fake_att(fs_arg):
        flags["att"] += 1
        assert fs_arg is fs

    def fake_sub(fs_arg):
        flags["sub"] += 1
        assert fs_arg is fs

    monkeypatch.setattr(up_mod, "import_wellbeing_csv", fake_well)
    monkeypatch.setattr(up_mod, "import_attendance_csv", fake_att)
    monkeypatch.setattr(up_mod, "import_submissions_csv", fake_sub)

    up_mod.import_csv_by_type("wellbeing", fs)
    up_mod.import_csv_by_type("attendance", fs)
    up_mod.import_csv_by_type("submissions", fs)

    assert flags == {"well": 1, "att": 1, "sub": 1}


def test_import_csv_by_type_invalid():
    fs = DummyFileStorage("dummy\n")
    with pytest.raises(ValueError):
        up_mod.import_csv_by_type("unknown_type", fs)
