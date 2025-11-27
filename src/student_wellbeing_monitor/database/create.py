# create.py
from student_wellbeing_monitor.database.db_core import get_conn, _hash_pwd


# ================== Student-related (Create) ==================


def insert_student(name, email=None):
    """Create a new student."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("INSERT INTO students (name, email) VALUES (?, ?)", (name, email))
    conn.commit()
    sid = cur.lastrowid
    conn.close()
    return sid


# ================== Wellbeing (Create) ==================


def add_wellbeing(sid, week, stress, sleep_hours):
    """Create a wellbeing record."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO wellbeing (student_id, week, stress_level, hours_slept) "
        "VALUES (?, ?, ?, ?)",
        (sid, week, stress, sleep_hours),
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
