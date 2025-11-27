# db.py  

import sqlite3
import pandas as pd
import hashlib

DB_PATH = "data/student.db"

def get_conn():
    return sqlite3.connect(DB_PATH)

# ================== Student-related ==================

def insert_student(name, email=None):
    """Add a student to the 'students'"""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO students (name, email) VALUES (?, ?)",
        (name, email)
    )
    conn.commit()
    sid = cur.lastrowid
    conn.close()
    return sid


def get_all_students():
    """Check all students who is late"""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT student_id, name, email FROM students")
    rows = cur.fetchall()
    conn.close()
    return rows


def get_student_information(sid):
    """Just the id and name."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT student_id, name FROM students WHERE student_id = ?",
        (sid,)
    )
    row = cur.fetchone()
    conn.close()
    return row


# ================== wellbeing ==================

def add_wellbeing(sid, week, stress, sleep_hours):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO wellbeing (student_id, week, stress_level, hours_slept) "
        "VALUES (?, ?, ?, ?)",
        (sid, week, stress, sleep_hours)
    )
    conn.commit()
    wid = cur.lastrowid
    conn.close()
    return wid


def get_wellbeing_by_student(sid):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT week, stress_level, hours_slept "
        "FROM wellbeing WHERE student_id = ? ORDER BY week",
        (sid,)
    )
    rows = cur.fetchall()
    conn.close()
    return rows


# ================== Attendance ==================

def add_attendance(sid, week, status):
    """status: present / absent / late"""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO attendance (student_id, week, status) VALUES (?, ?, ?)",
        (sid, week, status)
    )
    conn.commit()
    aid = cur.lastrowid
    conn.close()
    return aid


def get_attendance_by_student(sid):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT week, status FROM attendance WHERE student_id = ? ORDER BY week",
        (sid,)
    )
    rows = cur.fetchall()
    conn.close()
    return rows


def get_attendance_rate(sid):
    """Attendance rate = number of times present / total number of times; return None if not recorded"""
    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        "SELECT COUNT(*) FROM attendance WHERE student_id = ?",
        (sid,)
    )
    total = cur.fetchone()[0]

    if total == 0:
        conn.close()
        return None

    cur.execute(
        "SELECT COUNT(*) FROM attendance "
        "WHERE student_id = ? AND status = 'present'",
        (sid,)
    )
    present = cur.fetchone()[0]
    conn.close()

    return present * 1.0 / total


# ================== Assignment ==================

def add_submission(sid, ass_id, due_date, submit_date, grade):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO submissions "
        "(student_id, assignment_id, due_date, submit_date, grade) "
        "VALUES (?, ?, ?, ?, ?)",
        (sid, ass_id, due_date, submit_date, grade)
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return new_id


def get_submissions_by_student(sid):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT assignment_id, due_date, submit_date, grade "
        "FROM submissions WHERE student_id = ? ORDER BY submission_id",
        (sid,)
    )
    rows = cur.fetchall()
    conn.close()
    return rows


# ================== User & Roles ==================

def _hash_pwd(pwd):
    """Simply make a hash"""
    return hashlib.sha256(pwd.encode("utf-8")).hexdigest()


def create_user(username, password, role):
    """
    role: 'swo' = wellbeing officer
        'cd'  = course director
    """
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
        (username, _hash_pwd(password), role)
    )
    conn.commit()
    uid = cur.lastrowid
    conn.close()
    return uid


def check_login(username, password):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT password_hash FROM users WHERE username = ?",
        (username,)
    )
    row = cur.fetchone()
    conn.close()
    if row is None:
        return False
    return row[0] == _hash_pwd(password)


def get_user_role(username):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT role FROM users WHERE username = ?",
        (username,)
    )
    row = cur.fetchone()
    conn.close()
    if row is None:
        return None
    return row[0]


# ================== 角色视图（CD / SWO） ==================

def get_student_info(username, sid):
    """
    CD can only see: student ID, name, attendance rate
    SWO can see : student ID, name, attendance record, wellbeing, and assignments
    """
    role = get_user_role(username)
    if role is None:
        print("User does not exist:", username)
        return None

    basic = get_student_information(sid)
    if basic is None:
        print("The student does not exist:", sid)
        return None

    # basic = (student_id, name)
    if role == "cd":
        rate = get_attendance_rate(sid)
        return (basic[0], basic[1], rate)

    if role == "swo":
        att = get_attendance_by_student(sid)
        wb = get_wellbeing_by_student(sid)
        sub = get_submissions_by_student(sid)
        return [basic, att, wb, sub]

    print("The role does not have permission:", role)
    return None
# ================== - Update ==================

def update_wellbeing_stress(student_id: str, week: int, new_stress: int):
    """Modify a certain student's stress value for a specific week on site"""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        UPDATE wellbeing 
        SET stress_level = ? 
        WHERE student_id = ? AND week = ?
    """, (new_stress, student_id, week))
    conn.commit()
    conn.close()
    print(f"Updated stress level for {student_id} week {week} to {new_stress}")

def update_final_grade(student_id: str, new_grade: float):
    """Modify Final Grade"""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE grades SET final_grade = ? WHERE student_id = ?", (new_grade, student_id))
    conn.commit()
    conn.close()

# ==================  Delete ==================

def delete_student(student_id: str):
    """Permanently delete a student"""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM students WHERE student_id = ?", (student_id,))
    conn.commit()
    conn.close()
    print(f"Student {student_id} and all related records have been deleted")


def get_course_stats(course_id: str):
    """nput a course ID: return the number of students in the course + the average stress level + the attendance rate."""
    conn = get_conn()
    df = pd.read_sql_query("""
        SELECT 
            c.course_name,
            COUNT(s.student_id) AS student_count,
            ROUND(AVG(w.stress_level),2) AS avg_stress,
            ROUND(AVG(a.attended)*100,1) AS avg_attendance_percent
        FROM courses c
        JOIN students s ON c.course_id = s.course_id
        LEFT JOIN wellbeing w ON s.student_id = w.student_id
        LEFT JOIN attendance a ON s.student_id = a.student_id
        WHERE c.course_id = ?
        GROUP BY c.course_id
    """, conn, params=(course_id,))
    conn.close()
    return df

if __name__ == "__main__":
    print(get_course_stats("WM9AA0")) 

# =========================================================
# ================ Analytical Functions and Statistics ================
# =========================================================

# ---------- weekly wellbeing summary ----------

def weekly_wellbeing_summary(start_week, end_week):
    """
    return [(week, avg_stress, avg_sleep, count), ...]
    """
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT
            week,
            AVG(stress_level) AS avg_stress,
            AVG(hours_slept)  AS avg_sleep,
            COUNT(*)          AS cnt
        FROM wellbeing
        WHERE week BETWEEN ? AND ?
        GROUP BY week
        ORDER BY week
        """,
        (start_week, end_week)
    )
    rows = cur.fetchall()
    conn.close()
    return rows


