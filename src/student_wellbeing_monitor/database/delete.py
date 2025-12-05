# delete.py
from student_wellbeing_monitor.database.db_core import get_conn


def delete_student(student_id: str):
    """Permanently delete a student."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM students WHERE student_id = ?", (student_id,))
    conn.commit()
    conn.close()
    print(f"Student {student_id} and all related records have been deleted")


def delete_all_students():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM student")
    conn.commit()
    conn.close()


def delete_all_wellbeing():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM wellbeing")
    conn.commit()
    conn.close()


def delete_all_attendance():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM attendance")
    conn.commit()
    conn.close()


def delete_all_submissions():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM submission")
    conn.commit()
    conn.close()


def delete_all_student_modules():
    """Delete all rows from the student_module junction table."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM student_module")
    conn.commit()
    conn.close()
