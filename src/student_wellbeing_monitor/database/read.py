# read.py
from student_wellbeing_monitor.database.db_core import get_conn, _hash_pwd
import sqlite3 as _sqlite3
import pandas as pd
from typing import List, Optional, Tuple


# ================== Student-related (Read) ==================
def _query_students(
    programme_id: Optional[str] = None,
    student_id: Optional[str] = None,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
):
    """内部通用 student 查询函数，不对外暴露"""
    conn = get_conn()
    cur = conn.cursor()

    base_sql = """
        SELECT student_id, name, email, programme_id
        FROM student
    """
    params = []
    conditions = []

    if programme_id and programme_id.strip():
        conditions.append("programme_id = ?")
        params.append(programme_id)

    if student_id and student_id.strip():
        conditions.append("student_id = ?")
        params.append(student_id)

    if conditions:
        base_sql += " WHERE " + " AND ".join(conditions)

    base_sql += " ORDER BY student_id"

    if limit is not None:
        base_sql += " LIMIT ?"
        params.append(limit)

        # offset 如果没传就默认 0
        if offset is not None:
            base_sql += " OFFSET ?"
            params.append(offset)

    print("SQL:", base_sql, "PARAMS:", params)

    cur.execute(base_sql, params)
    rows = cur.fetchall()
    conn.close()

    return rows


def count_students(programme_id: Optional[str] = None) -> int:
    conn = get_conn()
    cur = conn.cursor()

    sql = "SELECT COUNT(*) FROM student"
    params = []

    if programme_id:
        sql += " WHERE programme_id = ?"
        params.append(programme_id)

    cur.execute(sql, params)
    total = cur.fetchone()[0]
    conn.close()
    return total


def get_all_students(limit=None, offset=None):
    return _query_students(
        programme_id=None, student_id=None, limit=limit, offset=offset
    )


def get_students_by_programme(programme_id: str, limit=None, offset=None):
    """Return student information in one programme."""
    return _query_students(programme_id=programme_id, limit=limit, offset=offset)


def get_student_by_id(sid):
    """Return student information for a single student."""
    rows = _query_students(student_id=sid)
    return rows[0] if rows else None


# ================== Wellbeing (Read) ==================
def get_wellbeing_records(
    start_week: int,
    end_week: int,
    programme_id: Optional[str] = None,
    student_id: Optional[str] = None,
):
    conn = get_conn()
    cur = conn.cursor()

    # ------ 1. 基础 SQL ------
    sql = """
        SELECT 
            w.student_id,
            w.week,
            w.stress_level,
            w.hours_slept,
            s.programme_id
        FROM wellbeing AS w
        JOIN student AS s ON w.student_id = s.student_id
        WHERE w.week BETWEEN ? AND ?
    """

    params = [start_week, end_week]

    # ------ 2. programme_id ------
    if programme_id is not None:
        sql += " AND s.programme_id = ?"
        params.append(programme_id)

    if student_id is not None:
        sql += " AND w.student_id = ?"
        params.append(student_id)

    # ------ 3. sort ------
    sql += " ORDER BY w.student_id, w.week"

    cur.execute(sql, params)
    rows = cur.fetchall()
    conn.close()
    return rows


def get_all_weeks() -> list[int]:
    """
    week in wellbeing Ex: [1,2,3,...,8]
    """
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT week FROM wellbeing ORDER BY week")
    rows = cur.fetchall()
    conn.close()
    # rows ： [(1,), (2,), (3,)] →  [1,2,3]
    return [r[0] for r in rows]


def count_wellbeing():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM wellbeing")
    total = cur.fetchone()[0]
    conn.close()
    return total


def get_wellbeing_page(limit=20, offset=0):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, student_id, week, stress_level, hours_slept
        FROM wellbeing
        ORDER BY student_id, week
        LIMIT ? OFFSET ?
        """,
        (limit, offset),
    )
    rows = cur.fetchall()
    conn.close()
    return rows


def get_wellbeing_by_id(record_id: int):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """ 
          SELECT id, student_id, week, stress_level, hours_slept  
          FROM wellbeing 
          WHERE id = ?""",
        (record_id,),
    )
    row = cur.fetchone()
    conn.close()
    return row


# ================== Programme (Read) ==================


def get_programmes():
    conn = get_conn(row_factory=_sqlite3.Row)  # 让返回值变成 dict-like
    cur = conn.cursor()

    cur.execute(
        """
        SELECT programme_id, programme_code, programme_name
        FROM programme
        ORDER BY programme_code
    """
    )

    rows = cur.fetchall()
    conn.close()
    return rows


# ================== Module (Read) ==================
def get_all_modules():
    conn = get_conn(row_factory=_sqlite3.Row)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT programme_id, module_code, module_name
        FROM module
        ORDER BY programme_id, module_code
        """
    )
    rows = cur.fetchall()
    conn.close()
    return rows


