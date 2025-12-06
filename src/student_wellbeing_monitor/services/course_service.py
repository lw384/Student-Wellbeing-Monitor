# course_service.py

import json
import os
from typing import Any, Dict, List, Optional, Tuple

from google import genai

from student_wellbeing_monitor.database.read import (
    attendance_and_grades,
    get_attendance_filtered,
    get_submissions_filtered,
    programme_wellbeing_engagement,
    submissions_for_course,
    unsubmissions_for_repeated_issues,
)


# =========================================================
# Class: CourseService
# =========================================================
class CourseService:
    """
    The course analysis service from the Course Leader's perspective.

    contain the method in API document.md:
      2️⃣ get_submission_summary
      4️⃣ get_repeated_missing_students
      5️⃣ get_attendance_vs_grades
      6️⃣ get_programme_wellbeing_engagement
      7️⃣ get_high_stress_sleep_engagement_analysis
      8️⃣ further analyze with AI (Gemini)
    """

    def get_course_leader_summary(
        self,
        programme_id: Optional[str],
        module_id: Optional[str],
        week_start: int,
        week_end: int,
    ):
        """
         return the three key metrics for Course Leader Dashboard:
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
    # 2️⃣ submission summary: submitted / unsubmitted
    # -------------------------------------------------
    def get_submission_summary(
        self,
        programme_id: str,
        course_id: Optional[str] = None,
        assignment_no: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        return the submission statistic for a specific assignment in a course.

        return:
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
    # 4️⃣ get the students with repeated missing submissions
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
        get the students with repeated missing submissions across multiple courses.

        return:
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
    # 5️⃣ attendance vs grades and scatter plot data
    # -------------------------------------------------
    def get_attendance_vs_grades(
        self,
        course_id: Optional[str] = None,
        programme_id: Optional[str] = None,
        week_start: Optional[int] = None,
        week_end: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        return the data for scatter plot of attendance vs grades.

        return:
        {
          "courseId": "...",
          "courseName": "...",
          "points": [
            {
              "studentId": "...",
              "name": "...",
              "attendanceRate": 0.85,   # x axis
              "avgGrade": 68.0          # y axis
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
            # attendance.status : 0 = absent, 1 = present
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
    # 6️⃣ summary of wellbeing + engagement by programme
    # -------------------------------------------------
    def get_programme_wellbeing_engagement(
        self,
        programme_id: Optional[str] = None,
        week_start: Optional[int] = None,
        week_end: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        summary of wellbeing and engagement by programme.

        - programme_id = None: return all programmes' summary
        - programme_id != None: only return that programme's summary

        return example:
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
    # 7️⃣ the status of students with high stress and low sleep vs others'
    # -------------------------------------------------
    def get_high_stress_sleep_engagement_analysis(
        self,
        programme_id: str,
        week_start: Optional[int] = None,
        week_end: Optional[int] = None,
        stress_threshold: float = 4.0,
        sleep_threshold: float = 6.0,
        min_weeks: int = 1,
    ) -> Dict[str, Any]:
        """
        针对单门课程，在指定周范围内：
        foucs on specific course, within specified weeks:
        get the status of students with high stress and low sleep
        and compare with other students on:
            * attendance rate ( lower? )
            * submission rate ( lower? )
            * average grade ( worse?)
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
                "programme_id": programme_id,
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

        # grouping by student
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
                    # skip invalid data
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

        # divide students into two groups
        high_group: List[Dict[str, Any]] = []
        other_group: List[Dict[str, Any]] = []

        for sid, info in per_student.items():
            stresses: List[float] = info["stresses"]
            sleeps: List[Optional[float]] = info["sleeps"]

            # how many weeks: “stress >= stress_threshold AND sleep < sleep_threshold”
            high_weeks = 0
            for s, sl in zip(stresses, sleeps):
                if s is None or sl is None:
                    continue
                if s >= stress_threshold and sl < sleep_threshold:
                    high_weeks += 1

            is_high = high_weeks >= min_weeks

            # the indicators per student
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

        # 3) calculate the mean of each group
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
            "courseId": programme_id,
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
    # 8️⃣ further analyze with AI (Gemini)
    # -------------------------------------------------
    def analyze_high_stress_sleep_with_ai(
        self,
        programme_id: str,
        week_start: Optional[int] = None,
        week_end: Optional[int] = None,
        stress_threshold: float = 4.0,
        sleep_threshold: float = 6.0,
        min_weeks: int = 1,
    ) -> Dict[str, Any]:
        """
        On basis of get_high_stress_sleep_engagement_analysis,
        use Gemini model to generate natural language analysis.

        Environment Variables:
        - GEMINI_API_KEY: Gemini API key
        """
        # get the base data
        base_result = self.get_high_stress_sleep_engagement_analysis(
            programme_id=programme_id,
            week_start=week_start,
            week_end=week_end,
            stress_threshold=stress_threshold,
            sleep_threshold=sleep_threshold,
            min_weeks=min_weeks,
        )
        # read API key
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            return {
                "baseStats": base_result,
                "aiAnalysis": {
                    "status": "error",
                    "message": "GEMINI_API_KEY is not configured in environment variables.",
                },
            }

        # create Gemini client
        client = genai.Client(api_key=api_key)
        print(api_key)
        # construct the prompt + data
        analysis_data = {
            "params": base_result.get("params", {}),
            "groups": base_result.get("groups", {}),
            "sampleStudents": {
                "highStressLowSleep": base_result.get("students", {}).get(
                    "highStressLowSleep", []
                ),
                "others": base_result.get("students", {}).get("others", []),
            },
        }

        prompt = (
            "You are a data analysis assistant in a university supporting the Wellbeing Officer "
            "and Course Director.\n\n"
            "You are given aggregated statistics for two groups of students:\n"
            "  • highStressLowSleep: students whose stress is high and sleep is low.\n"
            "  • others: all other students.\n\n"
            "For each group you have:\n"
            "  - average attendance rate\n"
            "  - average submission rate\n"
            "  - average grade\n"
            "  - some example students with their individual metrics.\n\n"
            "Please:\n"
            "1) Compare the two groups on attendance rate, submission rate and average grade.\n"
            "   Quantify differences where possible (e.g. ‘attendance is about 12 percentage points lower’).\n"
            "2) Summarise in clear, concise English what this means for student wellbeing and engagement.\n"
            "3) Provide 3–5 actionable recommendations for the school/teachers/Wellbeing team.\n"
            "4) Keep the answer short and structured (no Markdown, use bullet points or numbered list,pure text).\n\n"
            "Here is the JSON data:\n"
            f"{json.dumps(analysis_data, indent=2)}\n"
        )

        try:
            # 5) call Gemini API
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
            )
            ai_text = getattr(response, "text", None) or ""
            return {
                "baseStats": base_result,
                "aiAnalysis": {
                    "status": "ok",
                    "text": ai_text,
                },
            }
        except Exception as e:
            # API call failed
            return {
                "baseStats": base_result,
                "aiAnalysis": {
                    "status": "error",
                    "message": f"Gemini request failed: {e}",
                },
            }

    # def get_course_leader_summary(
    #     self,
    #     programme_id: Optional[str],
    #     module_id: Optional[str],
    #     week_start: int,
    #     week_end: int,
    # ):
    #     """
    #     return the three key metrics for Course Leader Dashboard:
    #     - avg_attendance_rate
    #     - avg_submission_rate
    #     - avg_grade
    #     """

    #     # -------------------------------
    #     # 1) Attendance
    #     # -------------------------------
    #     attendance_rows = get_attendance_filtered(
    #         programme_id=programme_id,
    #         module_code=module_code,
    #         week_start=week_start,
    #         week_end=week_end,
    #     )
    #     # rows: (student_id, module_code, week, status)

    #     present = sum(1 for r in attendance_rows if r["status"] == "present")
    #     absent = sum(1 for r in attendance_rows if r["status"] == "absent")
    #     total_att_records = present + absent

    #     avg_attendance_rate = (
    #         present / total_att_records if total_att_records > 0 else None
    #     )

    #     # -------------------------------
    #     # 2) Submissions
    #     # -------------------------------
    #     submission_rows = get_submissions_filtered(
    #         programme_id=programme_id,
    #         module_code=module_code,
    #     )
    #     # rows: (student_id, module_code, submitted, grade)

    #     submit_count = sum(1 for r in submission_rows if r["submitted"] == 1)
    #     total_sub_records = len(submission_rows)

    #     avg_submission_rate = (
    #         submit_count / total_sub_records if total_sub_records > 0 else None
    #     )

    #     # -------------------------------
    #     # 3) Grade
    #     # -------------------------------
    #     grades = [r["grade"] for r in submission_rows if r["grade"] is not None]
    #     avg_grade = sum(grades) / len(grades) if grades else None

    #     return {
    #         "avg_attendance_rate": avg_attendance_rate,
    #         "avg_submission_rate": avg_submission_rate,
    #         "avg_grade": avg_grade,
    #     }


course_service = CourseService()
