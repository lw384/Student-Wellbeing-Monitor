# read.py
from db_core import get_conn, _hash_pwd
import sqlite3 as _sqlite3
import pandas as pd


# ================== Student-related (Read) ==================

def get_all_students():
    """Return (student_id, name, email) for all students."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT student_id, name, email FROM students")
    rows = cur.fetchall()
    conn.close()
    return rows


def get_student_information(sid):
    """Return (student_id, name) for a single student."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT student_id, name FROM students WHERE student_id = ?",
        (sid,)
    )
    row = cur.fetchone()
    conn.close()
    return row


# ================== Wellbeing (Read) ==================

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


# ================== Attendance (Read) ==================

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
    """Attendance rate = present / total, or None if no records."""
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


# ================== Submissions (Read) ==================

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


# ================== User & Roles  ==================

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


def get_student_info(username, sid):
    """
    CD: id, name, attendance rate
    SWO: id, name, attendance record, wellbeing, submissions
    """
    role = get_user_role(username)
    if role is None:
        print("User does not exist:", username)
        return None

    basic = get_student_information(sid)
    if basic is None:
        print("The student does not exist:", sid)
        return None

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


# ================== Course-level stats ==================

def get_course_stats(course_id: str):
    """
    Input a course ID: return number of students, avg stress, attendance rate.
    """
    conn = get_conn()
    df = pd.read_sql_query(
        """
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
        """,
        conn,
        params=(course_id,),
    )
    conn.close()
    return df


# =========================================================
# ================ Analytical Functions ===================
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
    """Weeks where the average stress level is ≥ the threshold."""
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
    if a student has ≥2 weeks where (stress >= 4 and sleep < 6),
    mark as at-risk. Returns {student_id: [week1, week2, ...]}.
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
        tmp.setdefault(sid, []).append(wk)

    result = {sid: weeks for sid, weeks in tmp.items() if len(weeks) >= 2}
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
    Overall attendance trend by week.
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
            SUM(
                CASE 
                    WHEN submit_date IS NOT NULL AND submit_date <= due_date
                    THEN 1 ELSE 0 
                END
            ) AS on_time,
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
    Students whose attendance rate is below the threshold.
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


# ---------- repeated late or missing submissions ----------

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
    Returns (student_id, attendance_rate, avg_grade).
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
    """Students with high stress levels for three or more consecutive weeks."""
    conn = get_conn()
    conn.row_factory = _sqlite3.Row
    cur = conn.cursor()
    cur.execute(
        """
        WITH high AS (
            SELECT s.student_id, s.name, w.week, w.stress_level
            FROM wellbeing w 
            JOIN students s ON w.student_id = s.student_id
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
        """
    )
    result = [dict(row) for row in cur.fetchall()]
    conn.close()
    return result