# ================== Attendance (Read) ==================


def get_attendance_by_student(sid):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT week, status FROM attendance WHERE student_id = ? ORDER BY week", (sid,)
    )
    rows = cur.fetchall()
    conn.close()
    return rows


def get_attendance_rate(sid):
    """Attendance rate = present / total, or None if no records."""
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM attendance WHERE student_id = ?", (sid,))
    total = cur.fetchone()[0]

    if total == 0:
        conn.close()
        return None

    cur.execute(
        "SELECT COUNT(*) FROM attendance "
        "WHERE student_id = ? AND status = 'present'",
        (sid,),
    )
    present = cur.fetchone()[0]
    conn.close()
    return present * 1.0 / total


def get_attendance_filtered(
    programme_id=None, module_id=None, week_start=None, week_end=None
):

    conn = get_conn(row_factory=_sqlite3.Row)
    cur = conn.cursor()

    sql = """
        SELECT a.student_id, a.module_id, a.week, a.status
        FROM attendance a
        JOIN student s ON a.student_id = s.student_id
        WHERE 1=1
    """

    params = []

    if programme_id:
        sql += " AND s.programme_id = ?"
        params.append(programme_id)

    if module_id:  # if empty = all modules
        sql += " AND a.module_id = ?"
        params.append(module_id)

    if week_start:
        sql += " AND a.week >= ?"
        params.append(week_start)

    if week_end:
        sql += " AND a.week <= ?"
        params.append(week_end)

    cur.execute(sql, params)
    rows = cur.fetchall()
    conn.close()
    return rows


# ================== Submissions (Read) ==================


def get_submissions_by_student(sid):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT assignment_id, due_date, submit_date, grade "
        "FROM submission WHERE student_id = ? ORDER BY submission_id",
        (sid,),
    )
    rows = cur.fetchall()
    conn.close()
    return rows


def get_submissions_filtered(programme_id=None, module_id=None):

    conn = get_conn(row_factory=_sqlite3.Row)
    cur = conn.cursor()

    sql = """
        SELECT sub.student_id, sub.module_id, sub.submitted, sub.grade
        FROM submission sub
        JOIN student s ON sub.student_id = s.student_id
        WHERE 1=1
    """

    params = []

    if programme_id:
        sql += " AND s.programme_id = ?"
        params.append(programme_id)

    if module_id:
        sql += " AND sub.module_id = ?"
        params.append(module_id)

    cur.execute(sql, params)
    rows = cur.fetchall()
    conn.close()
    return rows


# ================== User & Roles  ==================


def check_login(username, password):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT password_hash FROM users WHERE username = ?", (username,))
    row = cur.fetchone()
    conn.close()
    if row is None:
        return False
    return row[0] == _hash_pwd(password)


def get_user_role(username):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT role FROM users WHERE username = ?", (username,))
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
        (start_week, end_week),
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
        (threshold,),
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
        (threshold,),
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
        (min_bad,),
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


# ----------  new  ----------
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
            JOIN student s ON w.student_id = s.student_id
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


def attendance_for_course(
    module_id: str,
    programme_id: Optional[str] = None,
    week_start: Optional[int] = None,
    week_end: Optional[int] = None,
) -> List[Tuple]:
    """
    为 get_attendance_trends 提供原始数据。

    返回每一条出勤记录：
      (module_id, module_name, student_id, student_name, week, status)
    """
    conn = get_conn(row_factory=_sqlite3.Row)
    cur = conn.cursor()

    sql = """
        SELECT
            m.module_id,
            m.module_name,
            s.student_id,
            s.name AS student_name,
            a.week,
            a.status
        FROM attendance AS a
        JOIN student_module AS sm
          ON a.student_id = sm.student_id
         AND a.module_id  = sm.module_id
        JOIN student AS s
          ON sm.student_id = s.student_id
        JOIN module AS m
          ON sm.module_id = m.module_id
        WHERE m.module_id = ?
    """
    params: List = [module_id]

    if programme_id is not None:
        sql += " AND s.programme_id = ?"
        params.append(programme_id)

    if week_start is not None:
        sql += " AND a.week >= ?"
        params.append(week_start)

    if week_end is not None:
        sql += " AND a.week <= ?"
        params.append(week_end)

    sql += " ORDER BY a.week, s.student_id"

    cur.execute(sql, params)
    rows = cur.fetchall()
    conn.close()
    return [tuple(r) for r in rows]


