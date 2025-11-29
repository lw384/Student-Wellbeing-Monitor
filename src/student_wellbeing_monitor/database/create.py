# create.py
from student_wellbeing_monitor.database.db_core import get_conn, _hash_pwd


# ================= Programme (Create) ==================


def insert_programme(
    programme_id,
    programme_name,
    programme_code,
):
    """Create a new programme."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO programme (programme_id, programme_name, programme_code) VALUES (?, ?, ?)",
        (programme_id, programme_name, programme_code),
    )
    conn.commit()
    sid = cur.lastrowid
    conn.close()
    return sid


# ================== Student  (Create) ==================
def insert_student(
    student_id,
    name,
    programme_id,
    email=None,
):
    """Create a new student."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO student (student_id, name, email,programme_id) VALUES (?, ?, ?,?)",
        (student_id, name, email, programme_id),
    )
    conn.commit()
    sid = cur.lastrowid
    conn.close()
    return sid


# ================== Module  (Create) ==================
def insert_module(module_id: str, module_name, module_code, programme_id):
    """Create a new module."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO module (module_id, module_name, module_code, programme_id) VALUES (?, ?, ?, ?)",
        (module_id, module_name, module_code, programme_id),
    )
    conn.commit()
    sid = cur.lastrowid
    conn.close()
    return sid


# ================== Student - Module  (Create) ==================


def insert_student_module(student_id: str, module_id: str):
    """
    Insert a record into student_module table.
    Only student_id and module_id are required,
    because id is AUTOINCREMENT.
    """

    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO student_module (student_id, module_id)
        VALUES (?, ?)
        """,
        (student_id, module_id),
    )

    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return new_id


# ================== Wellbeing (Create) ==================


def insert_wellbeing(student_id, week, stress_level, hours_slept, comment=None):
    """Create a wellbeing record."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO wellbeing (student_id, week, stress_level, hours_slept, comment) "
        "VALUES (?, ?, ?, ?, ?)",
        (student_id, week, stress_level, hours_slept, comment),
    )
    conn.commit()
    wid = cur.lastrowid
    conn.close()
    return wid


# ================== Attendance (Create) ==================


def add_attendance(sid, week, status):
    """status: present / absent / late"""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO attendance (student_id, week, status) VALUES (?, ?, ?)",
        (sid, week, status),
    )
    conn.commit()
    aid = cur.lastrowid
    conn.close()
    return aid


# ================== Assignment / Submission (Create) ==================


def add_submission(sid, ass_id, due_date, submit_date, grade):
    """Create a submission record."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO submissions "
        "(student_id, assignment_id, due_date, submit_date, grade) "
        "VALUES (?, ?, ?, ?, ?)",
        (sid, ass_id, due_date, submit_date, grade),
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return new_id


# ================== User & Roles (Create) ==================


def create_user(username, password, role):
    """
    role: 'swo' = wellbeing officer
        'cd'  = course director
    """
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
        (username, _hash_pwd(password), role),
    )
    conn.commit()
    uid = cur.lastrowid
    conn.close()
    return uid
