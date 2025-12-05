# attendance_service.py

from collections import defaultdict
from typing import Any, Dict, List, Optional

from student_wellbeing_monitor.database.read import (
    attendance_detail_for_students,
    attendance_for_course,
)


# =========================================================
# Class: AttendanceService
# =========================================================
class AttendanceService:
    """
    Attendance-related services from the Course Leader's perspective.

    contain the method in APIdocuemnt.md:
      1️⃣ get_attendance_trends
      3️⃣ get_low_attendance_students
    """

    # -------------------------------------------------
    # 1️⃣ check attendance trends by week
    # -------------------------------------------------
    def get_attendance_trends(
        self,
        course_id: str,
        programme_id: Optional[str] = None,
        week_start: Optional[int] = None,
        week_end: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        get_attendance_trends(course_id, programme_id=None, week_start=None, week_end=None)

        return:
        {
          "courseId": "...",
          "courseName": "...",
          "points": [
            {
              "week": 1,
              "attendanceRate": 0.8,
              "presentCount": 120,
              "totalCount": 150
            },
            ...
          ]
        }
        """
        rows = attendance_for_course(
            programme_id=programme_id,
            module_id=course_id,
            week_start=week_start,
            week_end=week_end,
        )
        # rows: (module_id, module_name, student_id, student_name, week, status)
        if not rows:
            return {
                "courseId": course_id,
                "courseName": None,
                "points": [],
            }

        course_name = rows[0][1]

        present_by_week: Dict[int, int] = defaultdict(int)
        total_by_week: Dict[int, int] = defaultdict(int)

        for _mid, _mname, _sid, _sname, week, status in rows:
            if week is None:
                continue
            w = int(week)
            total_by_week[w] += 1
            # status 为 0 / 1（0 缺勤，1 出勤）
            if status is not None and int(status) == 1:
                present_by_week[w] += 1

        points: List[Dict[str, Any]] = []
        for week in sorted(total_by_week.keys()):
            total = total_by_week[week]
            present = present_by_week.get(week, 0)
            rate = present / total if total > 0 else 0.0
            points.append(
                {
                    "week": week,
                    "attendanceRate": round(rate, 2),
                    "presentCount": int(present),
                    "totalCount": int(total),
                }
            )
        return {
            "courseId": course_id,
            "courseName": course_name,
            "points": points,
        }

    # -------------------------------------------------
    # 3️⃣ list of students with low attendance
    # -------------------------------------------------
    def get_low_attendance_students(
        self,
        course_id: str,
        programme_id: Optional[str] = None,
        week_start: Optional[int] = None,
        week_end: Optional[int] = None,
        threshold_rate: float = 0.8,
        min_absences: int = 2,
    ) -> Dict[str, Any]:
        """
        get_low_attendance_students(
            course_id,
            programme_id=None,
            week_start=None,
            week_end=None,
            threshold_rate=0.8,
            min_absences=2,
        )

        return:
        {
          "courseId": "...",
          "courseName": "...",
          "students": [
            {
              "studentId": "S0001",
              "name": "Alice",
              "email": "alice@example.com",
              "attendanceRate": 0.6,
              "absentSessions": 4
            },
            ...
          ]
        }
        """
        rows = attendance_detail_for_students(
            module_id=course_id,
            programme_id=programme_id,
            week_start=week_start,
            week_end=week_end,
        )
        # rows: (module_id, module_name, student_id, student_name, email, week, status)

        if not rows:
            return {
                "courseId": course_id,
                "courseName": None,
                "students": [],
            }

        course_name = rows[0][1]

        # statistics per student's attendance
        stats: Dict[str, Dict[str, Any]] = {}
        for _mid, _mname, sid, sname, email, _week, status in rows:
            if sid not in stats:
                stats[sid] = {
                    "name": sname,
                    "email": email,
                    "present": 0,
                    "absent": 0,
                    "total": 0,
                }
            stats[sid]["total"] += 1
            # status: 0 / 1（0 absent，1 present）
            if status is not None and int(status) == 1:
                stats[sid]["present"] += 1
            else:
                stats[sid]["absent"] += 1

        students: List[Dict[str, Any]] = []
        for sid, info in stats.items():
            total = info["total"]
            present = info["present"]
            absent = info["absent"]
            rate = present / total if total > 0 else 0.0

            if rate < threshold_rate or absent >= min_absences:
                students.append(
                    {
                        "studentId": sid,
                        "name": info["name"],
                        "email": info["email"],
                        "attendanceRate": round(rate, 2),
                        "absentSessions": int(absent),
                    }
                )

        return {
            "courseId": course_id,
            "courseName": course_name,
            "students": students,
        }


attendance_service = AttendanceService()
