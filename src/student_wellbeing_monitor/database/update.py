# update.py
from student_wellbeing_monitor.database.db_core import get_conn


def update_wellbeing_stress(student_id: str, week: int, new_stress: int):
    """Modify a student's stress value for a specific week."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE wellbeing 
        SET stress_level = ? 
        WHERE student_id = ? AND week = ?
        """,
        (new_stress, student_id, week),
    )
    conn.commit()
    conn.close()
    print(f"Updated stress level for {student_id} week {week} to {new_stress}")


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
