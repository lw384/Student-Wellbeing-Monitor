import pytest
from student_wellbeing_monitor.ui.app import app as flask_app


@pytest.fixture()
def client():
    flask_app.config.update(
        {
            "TESTING": True,
            "WTF_CSRF_ENABLED": False,
        }
    )

    with flask_app.test_client() as client:
        yield client