def attendance_detail_for_students(
    module_id: str,
    programme_id: Optional[str] = None,
    week_start: Optional[int] = None,
    week_end: Optional[int] = None,
) -> List[Tuple]:
    """
    为 get_low_attendance_students 提供原始数据。

    返回：
      (module_id, module_name, student_id, student_name, email, week, status)
    """
    conn = get_conn(row_factory=_sqlite3.Row)
    cur = conn.cursor()

    sql = """
        SELECT
            m.module_id,
            m.module_name,
            s.student_id,
            s.name AS student_name,
            s.email,
            a.week,
            a.status
        FROM attendance AS a
        JOIN student_module AS sm
          ON a.student_id = sm.student_id
         AND a.module_id  = sm.module_id
        JOIN student AS s
          ON sm.student_id = s.student_id
        JOIN module AS m
          ON sm.module_id = m.module_id
        WHERE m.module_id = ?
    """
    params: List = [module_id]

    if programme_id is not None:
        sql += " AND s.programme_id = ?"
        params.append(programme_id)

    if week_start is not None:
        sql += " AND a.week >= ?"
        params.append(week_start)

    if week_end is not None:
        sql += " AND a.week <= ?"
        params.append(week_end)

    sql += " ORDER BY s.student_id, a.week"

    cur.execute(sql, params)
    rows = cur.fetchall()
    conn.close()
    return [tuple(r) for r in rows]


def submissions_for_course(
    module_id: str,
    assignment_no: Optional[int] = None,
    programme_id: Optional[str] = None,
) -> List[Tuple]:
    """
    为 get_submission_summary 提供数据。

    逻辑：
      - student_module 找到所有选课学生
      - LEFT JOIN submission 得到 submitted(1/0)，无记录视为 0 (未交)

    返回：
      (module_id, module_name, student_id, submitted)
    """
    conn = get_conn(row_factory=_sqlite3.Row)
    cur = conn.cursor()

    join_condition = """
        sm.student_id = sub.student_id
        AND sm.module_id = sub.module_id
    """
    params: List = []

    if assignment_no is not None:
        join_condition += " AND sub.assignment_no = ?"
        params.append(assignment_no)

    sql = f"""
        SELECT
            m.module_id,
            m.module_name,
            s.student_id,
            COALESCE(sub.submitted, 0) AS submitted
        FROM student_module AS sm
        JOIN student AS s
          ON sm.student_id = s.student_id
        JOIN module AS m
          ON sm.module_id = m.module_id
        LEFT JOIN submission AS sub
          ON {join_condition}
        WHERE m.module_id = ?
    """
    params.append(module_id)

    if programme_id is not None:
        sql += " AND s.programme_id = ?"
        params.append(programme_id)

    sql += " ORDER BY s.student_id"

    cur.execute(sql, params)
    rows = cur.fetchall()
    conn.close()
    return [tuple(r) for r in rows]


def unsubmissions_for_repeated_issues(
    module_id: Optional[str] = None,
    programme_id: Optional[str] = None,
    week_start: Optional[int] = None,
    week_end: Optional[int] = None,
) -> List[Tuple]:
    """
    为 get_repeated_missing_students 提供数据。

    这里只有“未交(unsubmit)”这一种问题，没有迟交。

    返回：
      (module_id, module_name, assignment_no,
       student_id, student_name, email, submitted)
    """
    conn = get_conn(row_factory=_sqlite3.Row)
    cur = conn.cursor()

    sql = """
        SELECT
            m.module_id,
            m.module_name,
            sub.assignment_no,
            s.student_id,
            s.name AS student_name,
            s.email,
            sub.submitted
        FROM submission AS sub
        JOIN student AS s
          ON sub.student_id = s.student_id
        JOIN module AS m
          ON sub.module_id = m.module_id
        WHERE 1 = 1
    """
    params: List = []

    if module_id is not None:
        sql += " AND m.module_id = ?"
        params.append(module_id)

    if programme_id is not None:
        sql += " AND s.programme_id = ?"
        params.append(programme_id)

    # 如果你 submission 里没有 week，可以改成按 due_date 范围过滤
    if week_start is not None:
        sql += " AND sub.week >= ?"
        params.append(week_start)

    if week_end is not None:
        sql += " AND sub.week <= ?"
        params.append(week_end)

    sql += " ORDER BY s.student_id, m.module_id, sub.assignment_no"

    cur.execute(sql, params)
    rows = cur.fetchall()
    conn.close()
    return [tuple(r) for r in rows]


