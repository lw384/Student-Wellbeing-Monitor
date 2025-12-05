from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

from student_wellbeing_monitor.database.read import (
    get_all_students,
    get_students_by_programme,
    get_wellbeing_records,
)
# =========================================================
# Class: WellbeingService
# =========================================================
class WellbeingService:
    """
    Service layer for student wellbeing data processing and analysis

    contain the method in APIdocuemnt.md:
    9️⃣ get_dashboard_summary
    🔟 get_stress_sleep_trend
    1️⃣1️⃣ get_risk_students
    
    """
    def __init__(self):
        pass

    # --------------------------------------------------------
    # count student
    # --------------------------------------------------------
    def _get_student_count(self, programme_id: Optional[str]) -> int:
        """
        statistics student count
        - programme_id = None  → all students
        - programme_id = not None → students in the specified programme
        """
        if programme_id is None:
            rows = get_all_students()
            return len(rows)
        else:
            rows = get_students_by_programme(programme_id)
            return len(rows)

    # -------------------------------------------------
    # 9️⃣ get_dashboard_summary
    # -------------------------------------------------
    def get_dashboard_summary(
        self,
        start_week: int,
        end_week: int,
        programme_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Corresponding frontend interface: GET /getDashboardSummary

        input:
            - start_week:
            - end_week:
            - programme_id: if None, means all programmes

        output structure:
            {
              "avgHoursSlept": 7.1,
              "avgStressLevel": 3.2,
              "surveyResponses": {
                "studentCount": 38,
                "responseRate": 0.76
              }
            }
        """
        if end_week < start_week:
            raise ValueError("end_week must be >= start_week")

        # 1) search wellbeing origin data
        rows = get_wellbeing_records(start_week, end_week, programme_id)
        # rows: (student_id, week, stress_level, hours_slept,programme_id)

        total_stress = 0.0
        total_sleep = 0.0
        n_stress = 0
        n_sleep = 0
        responded_students = set()

        for student_id, week, stress_level, hours_slept, programme_id_record in rows:
            if stress_level is not None:
                try:
                    total_stress += float(stress_level)
                    n_stress += 1
                except (TypeError, ValueError):
                    pass

            if hours_slept is not None:
                try:
                    total_sleep += float(hours_slept)
                    n_sleep += 1
                except (TypeError, ValueError):
                    pass

            responded_students.add(student_id)

        avg_stress = round(total_stress / n_stress, 2) if n_stress > 0 else 0.0
        avg_sleep = round(total_sleep / n_sleep, 2) if n_sleep > 0 else 0.0

        # 2) Count the responser & Response rate
        total_students = self._get_student_count(programme_id)
        responded_count = len(responded_students)
        response_rate = (
            (responded_count / total_students) if total_students > 0 else 0.0
        )
        return {
            "avgHoursSlept": avg_sleep,
            "avgStressLevel": avg_stress,
            "surveyResponses": {
                "studentCount": responded_count,
                "responseRate": round(response_rate, 2) * 100,
            },
        }

    # -------------------------------------------------
    # 🔟 get_stress_sleep_trend
    # -------------------------------------------------
    def get_stress_sleep_trend(
        self,
        start_week: int,
        end_week: int,
        programme_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Corresponding frontend interface: GET /getStressSleepTrend

        ouput structure:
            {
              "weeks": [1, 2, 3, ...],      # X axis: week
              "stress": [3.1, 3.3, ...],     #  Y axis: average stress level
              "sleep": [7.2, 7.0, ...]      #  Y axis: average sleep hours
            }
        """
        if end_week < start_week:
            raise ValueError("end_week must be >= start_week")

        rows = get_wellbeing_records(start_week, end_week, programme_id)
        # rows: (programme_id, student_id, week, stress, sleep)

        stress_sum = defaultdict(float)
        stress_cnt = defaultdict(int)
        sleep_sum = defaultdict(float)
        sleep_cnt = defaultdict(int)

        for student_id, week, stress_level, hours_slept, programme_id in rows:
            if week is None:
                continue
            w = int(week)

            if stress_level is not None:
                try:
                    stress_sum[w] += float(stress_level)
                    stress_cnt[w] += 1
                except (TypeError, ValueError):
                    pass

            if hours_slept is not None:
                try:
                    sleep_sum[w] += float(hours_slept)
                    sleep_cnt[w] += 1
                except (TypeError, ValueError):
                    pass

        all_weeks = sorted(set(list(stress_sum.keys()) + list(sleep_sum.keys())))

        weeks: List[int] = []
        stress: List[float] = []
        sleep: List[float] = []

        for w in all_weeks:
            avg_stress = (
                round(stress_sum[w] / stress_cnt[w], 2) if stress_cnt[w] > 0 else 0.0
            )
            avg_sleep = (
                round(sleep_sum[w] / sleep_cnt[w], 2) if sleep_cnt[w] > 0 else 0.0
            )
            weeks.append(w)
            stress.append(avg_stress)
            sleep.append(avg_sleep)

        return {"weeks": weeks, "stress": stress, "sleep": sleep}

    # -------------------------------------------------
    # 1️⃣1️⃣ get_risk_students
    # -------------------------------------------------=
    def get_risk_students(
        self,
        start_week: int,
        end_week: int,
        programme_id: Optional[str] = None,
        threshold: float = 4.5,
        sleep_threshold: float = 6.0,
        student_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Corresponding frontend interface: GET /getRiskStudents

        rules of risk:
          - high_risk:
              3 consecutive weeks, simultaneously satisfy stress >= threshold and sleep < sleep_threshold
          - potential_risk:
              1 week, simultaneously satisfy stress >= threshold and sleep < sleep_threshold suddenly
          - normal:
              no risk detected

        input:
          - student_id: if specified, only return the risk status of the given student, or return all risk students

        output structure:
            normal case:
            {
              "items": [
                {
                  "studentId": "5000001",
                  "name": "Alice",
                  "riskType": "high_risk" or "potential_risk" or "normal",
                  "email": "alice@warwick.ac.uk",
                  "reason": "...",
                  "details": "...",
                  "modules": ["WM9QF"]
                },
                ...
              ]
            }

            if student_id is not available:
            {
              "items": [],
              "status": "not_found" or "no_data",
              "message": "wrong message discription"
            }
            - status="not_found": student does not exist
            - status="no_data": student exists but has no data
        """
        if end_week < start_week:
            raise ValueError("end_week must be >= start_week")

        rows = get_wellbeing_records(start_week, end_week, programme_id)
        # rows: (student_id, week, stress_level, hours_slept,programme_id)

        # 1) get student name mapping
        if programme_id is None:
            student_rows = get_all_students()
        else:
            student_rows = get_students_by_programme(programme_id)
            # student_rows: student_id, name, email, programme_id

        student_name_map: Dict[str, str] = {
            str(row[0]): row[1]  # 0 = student_id, 1 = name
            for row in student_rows
            if row[0] is not None
        }
        student_email_map: Dict[str, str] = {
            str(row[0]): row[2]  # 0 = student_id, 1 = name
            for row in student_rows
            if row[0] is not None
        }

        # if specific student_id is given, ensure it exists in the name map
        if student_id is not None:
            student_id_str = str(student_id)
            if student_id_str not in student_name_map:
                # check in all students
                all_student_rows = get_all_students()
                for sid, name, email, pid in all_student_rows:
                    if sid is not None and str(sid) == student_id_str:
                        student_name_map[student_id_str] = name
                        break

        # 2) group wellbeing data by student
        per_student: Dict[str, List[Tuple[int, float, float, str]]] = defaultdict(list)
        for row_student_id, week, stress, sleep, programme_id in rows:
            if row_student_id is None or week is None or stress is None:
                continue
            # if specific student_id is given, only process that student
            if student_id is not None and str(row_student_id) != str(student_id):
                continue
            try:
                w = int(week)
                s = float(stress)
                sl = float(sleep) if sleep is not None else None
            except (TypeError, ValueError):
                continue
            cid = str(programme_id) if programme_id is not None else ""
            per_student[str(row_student_id)].append((w, s, sl, cid))

        # if specific student_id is given, only process that student
        if student_id is not None:
            student_id_str = str(student_id)
            if student_id_str not in per_student:
                # check if the student exists
                if student_id_str in student_name_map:
                    # student exists but has no data
                    return {
                        "items": [],
                        "status": "no_data",
                        "message": f"Student {student_id_str} exists but has no wellbeing data for the specified period",
                    }
                else:
                    # student does not exist
                    return {
                        "items": [],
                        "status": "not_found",
                        "message": f"Student {student_id_str} not found",
                    }
            # only process the specified student
            students_to_process = [(student_id_str, per_student[student_id_str])]
        else:
            # process all students
            students_to_process = list(per_student.items())

        items: List[Dict[str, Any]] = []

        for sid, recs in students_to_process:
            # recs = [(week, stress, sleep, course_id), ...]
            recs.sort(key=lambda x: x[0])
            weeks = [r[0] for r in recs]
            stresses = [r[1] for r in recs]
            sleeps = [r[2] for r in recs]
            courses = list({r[3] for r in recs if r[3]})

            # ---------- High Risk：3 consecutive weeks simultaneously satisfy stress >= threshold and sleep < sleep_threshold ----------
            high_risk = False
            high_weeks: List[int] = []
            streak = 0
            streak_weeks: List[int] = []

            for w, s, sl in zip(weeks, stresses, sleeps):
                # both conditions met
                if s >= threshold and sl is not None and sl < sleep_threshold:
                    streak += 1
                    streak_weeks.append(w)
                    if streak >= 3:
                        high_risk = True
                        high_weeks = streak_weeks[-3:]
                        break
                else:
                    streak = 0
                    streak_weeks = []

            # ---------- Potential Risk：1 week simultaneously satisfy stress >= threshold and sleep < sleep_threshold suddenly ----------
            potential = False
            potential = False
            potential_week_idx = None
            for i, (s, sl) in enumerate(zip(stresses, sleeps)):
                if s >= threshold and sl is not None and sl < sleep_threshold:
                    potential = True
                    potential_week_idx = i
                    break

            # if user specified student_id, through student not belong to any risk, still need to return normal status
            if not (high_risk or potential):
                if student_id is not None:
                    risk_type = "normal"
                    avg_stress = sum(stresses) / len(stresses) if stresses else 0.0
                    valid_sleeps = [sl for sl in sleeps if sl is not None]
                    avg_sleep = (
                        sum(valid_sleeps) / len(valid_sleeps) if valid_sleeps else None
                    )
                    reason = "No risk detected"
                    if avg_sleep is not None:
                        details = f"Average stress: {avg_stress:.1f}, average sleep: {avg_sleep:.1f}h"
                    else:
                        details = f"Average stress: {avg_stress:.1f}, no sleep data"
                    items.append(
                        {
                            "studentId": sid,
                            "name": student_name_map.get(sid),
                            "email": student_email_map.get(sid),
                            "riskType": risk_type,
                            "reason": reason,
                            "details": details,
                            "modules": courses if courses else [],
                        }
                    )
                continue  # skip non-risk students if no specific student_id

            if high_risk:
                risk_type = "high_risk"
                reason = f"Stress ≥ {threshold:.1f} and sleep < {sleep_threshold:.1f}h for 3 consecutive weeks"
                details = f"Weeks {high_weeks[0]}–{high_weeks[-1]}: stress ≥ {threshold:.1f} and sleep < {sleep_threshold:.1f}h"
            else:
                risk_type = "potential_risk"
                reason = f"Stress ≥ {threshold:.1f} and sleep < {sleep_threshold:.1f}h"
                details = f"Week {weeks[potential_week_idx]}: stress = {stresses[potential_week_idx]:.1f}, sleep = {sleeps[potential_week_idx]:.1f}h"

            items.append(
                {
                    "studentId": sid,
                    "name": student_name_map.get(sid),
                    "email": student_email_map.get(sid),
                    "riskType": risk_type,
                    "reason": reason,
                    "details": details,
                    "modules": courses if courses else [],
                }
            )

        return {"items": items}


wellbeing_service = WellbeingService()