# ----------  high stress weeks ----------

def find_high_stress_weeks(threshold=4):
    """Weeks where the average stress level is ≥ the threshold"""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT
            week,
            AVG(stress_level) AS avg_stress
        FROM wellbeing
        GROUP BY week
        HAVING avg_stress >= ?
        ORDER BY week
        """,
        (threshold,)
    )
    rows = cur.fetchall()
    conn.close()
    return rows


# ----------  at-risk students ----------

def get_at_risk_students():
    """
    Simple rule:
    - if a student has ≥2 weeks where (stress >= 4 and sleep < 6),
    then mark the student as at-risk.Returns a dict: {student_id: [week1, week2, ...]}
    """
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT student_id, week
        FROM wellbeing
        WHERE stress_level >= 4 AND hours_slept < 6
        ORDER BY student_id, week
        """
    )
    rows = cur.fetchall()
    conn.close()

    tmp = {}
    for sid, wk in rows:
        if sid not in tmp:
            tmp[sid] = []
        tmp[sid].append(wk)

    result = {}
    for sid, weeks in tmp.items():
        if len(weeks) >= 2:  
            result[sid] = weeks

    return result


# ---------- stress vs attendance ----------

def stress_vs_attendance():
    """
    Weekly view: stress level vs attendance rate.
    return [(week, avg_stress, attendance_rate), ...]
    """
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT
            w.week,
            AVG(w.stress_level) AS avg_stress,
            AVG(CASE WHEN a.status='present' THEN 1.0 ELSE 0.0 END) AS att_rate
        FROM wellbeing w
        JOIN attendance a
        ON w.student_id = a.student_id AND w.week = a.week
        GROUP BY w.week
        ORDER BY w.week
        """
    )
    rows = cur.fetchall()
    conn.close()
    return rows


# ---------- attendance trend ----------

def attendance_trend():
    """
    Overall attendance trend by week
    return [(week, attendance_rate), ...]
    """
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT
            week,
            AVG(CASE WHEN status='present' THEN 1.0 ELSE 0.0 END) AS att_rate
        FROM attendance
        GROUP BY week
        ORDER BY week
        """
    )
    rows = cur.fetchall()
    conn.close()
    return rows


