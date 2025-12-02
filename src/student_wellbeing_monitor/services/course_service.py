# course_service.py

from typing import Optional, Dict, Any, List, Tuple
from collections import defaultdict

from student_wellbeing_monitor.database.read import (
    submissions_for_course,
    unsubmissions_for_repeated_issues,
    attendance_and_grades,
    programme_wellbeing_engagement,
)


class CourseService:
    """
    Course Leader 视角的课程综合分析服务。

    对应 CourseLeader.md 中的：
      2️⃣ get_submission_summary        （作业提交情况统计：已交 / 未交）
      4️⃣ get_repeated_missing_students （多门课作业问题学生：多门课未交）
      5️⃣ get_attendance_vs_grades      （出勤率 vs 成绩）
      6️⃣ get_programme_wellbeing_engagement （按专业的 wellbeing + engagement 汇总）
    """

    # -------------------------------------------------
    # 2️⃣ 课程作业提交情况统计（已交 / 未交）
    # -------------------------------------------------
    def get_submission_summary(
        self,
        course_id: str,
        assignment_no: Optional[int] = None,
        programme_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        返回某课程在指定作业上的“已交 / 未交”统计。

        返回：
        {
          "courseId": "WM9AA0",
          "courseName": "Applied AI",
          "assignmentNo": 1,
          "totalStudents": 40,
          "submit": 32,
          "unsubmit": 8
        }
        """
        rows = submissions_for_course(
            module_id=course_id,
            assignment_no=assignment_no,
            programme_id=programme_id,
        )
        # rows: (module_id, module_name, student_id, submitted)

        if not rows:
            return {
                "courseId": course_id,
                "courseName": None,
                "assignmentNo": assignment_no,
                "totalStudents": 0,
                "submit": 0,
                "unsubmit": 0,
            }

        course_name = rows[0][1]

        total_students = 0
        submit_count = 0
        unsubmit_count = 0

        for _mid, _mname, _sid, submitted in rows:
            total_students += 1
            if submitted:
                submit_count += 1
            else:
                unsubmit_count += 1

        return {
            "courseId": course_id,
            "courseName": course_name,
            "assignmentNo": assignment_no,
            "totalStudents": total_students,
            "submit": submit_count,
            "unsubmit": unsubmit_count,
        }

    # -------------------------------------------------
    # 4️⃣ 多门课作业问题学生（多门课未交）
    # -------------------------------------------------
    def get_repeated_missing_students(
        self,
        course_id: Optional[str] = None,
        programme_id: Optional[str] = None,
        start_week: Optional[int] = None,
        end_week: Optional[int] = None,
        min_offending_modules: int = 2,
    ) -> Dict[str, Any]:
        """
        找出在多门课里“作业有问题”的学生。
        在当前约束下：只有“未交(unsubmit)”这一种问题（没有迟交的概念）。

        返回：
        {
          "students": [
            {
              "studentId": "S0001",
              "name": "Alice",
              "email": "alice@example.com",
              "offendingModuleCount": 2,
              "details": [
                {
                  "courseId": "WM9AA0",
                  "courseName": "Applied AI",
                  "assignmentNo": 1,
                  "status": "unsubmit"
                },
                ...
              ]
            },
            ...
          ]
        }
        """
        rows = unsubmissions_for_repeated_issues(
            module_id=course_id,
            programme_id=programme_id,
            week_start=start_week,
            week_end=end_week,
        )
        # rows: (module_id, module_name, assignment_no, student_id, student_name, email, submitted)

        problem_records: List[Tuple[str, str, int, str, str, str]] = []
        for module_id, module_name, assignment_no, sid, sname, email, submitted in rows:
            # 只关心未交（submitted 为 0 或 False）
            if not submitted:
                problem_records.append(
                    (module_id, module_name, assignment_no, sid, sname, email)
                )

        by_student: Dict[str, Dict[str, Any]] = {}
        for module_id, module_name, assignment_no, sid, sname, email in problem_records:
            if sid not in by_student:
                by_student[sid] = {
                    "studentId": sid,
                    "name": sname,
                    "email": email,
                    "modules": set(),
                    "details": [],
                }
            by_student[sid]["modules"].add(module_id)
            by_student[sid]["details"].append(
                {
                    "courseId": module_id,
                    "courseName": module_name,
                    "assignmentNo": assignment_no,
                    "status": "unsubmit",
                }
            )

        result_students: List[Dict[str, Any]] = []
        for info in by_student.values():
            module_count = len(info["modules"])
            if module_count >= min_offending_modules:
                result_students.append(
                    {
                        "studentId": info["studentId"],
                        "name": info["name"],
                        "email": info["email"],
                        "offendingModuleCount": module_count,
                        "details": info["details"],
                    }
                )

        return {"students": result_students}

    # -------------------------------------------------
    # 5️⃣ 出勤 vs 成绩：简单相关性（散点图数据）
    # -------------------------------------------------
    def get_attendance_vs_grades(
        self,
        course_id: str,
        programme_id: Optional[str] = None,
        week_start: Optional[int] = None,
        week_end: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        返回 UI 画散点图所需的基础数据：每个学生的出勤率和平均成绩。

        返回：
        {
          "courseId": "...",
          "courseName": "...",
          "points": [
            {
              "studentId": "...",
              "name": "...",
              "attendanceRate": 0.85,   # x 轴
              "avgGrade": 68.0          # y 轴
            },
            ...
          ]
        }
        """
        rows = attendance_and_grades(
            module_id=course_id,
            programme_id=programme_id,
            week_start=week_start,
            week_end=week_end,
        )
        # rows: (module_id, module_name, student_id, student_name, week, status, grade)

        if not rows:
            return {
                "courseId": course_id,
                "courseName": None,
                "points": [],
            }

        course_name = rows[0][1]

        tmp: Dict[str, Dict[str, Any]] = {}
        for _mid, _mname, sid, sname, _week, status, grade in rows:
            if sid not in tmp:
                tmp[sid] = {
                    "name": sname,
                    "present": 0,
                    "total": 0,
                    "grade_sum": 0.0,
                    "grade_cnt": 0,
                }
            tmp[sid]["total"] += 1
            # attendance.status 在数据库中为 0 / 1（0 缺勤，1 出勤）
            if status is not None and int(status) == 1:
                tmp[sid]["present"] += 1
            if grade is not None:
                tmp[sid]["grade_sum"] += float(grade)
                tmp[sid]["grade_cnt"] += 1

        points: List[Dict[str, Any]] = []

        for sid, info in tmp.items():
            total = info["total"]
            present = info["present"]
            grade_cnt = info["grade_cnt"]

            att_rate = present / total if total > 0 else 0.0
            avg_grade = (
                info["grade_sum"] / grade_cnt if grade_cnt > 0 else None
            )

            points.append(
                {
                    "studentId": sid,
                    "name": info["name"],
                    "attendanceRate": round(att_rate, 2),
                    "avgGrade": round(avg_grade, 2) if avg_grade is not None else None,
                }
            )

        return {
            "courseId": course_id,
            "courseName": course_name,
            "points": points,
        }

    # -------------------------------------------------
    # 6️⃣ 按专业的 wellbeing + engagement 汇总
    # -------------------------------------------------
    def get_programme_wellbeing_engagement(
        self,
        course_id: str,
        week_start: Optional[int] = None,
        week_end: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        按专业 (programme) 维度，汇总某门课在指定周内的 wellbeing + engagement 指标。

        返回示例：
        {
          "courseId": "...",
          "courseName": "...",
          "programmes": [
            {
              "programmeId": "...",
              "programmeName": "...",
              "studentCount": 20,
              "avgStress": 3.4,
              "attendanceRate": 0.87,
              "submissionRate": 0.9,
              "avgGrade": 65.2
            },
            ...
          ]
        }
        """
        rows = programme_wellbeing_engagement(
            module_id=course_id,
            week_start=week_start,
            week_end=week_end,
        )
        # rows: (module_id, module_name,
        #        student_id,
        #        programme_id, programme_name,
        #        week,
        #        stress_level,
        #        attendance_status,
        #        submission_status,   -- 'submit' / 'unsubmit'
        #        grade)

        if not rows:
            return {
                "courseId": course_id,
                "courseName": None,
                "programmes": [],
            }

        course_name = rows[0][1]

        agg: Dict[str, Dict[str, Any]] = {}

        for (
            _mid,
            _mname,
            student_id,
            programme_id,
            programme_name,
            _week,
            stress_level,
            attendance_status,
            submission_status,
            grade,
        ) in rows:
            if programme_id not in agg:
                agg[programme_id] = {
                    "programmeId": programme_id,
                    "programmeName": programme_name,
                    "students": set(),  # 去重统计学生数
                    "stress_sum": 0.0,
                    "stress_cnt": 0,
                    "att_present": 0,
                    "att_total": 0,
                    "sub_submit": 0,
                    "sub_total": 0,
                    "grade_sum": 0.0,
                    "grade_cnt": 0,
                }

            info = agg[programme_id]
            info["students"].add(student_id)

            if stress_level is not None:
                info["stress_sum"] += float(stress_level)
                info["stress_cnt"] += 1

            if attendance_status is not None:
                info["att_total"] += 1
                # attendance_status 为 0 / 1（0 缺勤，1 出勤）
                if int(attendance_status) == 1:
                    info["att_present"] += 1

            if submission_status in ("submit", "unsubmit"):
                info["sub_total"] += 1
                if submission_status == "submit":
                    info["sub_submit"] += 1

            if grade is not None:
                info["grade_sum"] += float(grade)
                info["grade_cnt"] += 1

        programmes: List[Dict[str, Any]] = []
        for info in agg.values():
            stress_avg = (
                info["stress_sum"] / info["stress_cnt"]
                if info["stress_cnt"] > 0
                else None
            )
            att_rate = (
                info["att_present"] / info["att_total"]
                if info["att_total"] > 0
                else None
            )
            sub_rate = (
                info["sub_submit"] / info["sub_total"]
                if info["sub_total"] > 0
                else None
            )
            avg_grade = (
                info["grade_sum"] / info["grade_cnt"]
                if info["grade_cnt"] > 0
                else None
            )

            programmes.append(
                {
                    "programmeId": info["programmeId"],
                    "programmeName": info["programmeName"],
                    "studentCount": len(info["students"]),
                    "avgStress": round(stress_avg, 2) if stress_avg is not None else None,
                    "attendanceRate": round(att_rate, 2) if att_rate is not None else None,
                    "submissionRate": round(sub_rate, 2) if sub_rate is not None else None,
                    "avgGrade": round(avg_grade, 2) if avg_grade is not None else None,
                }
            )

        return {
            "courseId": course_id,
            "courseName": course_name,
            "programmes": programmes,
        }
