# course_service.py

from typing import Optional, Dict, Any, List, Tuple
from collections import defaultdict
import os
import json
from student_wellbeing_monitor.database.read import (
    submissions_for_course,
    unsubmissions_for_repeated_issues,
    attendance_and_grades,
    programme_wellbeing_engagement,
    get_attendance_filtered,
    get_submissions_filtered,
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

    def get_course_leader_summary(
        self,
        programme_id: Optional[str],
        module_id: Optional[str],
        week_start: int,
        week_end: int,
    ):
        """
         返回课程负责人 Dashboard 的三项核心指标：
         - avg_attendance_rate
         - avg_submission_rate
        - avg_grade
        """

        # -------------------------------
        # 1) Attendance
        # -------------------------------
        attendance_rows = get_attendance_filtered(
            programme_id=programme_id,
            module_id=module_id,
            week_start=week_start,
            week_end=week_end,
        )
        # rows: (student_id, module_code, week, status)
        present = sum(1 for r in attendance_rows if r["status"] == 1)
        absent = sum(1 for r in attendance_rows if r["status"] == 0)
        total_att_records = present + absent

        avg_attendance_rate = (
            present / total_att_records if total_att_records > 0 else None
        )

        # -------------------------------
        # 2) Submissions
        # -------------------------------
        submission_rows = get_submissions_filtered(
            programme_id=programme_id,
            module_id=module_id,
        )
        # rows: (student_id, module_code, submitted, grade)

        submit_count = sum(1 for r in submission_rows if r["submitted"] == 1)
        total_sub_records = len(submission_rows)

        avg_submission_rate = (
            submit_count / total_sub_records if total_sub_records > 0 else None
        )

        # -------------------------------
        # 3) Grade
        # -------------------------------
        grades = [r["grade"] for r in submission_rows if r["grade"] is not None]
        avg_grade = sum(grades) / len(grades) if grades else None

        return {
            "avg_attendance_rate": avg_attendance_rate,
            "avg_submission_rate": avg_submission_rate,
            "avg_grade": avg_grade,
        }

    # -------------------------------------------------
    # 2️⃣ 课程作业提交情况统计（已交 / 未交）
    # -------------------------------------------------
    def get_submission_summary(
        self,
        programme_id: str,
        course_id: Optional[str] = None,
        assignment_no: Optional[int] = None,
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
        course_id: Optional[str] = None,
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
        print("DEBUG rows len =", len(rows))
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
            avg_grade = info["grade_sum"] / grade_cnt if grade_cnt > 0 else None

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
        programme_id: Optional[str] = None,
        week_start: Optional[int] = None,
        week_end: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        按“专业 (programme)”维度，对 wellbeing + engagement 做汇总。

        - programme_id 为 None：返回所有专业的汇总列表（适合做对比图表）
        - programme_id 有值：只返回该专业的汇总（列表里通常只有 1 条）

        返回示例：
        {
          "programmeId": "12345" 或 None,
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
            programme_id=programme_id,
            week_start=week_start,
            week_end=week_end,
        )
        # rows: (module_id, module_name,
        #        student_id,
        #        programme_id, programme_name,
        #        week,
        #        stress_level,
        #        hours_slept,
        #        attendance_status,
        #        submission_status,
        #        grade)

        if not rows:
            return {
                "programmeId": programme_id,
                "programmes": [],
            }

        agg: Dict[str, Dict[str, Any]] = {}

        for (
            _mid,
            _mname,
            student_id,
            prog_id_row,
            prog_name,
            _week,
            stress_level,
            _hours_slept,
            attendance_status,
            submission_status,
            grade,
        ) in rows:
            if prog_id_row not in agg:
                agg[prog_id_row] = {
                    "programmeId": prog_id_row,
                    "programmeName": prog_name,
                    "students": set(),  # unique students count
                    "stress_sum": 0.0,
                    "stress_cnt": 0,
                    "att_present": 0,
                    "att_total": 0,
                    "sub_submit": 0,
                    "sub_total": 0,
                    "grade_sum": 0.0,
                    "grade_cnt": 0,
                }

            info = agg[prog_id_row]
            info["students"].add(student_id)

            if stress_level is not None:
                info["stress_sum"] += float(stress_level)
                info["stress_cnt"] += 1

            if attendance_status is not None:
                info["att_total"] += 1
                # 0 = absent, 1 = present
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
                info["grade_sum"] / info["grade_cnt"] if info["grade_cnt"] > 0 else None
            )

            programmes.append(
                {
                    "programmeId": info["programmeId"],
                    "programmeName": info["programmeName"],
                    "studentCount": len(info["students"]),
                    "avgStress": (
                        round(stress_avg, 2) if stress_avg is not None else None
                    ),
                    "attendanceRate": (
                        round(att_rate, 2) if att_rate is not None else None
                    ),
                    "submissionRate": (
                        round(sub_rate, 2) if sub_rate is not None else None
                    ),
                    "avgGrade": round(avg_grade, 2) if avg_grade is not None else None,
                }
            )

        return {
            "programmeId": programme_id,
            "programmes": programmes,
        }

    # -------------------------------------------------
    # 7️⃣ 高压少睡学生 vs 其他学生：出勤 / 提交 / 成绩对比
    # -------------------------------------------------
    def get_high_stress_sleep_engagement_analysis(
        self,
        course_id: str,
        week_start: Optional[int] = None,
        week_end: Optional[int] = None,
        stress_threshold: float = 4.0,
        sleep_threshold: float = 6.0,
        min_weeks: int = 1,
    ) -> Dict[str, Any]:
        """
        针对单门课程，在指定周范围内：
        - 找出“stress 高 AND sleep 少”的学生（满足条件的周数 >= min_weeks）
        - 对比这类学生和其他学生在：
            * 出勤率（缺课更多？）
            * 作业提交率（提交率更低？）
            * 平均成绩（成绩更差？）
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
        #        hours_slept,
        #        attendance_status,
        #        submission_status,
        #        grade)

        if not rows:
            return {
                "courseId": course_id,
                "courseName": None,
                "params": {
                    "weekStart": week_start,
                    "weekEnd": week_end,
                    "stressThreshold": stress_threshold,
                    "sleepThreshold": sleep_threshold,
                    "minWeeks": min_weeks,
                },
                "groups": {
                    "highStressLowSleep": {
                        "studentCount": 0,
                        "avgAttendanceRate": None,
                        "avgSubmissionRate": None,
                        "avgGrade": None,
                    },
                    "others": {
                        "studentCount": 0,
                        "avgAttendanceRate": None,
                        "avgSubmissionRate": None,
                        "avgGrade": None,
                    },
                },
                "students": {"highStressLowSleep": [], "others": []},
            }

        course_name = rows[0][1]

        # 1) 按学生聚合
        per_student: Dict[str, Dict[str, Any]] = {}

        for (
            _mid,
            _mname,
            student_id,
            _programme_id,
            _programme_name,
            week,
            stress_level,
            hours_slept,
            attendance_status,
            submission_status,
            grade,
        ) in rows:
            sid = str(student_id)
            if sid not in per_student:
                per_student[sid] = {
                    "weeks": [],
                    "stresses": [],
                    "sleeps": [],
                    "att_present": 0,
                    "att_total": 0,
                    "sub_submit": 0,
                    "sub_total": 0,
                    "grade_sum": 0.0,
                    "grade_cnt": 0,
                }
            info = per_student[sid]

            # wellbeing
            if week is not None and stress_level is not None:
                try:
                    info["weeks"].append(int(week))
                    info["stresses"].append(float(stress_level))
                    if hours_slept is not None:
                        info["sleeps"].append(float(hours_slept))
                    else:
                        info["sleeps"].append(None)
                except (TypeError, ValueError):
                    # 跳过异常数据
                    pass

            # attendance
            if attendance_status is not None:
                info["att_total"] += 1
                try:
                    if int(attendance_status) == 1:
                        info["att_present"] += 1
                except (TypeError, ValueError):
                    pass

            # submission
            if submission_status in ("submit", "unsubmit"):
                info["sub_total"] += 1
                if submission_status == "submit":
                    info["sub_submit"] += 1

            # grade
            if grade is not None:
                try:
                    info["grade_sum"] += float(grade)
                    info["grade_cnt"] += 1
                except (TypeError, ValueError):
                    pass

        # 2) 划分高压少睡组 vs 其它学生
        high_group: List[Dict[str, Any]] = []
        other_group: List[Dict[str, Any]] = []

        for sid, info in per_student.items():
            stresses: List[float] = info["stresses"]
            sleeps: List[Optional[float]] = info["sleeps"]

            # 有多少周满足 “stress >= stress_threshold AND sleep < sleep_threshold”
            high_weeks = 0
            for s, sl in zip(stresses, sleeps):
                if s is None or sl is None:
                    continue
                if s >= stress_threshold and sl < sleep_threshold:
                    high_weeks += 1

            is_high = high_weeks >= min_weeks

            # 学生级别指标
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
                info["grade_sum"] / info["grade_cnt"] if info["grade_cnt"] > 0 else None
            )

            record = {
                "studentId": sid,
                "attendanceRate": round(att_rate, 2) if att_rate is not None else None,
                "submissionRate": round(sub_rate, 2) if sub_rate is not None else None,
                "avgGrade": round(avg_grade, 2) if avg_grade is not None else None,
            }

            if is_high:
                high_group.append(record)
            else:
                other_group.append(record)

        # 3) 计算两组平均值
        def _group_stats(group: List[Dict[str, Any]]) -> Dict[str, Any]:
            if not group:
                return {
                    "studentCount": 0,
                    "avgAttendanceRate": None,
                    "avgSubmissionRate": None,
                    "avgGrade": None,
                }

            def _avg(values: List[Optional[float]]) -> Optional[float]:
                valid = [v for v in values if v is not None]
                if not valid:
                    return None
                return round(sum(valid) / len(valid), 2)

            return {
                "studentCount": len(group),
                "avgAttendanceRate": _avg([g.get("attendanceRate") for g in group]),
                "avgSubmissionRate": _avg([g.get("submissionRate") for g in group]),
                "avgGrade": _avg([g.get("avgGrade") for g in group]),
            }

        params = {
            "weekStart": week_start,
            "weekEnd": week_end,
            "stressThreshold": stress_threshold,
            "sleepThreshold": sleep_threshold,
            "minWeeks": min_weeks,
        }

        return {
            "courseId": course_id,
            "courseName": course_name,
            "params": params,
            "groups": {
                "highStressLowSleep": _group_stats(high_group),
                "others": _group_stats(other_group),
            },
            "students": {
                "highStressLowSleep": high_group,
                "others": other_group,
            },
        }

    # -------------------------------------------------
    # 8️⃣ 调用外部 AI API，对上述结果做进一步分析
    # -------------------------------------------------
    def analyze_high_stress_sleep_with_ai(
        self,
        course_id: str,
        week_start: Optional[int] = None,
        week_end: Optional[int] = None,
        stress_threshold: float = 4.0,
        sleep_threshold: float = 6.0,
        min_weeks: int = 1,
    ) -> Dict[str, Any]:
        """
        在 get_high_stress_sleep_engagement_analysis 的基础上，
        调用一个外部 AI HTTP 接口，让 AI 生成自然语言分析。

        需要在环境变量中配置：
          - AI_ANALYSIS_URL: 外部 AI 服务的 URL
          - AI_API_KEY:     可选的 Bearer Token
        """
        base_result = self.get_high_stress_sleep_engagement_analysis(
            course_id=course_id,
            week_start=week_start,
            week_end=week_end,
            stress_threshold=stress_threshold,
            sleep_threshold=sleep_threshold,
            min_weeks=min_weeks,
        )

        # Call external AI API to generate natural language analysis
        ai_url = os.environ.get("AI_ANALYSIS_URL")
        if not ai_url:
            return {
                "baseStats": base_result,
                "aiAnalysis": {
                    "status": "error",
                    "message": "AI_ANALYSIS_URL is not configured in environment variables.",
                },
            }

        api_key = os.environ.get("AI_API_KEY", "")

        payload = {
            "task": "analyze_high_stress_low_sleep_vs_engagement",
            "prompt": (
                "You are a data analysis assistant in a university supporting Wellbeing Officer and Course Director."
                "This system will provide the statistical data of two groups of students: one group is the students with high stress and low sleep (highStressLowSleep), "
                "the other group is the other students (others). Each group contains: average attendance rate, submission rate, average grade, and some student samples."
                "Please: "
                "1. Determine if the students with high stress and low sleep are significantly different in attendance rate, submission rate, and average grade from the other students."
                "2. Use concise natural language to summarize the key differences between the two groups (quantify as much as possible, e.g., how many percentage points different)."
                "3. Provide 3–5 actionable recommendations for the school/teacher/Wellbeing team."
                "4. Answer in concise English."
            ),
            "data": {
                "params": base_result.get("params", {}),
                "groups": base_result.get("groups", {}),
                "sampleStudents": {
                    "highStressLowSleep": base_result.get("students", {}).get(
                        "highStressLowSleep", []
                    ),
                    "others": base_result.get("students", {}).get("others", []),
                },
            },
        }

        headers = {
            "Content-Type": "application/json",
        }
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        try:
            resp = requests.post(
                ai_url,
                headers=headers,
                data=json.dumps(payload),
                timeout=30,
            )
            resp.raise_for_status()
            ai_output = resp.json()
        except Exception as e:  # 容错，避免前端因为 AI 失败而崩溃
            return {
                "baseStats": base_result,
                "aiAnalysis": {
                    "status": "error",
                    "message": f"AI request failed: {e}",
                },
            }

        return {
            "baseStats": base_result,
            "aiAnalysis": ai_output,
        }


def get_course_leader_summary(
    self,
    programme_id: Optional[str],
    module_code: Optional[str],
    week_start: int,
    week_end: int,
):
    """
    返回课程负责人 Dashboard 的三项核心指标：
    - avg_attendance_rate
    - avg_submission_rate
    - avg_grade
    """

    # -------------------------------
    # 1) Attendance
    # -------------------------------
    attendance_rows = get_attendance_filtered(
        programme_id=programme_id,
        module_code=module_code,
        week_start=week_start,
        week_end=week_end,
    )
    # rows: (student_id, module_code, week, status)

    present = sum(1 for r in attendance_rows if r["status"] == "present")
    absent = sum(1 for r in attendance_rows if r["status"] == "absent")
    total_att_records = present + absent

    avg_attendance_rate = present / total_att_records if total_att_records > 0 else None

    # -------------------------------
    # 2) Submissions
    # -------------------------------
    submission_rows = get_submissions_filtered(
        programme_id=programme_id,
        module_code=module_code,
    )
    # rows: (student_id, module_code, submitted, grade)

    submit_count = sum(1 for r in submission_rows if r["submitted"] == 1)
    total_sub_records = len(submission_rows)

    avg_submission_rate = (
        submit_count / total_sub_records if total_sub_records > 0 else None
    )

    # -------------------------------
    # 3) Grade
    # -------------------------------
    grades = [r["grade"] for r in submission_rows if r["grade"] is not None]
    avg_grade = sum(grades) / len(grades) if grades else None

    return {
        "avg_attendance_rate": avg_attendance_rate,
        "avg_submission_rate": avg_submission_rate,
        "avg_grade": avg_grade,
    }


course_service = CourseService()
