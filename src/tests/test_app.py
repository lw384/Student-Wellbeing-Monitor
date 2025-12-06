from io import BytesIO
from unittest.mock import patch
import pytest


# -----------------------
#  Test: Index page
# -----------------------
def test_index_page(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"role" in resp.data or b"Dashboard" in resp.data


# -----------------------
#  Test: Dashboard (Wellbeing)
# -----------------------
@patch("student_wellbeing_monitor.database.read.get_all_weeks", return_value=[1, 2, 3])
@patch("student_wellbeing_monitor.database.read.get_programmes", return_value=[])
@patch("student_wellbeing_monitor.services.wellbeing_service.get_dashboard_summary")
def test_dashboard_wellbeing(mock_summary, mock_prog, mock_weeks, client):
    mock_summary.return_value = {
        "surveyResponses": {"studentCount": 5, "responseRate": 0.5},
        "avgHoursSlept": 7,
        "avgStressLevel": 3,
    }

    resp = client.get("/dashboard/wellbeing")
    assert resp.status_code == 200
    assert b"Avg Stress" in resp.data


# -----------------------
#  Test: Dashboard (Course Leader)
# -----------------------
@patch("student_wellbeing_monitor.database.read.get_all_weeks", return_value=[1, 2, 3])
@patch(
    "student_wellbeing_monitor.database.read.get_programmes",
    return_value=[
        {"programme_id": "P1", "programme_code": "C1", "programme_name": "Programme 1"}
    ],
)
@patch("student_wellbeing_monitor.ui.app.course_service.get_course_leader_summary")
def test_dashboard_course_leader(mock_summary, mock_prog, mock_weeks, client):
    mock_summary.return_value = {
        "avg_attendance_rate": 0.9,
        "avg_submission_rate": 0.8,
        "avg_grade": 70,
    }

    resp = client.get("/dashboard/course_leader")
    assert resp.status_code == 200
    assert b"Avg Attendance Rate" in resp.data


# -----------------------
#  Test: AI Analysis Trigger
# -----------------------
@patch(
    "student_wellbeing_monitor.ui.app.course_service.analyze_high_stress_sleep_with_ai"
)
@patch(
    "student_wellbeing_monitor.database.read.get_programmes",
    return_value=[
        {
            "programme_id": "P1",
            "programme_code": "X",
            "programme_name": "Test Programme",
        }
    ],
)
@patch("student_wellbeing_monitor.database.read.get_all_weeks", return_value=[1, 2, 3])
def test_ai_analysis_triggered(mock_weeks, mock_prog, mock_ai, client):
    # 注意：参数顺序与 patch 装饰器顺序一致：
    # mock_ai -> analyze_high_stress_sleep_with_ai
    # mock_prog -> get_programmes
    # mock_weeks -> get_all_weeks
    mock_ai.return_value = {"aiAnalysis": {"status": "ok", "text": "AI summary"}}

    resp = client.get("/dashboard/wellbeing?programme_id=P1&run_ai=1")
    assert resp.status_code == 200

    mock_ai.assert_called_once()
    assert b"AI summary" in resp.data


# -----------------------
#  Test: Upload page GET
# -----------------------
def test_upload_page(client):
    resp = client.get("/upload/wellbeing")
    assert resp.status_code == 200
    assert b"Upload" in resp.data


# -----------------------
#  Test: Upload CSV POST
# -----------------------
@patch("student_wellbeing_monitor.ui.app.import_csv_by_type")
def test_upload_csv(mock_import, client):
    data = {
        "data_type": "wellbeing",
        "file": (BytesIO(b"dummy,data"), "test.csv"),
    }
    resp = client.post(
        "/upload/wellbeing", data=data, content_type="multipart/form-data"
    )

    # 上传成功后应进行重定向
    assert resp.status_code in (302, 303)
    mock_import.assert_called_once()


# -----------------------
#  Test: View data (students)
# -----------------------
@patch("student_wellbeing_monitor.database.read.get_programmes", return_value=[])
@patch("student_wellbeing_monitor.database.read.count_students", return_value=1)
@patch("student_wellbeing_monitor.database.read.get_all_students")
def test_view_students_table(mock_get, mock_count, mock_prog, client):
    mock_get.return_value = [
        {
            "student_id": "1001",
            "name": "Alice",
            "email": "alice@test.com",
            "programme_id": "P1",
        }
    ]

    # 加 follow_redirects=True，避免 308 重定向导致断言失败
    resp = client.get("/data/wellbeing/students", follow_redirects=True)
    assert resp.status_code == 200


# -----------------------
#  Test: Edit wellbeing GET
# -----------------------
@patch("student_wellbeing_monitor.database.read.get_wellbeing_by_id")
def test_edit_wellbeing_get(mock_get, client):
    mock_get.return_value = {
        "id": 1,
        "student_id": "1001",
        "week": 1,
        "stress_level": 3,
        "hours_slept": 6.5,
    }

    resp = client.get("/data/wellbeing/wellbeing/1/edit")
    assert resp.status_code == 200
    assert b"Stress Level" in resp.data


# -----------------------
#  Test: Edit wellbeing POST
# -----------------------
@patch("student_wellbeing_monitor.ui.app.update_wellbeing")
@patch("student_wellbeing_monitor.ui.app.get_wellbeing_by_id")
def test_edit_wellbeing_post(mock_get, mock_update, client):
    # 注意：装饰器从下往上应用，所以参数顺序是：
    # mock_get -> get_wellbeing_by_id
    # mock_update -> update_wellbeing
    mock_get.return_value = {
        "id": 1,
        "student_id": "1001",
        "week": 1,
        "stress_level": 3,
        "hours_slept": 6.5,
    }

    resp = client.post(
        "/data/wellbeing/wellbeing/1/edit",
        data={"stress_level": "4", "hours_slept": "7.0"},
        follow_redirects=False,
    )

    assert resp.status_code in (302, 303)
    mock_update.assert_called_once_with(1, 4, 7.0)


# -----------------------
#  Test: dashboard invalid role
# -----------------------
def test_dashboard_invalid_role_redirect(client):
    resp = client.get("/dashboard/invalid-role", follow_redirects=False)
    assert resp.status_code in (302, 303)


# -----------------------
# Pytest fixture for flask client
# -----------------------
@pytest.fixture
def client():
    from student_wellbeing_monitor.ui.app import app

    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client
