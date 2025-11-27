# delete.py
from db_core import get_conn


def delete_student(student_id: str):
    """Permanently delete a student."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "DELETE FROM students WHERE student_id = ?",
        (student_id,)
    )
    conn.commit()
    conn.close()
    print(f"Student {student_id} and all related records have been deleted")
