import sqlite3
from typing import List, Dict, Any, Optional, Tuple

# ========= 数据库文件路径 =========
# 这里假设你的数据库文件名是 student.db，并且和 db.py 在同一文件夹下。
# 如果实际叫 wellbeing.db 或者在别的路径，请改成正确的。
DB_PATH = "C:/Users/Jack/Desktop/Warwick_WM9QF/Assignment/Group/Student-Wellbeing-Monitor/src/database/data/student.db"

# =============== 基础工具函数 ===============

def get_conn() -> sqlite3.Connection:
    """获取数据库连接。"""
    return sqlite3.connect(DB_PATH)


# =============== 原有 4 个查询（已按真实表结构修正） ===============

def get_course_wellbeing(
    start_week: int,
    end_week: int,
    course_id: str,
) -> List[Dict[str, Any]]:
    """
    查询某课程 start_week 到 end_week 的压力和睡眠记录。

    返回 List[Dict]，每个 dict 结构：
    {
        "course_id": ...,
        "week": ...,
        "stress": ...,
        "sleep_hours": ...
    }
    """
    conn = get_conn()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute(
        f"""
        SELECT
            s.course_id,
            w.week,
            w.stress_level AS stress,
            w.hours_slept  AS sleep_hours
        FROM wellbeing w
        JOIN students s ON w.student_id = s.student_id
        WHERE s.course_id = ?
          AND w.week BETWEEN ? AND ?
        ORDER BY w.week ASC
        """,
        (course_id, start_week, end_week),
    )

    rows = cur.fetchall()
    conn.close()

    return [
        {
            "course_id": row["course_id"],
            "week": row["week"],
            "stress": row["stress"],
            "sleep_hours": row["sleep_hours"],
        }
        for row in rows
    ]


def get_all_courses_wellbeing(
    start_week: int,
    end_week: int,
) -> List[Dict[str, Any]]:
    """
    查询所有课程 start_week 到 end_week 的压力和睡眠记录。
    返回 List[Dict]，结构同上。
    """
    conn = get_conn()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute(
        f"""
        SELECT
            s.course_id,
            w.week,
            w.stress_level AS stress,
            w.hours_slept  AS sleep_hours
        FROM wellbeing w
        JOIN students s ON w.student_id = s.student_id
        WHERE w.week BETWEEN ? AND ?
        ORDER BY s.course_id, w.week ASC
        """,
        (start_week, end_week),
    )

    rows = cur.fetchall()
    conn.close()

    return [
        {
            "course_id": row["course_id"],
            "week": row["week"],
            "stress": row["stress"],
            "sleep_hours": row["sleep_hours"],
        }
        for row in rows
    ]


def get_all_students_wellbeing(
    start_week: int,
    end_week: int,
) -> List[Dict[str, Any]]:
    """
    查询所有学生 start_week 到 end_week 的压力和睡眠记录。
    返回 List[Dict]：
    {
        "student_id": ...,
        "course_id": ...,
        "week": ...,
        "stress": ...,
        "sleep_hours": ...
    }
    """
    conn = get_conn()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute(
        f"""
        SELECT
            w.student_id,
            s.course_id,
            w.week,
            w.stress_level AS stress,
            w.hours_slept  AS sleep_hours
        FROM wellbeing w
        JOIN students s ON w.student_id = s.student_id
        WHERE w.week BETWEEN ? AND ?
        ORDER BY w.student_id, w.week ASC
        """,
        (start_week, end_week),
    )

    rows = cur.fetchall()
    conn.close()

    return [
        {
            "student_id": row["student_id"],
            "course_id": row["course_id"],
            "week": row["week"],
            "stress": row["stress"],
            "sleep_hours": row["sleep_hours"],
        }
        for row in rows
    ]


