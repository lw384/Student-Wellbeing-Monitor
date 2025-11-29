# test/test_services.py
import io
import math
import pytest

import sys   #导入sys模块
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SRC_DIR))

from student_wellbeing_monitor.services import (
    wellbeing_service,
    service_utils,
    upload_service,
)

class DummyFileStorage:
    """简单模拟 werkzeug FileStorage，只保留 .stream 属性即可"""
    def __init__(self, content: str):
        self.stream = io.BytesIO(content.encode("utf-8"))


# -------------------------
# service_utils.py 的测试
# -------------------------

def test_mean_value_basic():
    result = service_utils.mean_value([1, 2, 3, 4])
    assert result == pytest.approx(2.5)


def test_completion_rate_basic():
    data = ["1", "0", "1", "1"]
    result = service_utils.completion_rate(data)
    assert result == pytest.approx(0.75, rel=1e-4)


def test_completion_rate_empty_list():
    assert service_utils.completion_rate([]) == 0.0


def test_completion_rate_custom_mark():
    data = ["YES", "NO", "YES"]
    result = service_utils.completion_rate(data, mark_submitted="YES")
    assert result == pytest.approx(2 / 3, rel=1e-4)


def test_count_above_threshold():
    data = [1, 2, 3, 4]
    assert service_utils.count_above_threshold(data, 2) == 2  # 3, 4


def test_count_below_threshold():
    data = [1, 2, 3, 4]
    assert service_utils.count_below_threshold(data, 2) == 1  # 1


def test_count_occurrences():
    data = ["a", "b", "a", "c", "a"]
    assert service_utils.count_occurrences(data, "a") == 3


def test_sum_value_basic_and_empty():
    assert service_utils.sum_value([1, 2, 3]) == 6.0
    assert service_utils.sum_value([]) == 0.0


def test_group_stress_by_student_basic():
    records = [
        {"student_id": "s1", "stress": 3},
        {"student_id": "s1", "stress": 4},
        {"student_id": "s2", "stress": 5},
        {"student_id": "s2", "stress": None},  # 应该被忽略
        {"student_id": None, "stress": 1},     # 没有 student_id 应该被忽略
    ]
    result = service_utils.group_stress_by_student(records)
    assert result == {
        "s1": [3, 4],
        "s2": [5],
    }


# -------------------------
# wellbeing_service.py 的测试
# -------------------------

def test_flag_high_stress_students_empty_records():
    risky_ids, risky_weeks = wellbeing_service.flag_high_stress_students([])
    assert risky_ids == []
    assert risky_weeks == {}


def test_flag_high_stress_students_last_max_level_or_consecutive():
    records = [
        # s1：最后一次压力值 == max_level，应标记
        {"student_id": "s1", "week": 1, "stress": 3},
        {"student_id": "s1", "week": 2, "stress": 5},

        # s2：连续三周 >= threshold，应标记
        {"student_id": "s2", "week": 1, "stress": 4},
        {"student_id": "s2", "week": 2, "stress": 4},
        {"student_id": "s2", "week": 3, "stress": 4},
    ]

    risky_ids, risky_weeks = wellbeing_service.flag_high_stress_students(records)

    assert set(risky_ids) == {"s1", "s2"}
    assert risky_weeks["s1"] == [(2, 5.0)]
    assert risky_weeks["s2"] == [(1, 4.0), (2, 4.0), (3, 4.0)]


def test_flag_high_stress_students_week_filter():
    records = [
        {"student_id": "s1", "week": 1, "stress": 5},
        {"student_id": "s1", "week": 2, "stress": 5},
        {"student_id": "s1", "week": 3, "stress": 5},
        {"student_id": "s1", "week": 4, "stress": 2},
    ]

    # 不加过滤时，s1 连续三周 >=4，应标记
    risky_ids_all, _ = wellbeing_service.flag_high_stress_students(
        records, threshold=4.0, max_weeks=3
    )
    assert "s1" in risky_ids_all

    # 只看 week 3-4，连续性被打断，不应再标记
    risky_ids_filtered, _ = wellbeing_service.flag_high_stress_students(
        records, threshold=4.0, max_weeks=3, start_week=3, end_week=4
    )
    assert "s1" not in risky_ids_filtered


def test_flag_high_stress_students_ignore_none_and_empty():
    records = [
        {"student_id": "s1", "week": 1, "stress": None},
        {"student_id": "s1", "week": 2, "stress": ""},
        {"student_id": "s1", "week": 3, "stress": 5},
    ]
    risky_ids, risky_weeks = wellbeing_service.flag_high_stress_students(records)
    assert risky_ids == ["s1"]
    assert risky_weeks["s1"] == [(1, 5.0)]  # 第一个有效 stress 是 5，对应 enumerate 起始 1


def test_weekly_sleep_trend_basic():
    records = [
        {"student_id": "s1", "week": 1, "sleep_hours": 8},
        {"student_id": "s2", "week": 1, "sleep_hours": 6},
        {"student_id": "s1", "week": 2, "sleep_hours": 7},
        {"student_id": "s2", "week": 2, "sleep_hours": None},  # 忽略
        {"student_id": "s3", "week": 3, "sleep_hours": 5},
    ]
    y_sleep, week_lowest = wellbeing_service.weekly_sleep_trend(records)
    assert y_sleep[1] == pytest.approx(7.0)  # (8+6)/2
    assert y_sleep[2] == pytest.approx(7.0)  # 7/1
    assert y_sleep[3] == pytest.approx(5.0)
    assert week_lowest == 3


def test_weekly_sleep_trend_no_valid_data():
    # 有 records，但都因为 week/sleep_hours 无效被过滤掉
    records = [
        {"week": None, "sleep_hours": 7},
        {"week": 1, "sleep_hours": None},
    ]
    y_sleep, week_lowest = wellbeing_service.weekly_sleep_trend(records)
    assert y_sleep == {}
    assert week_lowest is None


