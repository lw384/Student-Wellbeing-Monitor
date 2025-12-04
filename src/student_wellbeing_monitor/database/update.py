# update.py
from student_wellbeing_monitor.database.db_core import get_conn


def update_wellbeing(record_id: int, new_stress: int, new_sleep: float):
    """Update stress_level and hours_slept using primary key id."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE wellbeing
        SET stress_level = ?, hours_slept = ?
        WHERE id = ?
        """,
        (new_stress, new_sleep, record_id),
    )
    conn.commit()
    conn.close()

    print(f"Updated wellbeing id={record_id}: stress={new_stress}, sleep={new_sleep}")


def update_attendance(record_id: int, status: int, week: int = None):
    conn = get_conn()
    cur = conn.cursor()

    if week is None:
        cur.execute(
            "UPDATE attendance SET status = ? WHERE id = ?", (status, record_id)
        )
    else:
        cur.execute(
            "UPDATE attendance SET status = ?, week = ? WHERE id = ?",
            (status, week, record_id),
        )

    conn.commit()
    conn.close()


def update_submission(
    record_id: int, submitted: int, grade: float, due_date, submit_date
):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        """
        UPDATE submission
        SET submitted = ?, grade = ?, due_date = ?, submit_date = ?
        WHERE id = ?
        """,
        (submitted, grade, due_date, submit_date, record_id),
    )

    conn.commit()
    conn.close()


def update_final_grade(student_id: str, new_grade: float):
    """Update final grade for a student."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "UPDATE grades SET final_grade = ? WHERE student_id = ?",
        (new_grade, student_id),
    )
    conn.commit()
    conn.close()
