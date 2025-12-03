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