def get_wellbeing_by_student(
    student_id: str,
    start_week: int,
    end_week: int,
) -> List[Dict[str, Any]]:
    """
    查询某学生 start_week 到 end_week 的压力和睡眠记录。
    返回 List[Dict]，结构同上。
    """
    conn = get_conn()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute(
        f"""
        SELECT
            w.student_id,
            s.course_id,
            w.week,
            w.stress_level AS stress,
            w.hours_slept  AS sleep_hours
        FROM wellbeing w
        JOIN students s ON w.student_id = s.student_id
        WHERE w.student_id = ?
          AND w.week BETWEEN ? AND ?
        ORDER BY w.week ASC
        """,
        (student_id, start_week, end_week),
    )

    rows = cur.fetchall()
    conn.close()

    return [
        {
            "student_id": row["student_id"],
            "course_id": row["course_id"],
            "week": row["week"],
            "stress": row["stress"],
            "sleep_hours": row["sleep_hours"],
        }
        for row in rows
    ]


# =============== Dashboard / Service 用的新接口 ===============

def get_all_students() -> List[Tuple[Any, ...]]:
    """
    返回所有学生基本信息，用于统计总人数。

    返回每行：(student_id, name, course_id)
    """
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT student_id, name, course_id
        FROM students
        ORDER BY student_id
        """
    )
    rows = cur.fetchall()
    conn.close()
    return rows


def get_course_students(course_id: str) -> List[Tuple[Any, ...]]:
    """
    返回某课程下的学生列表，用于统计该课程学生数。

    返回每行：(student_id, name, course_id)
    """
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT student_id, name, course_id
        FROM students
        WHERE course_id = ?
        ORDER BY student_id
        """,
        (course_id,),
    )
    rows = cur.fetchall()
    conn.close()
    return rows


def get_wellbeing_by_week_and_course(
    start_week: int,
    end_week: int,
    course_id: Optional[str] = None,
) -> List[Tuple[Any, ...]]:
    """
    返回指定周区间 & 课程范围内的 wellbeing 原始数据。

    返回 List[tuple]，每行：
        (course_id, student_id, week, stress_level, hours_slept)

    - course_id 为 None → 所有课程
    - 否则只筛选该课程
    """
    conn = get_conn()
    cur = conn.cursor()

    if course_id is None:
        # 所有课程
        cur.execute(
            f"""
            SELECT
                s.course_id,
                w.student_id,
                w.week,
                w.stress_level,
                w.hours_slept
            FROM wellbeing w
            JOIN students s ON w.student_id = s.student_id
            WHERE w.week BETWEEN ? AND ?
            ORDER BY s.course_id, w.student_id, w.week
            """,
            (start_week, end_week),
        )
    else:
        # 某一门课程
        cur.execute(
            f"""
            SELECT
                s.course_id,
                w.student_id,
                w.week,
                w.stress_level,
                w.hours_slept
            FROM wellbeing w
            JOIN students s ON w.student_id = s.student_id
            WHERE s.course_id = ?
              AND w.week BETWEEN ? AND ?
            ORDER BY w.student_id, w.week
            """,
            (course_id, start_week, end_week),
        )

    rows = cur.fetchall()
    conn.close()
    return rows


def get_attendance_by_module_weeks(
    start_week: int,
    end_week: int,
) -> List[Tuple[Any, ...]]:
    """
    返回所有课程在 [start_week, end_week] 区间的出勤记录。

    预期返回每行：
        (course_id, week, attended)

    这里假设：
        - attendance 表字段：student_id, week, attended
        - students 表字段：student_id, course_id
        - attended: 1 = 出席, 0 = 缺席
    如果你实际 attendance 表字段不同，可以根据实际字段名调整 SQL。
    """
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT
            s.course_id,
            a.week,
            a.attended
        FROM attendance a
        JOIN students s ON a.student_id = s.student_id
        WHERE a.week BETWEEN ? AND ?
        ORDER BY s.course_id, a.week, a.student_id
        """,
        (start_week, end_week),
    )
    rows = cur.fetchall()
    conn.close()
    return rows