# ---------- submission behaviour ----------

def submission_behaviour():
    """
    View submission status for each assignment:
    (assignment_id, no_submit, on_time, total)
    """
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT
            assignment_id,
            SUM(CASE WHEN submit_date IS NULL THEN 1 ELSE 0 END) AS no_submit,
            SUM(CASE WHEN submit_date IS NOT NULL AND submit_date <= due_date
                    THEN 1 ELSE 0 END) AS on_time,
            COUNT(*) AS total
        FROM submissions
        GROUP BY assignment_id
        """
    )
    rows = cur.fetchall()
    conn.close()
    return rows


# ---------- low attendance ----------

def low_attendance(threshold=0.7):
    """
    Students whose attendance rate is below the threshold
    return [(student_id, att_rate), ...]
    """
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT
            student_id,
            AVG(CASE WHEN status='present' THEN 1.0 ELSE 0.0 END) AS att_rate
        FROM attendance
        GROUP BY student_id
        HAVING att_rate < ?
        """,
        (threshold,)
    )
    rows = cur.fetchall()
    conn.close()
    return rows


# ---------- FR-10: repeated late or missing submissions ----------

def repeated_late_submissions(min_bad=2):
    """
    Students with late or missing submissions ≥ min_bad.
    return [(student_id, bad_count), ...]
    """
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT
            student_id,
            COUNT(*) AS bad_count
        FROM submissions
        WHERE submit_date IS NULL OR submit_date > due_date
        GROUP BY student_id
        HAVING bad_count >= ?
        """,
        (min_bad,)
    )
    rows = cur.fetchall()
    conn.close()
    return rows


# ----------  attendance vs grade ----------

def attendance_vs_grade():
    """
    Returns a tuple: (student_id, attendance_rate, avg_grade)
    """
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT
            a.student_id,
            AVG(CASE WHEN a.status='present' THEN 1.0 ELSE 0.0 END) AS att_rate,
            AVG(s.grade) AS avg_grade
        FROM attendance a
        JOIN submissions s ON a.student_id = s.student_id
        GROUP BY a.student_id
        """
    )
    rows = cur.fetchall()
    conn.close()
    return rows

def get_continuous_high_stress_students():
    conn = get_conn()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("""
        WITH high AS (
            SELECT s.student_id, s.name, w.week, w.stress_level
            FROM wellbeing w JOIN students s ON w.student_id = s.student_id
            WHERE w.stress_level >= 4
        ),
        grouped AS (
            SELECT *,
                week - ROW_NUMBER() OVER (PARTITION BY student_id ORDER BY week) AS grp
            FROM high
        )
        SELECT student_id, name,
            COUNT(*) AS weeks,
            GROUP_CONCAT('Week ' || week) AS weeks_list
        FROM grouped
        GROUP BY student_id, name, grp
        HAVING weeks >= 3
        ORDER BY weeks DESC
    """)
    result = [dict(row) for row in cur.fetchall()]
    conn.close()
    return result

# test
if __name__ == "__main__":
    print("Students with high stress levels for three or more consecutive weeks:")
    print(get_continuous_high_stress_students())