def attendance_and_grades(
    module_id: str,
    programme_id: Optional[str] = None,
    week_start: Optional[int] = None,
    week_end: Optional[int] = None,
) -> List[Tuple]:
    """
    为 get_attendance_vs_grades 提供数据。

    返回：
      (module_id, module_name, student_id, student_name, week, status, grade)
    """
    conn = get_conn(row_factory=_sqlite3.Row)
    cur = conn.cursor()

    sql = """
        SELECT
            m.module_id,
            m.module_name,
            s.student_id,
            s.name AS student_name,
            a.week,
            a.status,
            sub.grade
        FROM attendance AS a
        JOIN student_module AS sm
          ON a.student_id = sm.student_id
         AND a.module_id  = sm.module_id
        JOIN student AS s
          ON sm.student_id = s.student_id
        JOIN module AS m
          ON sm.module_id = m.module_id
        LEFT JOIN submission AS sub
          ON sub.student_id = sm.student_id
         AND sub.module_id  = sm.module_id
        WHERE m.module_id = ?
    """
    params: List = [module_id]

    if programme_id is not None:
        sql += " AND s.programme_id = ?"
        params.append(programme_id)

    if week_start is not None:
        sql += " AND a.week >= ?"
        params.append(week_start)

    if week_end is not None:
        sql += " AND a.week <= ?"
        params.append(week_end)

    sql += " ORDER BY s.student_id, a.week"

    cur.execute(sql, params)
    rows = cur.fetchall()
    conn.close()
    return [tuple(r) for r in rows]


def programme_wellbeing_engagement(
    module_id: str,
    week_start: Optional[int] = None,
    week_end: Optional[int] = None,
) -> List[Tuple]:
    """
    为 get_programme_wellbeing_engagement 以及其他综合分析提供数据。

    返回：
      (module_id, module_name,
       student_id,
       programme_id, programme_name,
       week,
       stress_level,
       hours_slept,
       attendance_status,
       submission_status,   -- 'submit' / 'unsubmit'
       grade)
    """
    conn = get_conn(row_factory=_sqlite3.Row)
    cur = conn.cursor()

    sql = """
        SELECT
            m.module_id,
            m.module_name,
            s.student_id,
            p.programme_id,
            p.programme_name,
            w.week,
            w.stress_level,
            w.hours_slept,
            a.status AS attendance_status,
            CASE
                WHEN sub.submitted = 1 THEN 'submit'
                WHEN sub.submitted = 0 THEN 'unsubmit'
                ELSE NULL
            END AS submission_status,
            sub.grade
        FROM student_module AS sm
        JOIN student AS s
          ON sm.student_id = s.student_id
        JOIN module AS m
          ON sm.module_id = m.module_id
        LEFT JOIN programme AS p
          ON s.programme_id = p.programme_id
        LEFT JOIN wellbeing AS w
          ON w.student_id = s.student_id
        LEFT JOIN attendance AS a
          ON a.student_id = s.student_id
         AND a.module_id  = sm.module_id
         AND a.week       = w.week
        LEFT JOIN submission AS sub
          ON sub.student_id = s.student_id
         AND sub.module_id  = sm.module_id
        WHERE m.module_id = ?
    """
    params: List = [module_id]

    if week_start is not None:
        sql += " AND w.week >= ?"
        params.append(week_start)

    if week_end is not None:
        sql += " AND w.week <= ?"
        params.append(week_end)

    sql += " ORDER BY p.programme_id, s.student_id, w.week"

    cur.execute(sql, params)
    rows = cur.fetchall()
    conn.close()
    return [tuple(r) for r in rows]