def test_weekly_sleep_trend_empty_after_filter_should_return_empty_and_none():
    # 记录存在，但通过 start_week/end_week 过滤后为空
    records = [{"week": 1, "sleep_hours": 7}]
    y_sleep, week_lowest = wellbeing_service.weekly_sleep_trend(
        records, start_week=2
    )
    # 期望接口语义：无数据 -> 空 dict + None
    assert isinstance(y_sleep, dict)
    assert y_sleep == {}
    assert week_lowest is None


def test_weekly_stress_trend_basic():
    records = [
        {"student_id": "s1", "week": 1, "stress": 1},
        {"student_id": "s2", "week": 1, "stress": 3},
        {"student_id": "s3", "week": 2, "stress": 4},
    ]
    y_stress, week_highest = wellbeing_service.weekly_stress_trend(records)
    assert y_stress[1] == pytest.approx(2.0)  # (1+3)/2
    assert y_stress[2] == pytest.approx(4.0)
    assert week_highest == 2


def test_weekly_stress_trend_no_valid_data():
    records = [
        {"week": None, "stress": 3},
        {"week": 1, "stress": None},
    ]
    y_stress, week_highest = wellbeing_service.weekly_stress_trend(records)
    assert y_stress == {}
    assert week_highest is None


def test_weekly_stress_trend_empty_after_filter_should_return_empty_and_none():
    records = [{"week": 1, "stress": 3}]
    y_stress, week_highest = wellbeing_service.weekly_stress_trend(
        records, start_week=2
    )
    assert isinstance(y_stress, dict)
    assert y_stress == {}
    assert week_highest is None


# -------------------------
# upload_service.py 的测试
# -------------------------

def test_read_csv_basic():
    csv_content = (
        "student_id,week,stress_level,hours_slept\n"
        "1,1,4,7\n"
        "2,1,2,8\n"
    )
    fs = DummyFileStorage(csv_content)
    rows = upload_service.read_csv(fs)

    assert rows == [
        {
            "student_id": "1",
            "week": "1",
            "stress_level": "4",
            "hours_slept": "7",
        },
        {
            "student_id": "2",
            "week": "1",
            "stress_level": "2",
            "hours_slept": "8",
        },
    ]


def test_import_wellbeing_csv_calls_create(monkeypatch):
    captured = []

    def fake_add_wellbeing(student_id, week, stress_level, hours_slept):
        captured.append((student_id, week, stress_level, hours_slept))

    monkeypatch.setattr(upload_service.create, "add_wellbeing", fake_add_wellbeing)

    csv_content = (
        "student_id,week,stress_level,hours_slept\n"
        "1,1,4,7\n"
        "2,3,5,6\n"
    )
    fs = DummyFileStorage(csv_content)
    upload_service.import_wellbeing_csv(fs)

    assert captured == [
        (1, 1, 4, 7),
        (2, 3, 5, 6),
    ]


def test_import_attendance_csv_calls_create(monkeypatch):
    captured = []

    def fake_insert_attendance(*, student_id, module_code, week, status):
        captured.append((student_id, module_code, week, status))

    monkeypatch.setattr(upload_service.create, "insert_attendance", fake_insert_attendance)

    csv_content = (
        "student_id,module_code,week,attendance_status\n"
        "1,CS101,1,1\n"
        "2,CS102,2,0\n"
    )
    fs = DummyFileStorage(csv_content)
    upload_service.import_attendance_csv(fs)

    assert captured == [
        (1, "CS101", 1, 1),
        (2, "CS102", 2, 0),
    ]


def test_import_submissions_csv_calls_create(monkeypatch):
    captured = []

    def fake_insert_submission(*, student_id, module_code, submitted,
                               grade, due_date, submit_date):
        captured.append((student_id, module_code, submitted,
                         grade, due_date, submit_date))

    monkeypatch.setattr(upload_service.create, "insert_submission", fake_insert_submission)

    csv_content = (
        "student_id,module_code,submitted,grade,due_date,submit_date\n"
        "1,CS101,1,85,2024-01-01,2024-01-01\n"
        "2,CS101,0,,2024-01-01,\n"
    )
    fs = DummyFileStorage(csv_content)
    upload_service.import_submissions_csv(fs)

    assert captured == [
        (1, "CS101", 1, "85", "2024-01-01", "2024-01-01"),
        (2, "CS101", 0, None, "2024-01-01", ""),  # grade 为空串应变 None
    ]


def test_import_csv_by_type_dispatch(monkeypatch):
    called = {"wellbeing": 0, "attendance": 0, "submissions": 0}

    def fake_wellbeing(fs):
        called["wellbeing"] += 1

    def fake_attendance(fs):
        called["attendance"] += 1

    def fake_submissions(fs):
        called["submissions"] += 1

    monkeypatch.setattr(upload_service, "import_wellbeing_csv", fake_wellbeing)
    monkeypatch.setattr(upload_service, "import_attendance_csv", fake_attendance)
    monkeypatch.setattr(upload_service, "import_submissions_csv", fake_submissions)

    fs = DummyFileStorage("a,b\n1,2\n")

    upload_service.import_csv_by_type("wellbeing", fs)
    upload_service.import_csv_by_type("attendance", fs)
    upload_service.import_csv_by_type("submissions", fs)

    assert called == {"wellbeing": 1, "attendance": 1, "submissions": 1}


def test_import_csv_by_type_invalid_type():
    fs = DummyFileStorage("a,b\n1,2\n")
    with pytest.raises(ValueError):
        upload_service.import_csv_by_type("unknown_type", fs)


