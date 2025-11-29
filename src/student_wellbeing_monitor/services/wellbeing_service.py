from typing import Optional, Dict, Any, List, Tuple
from collections import defaultdict
import sys
import os
from student_wellbeing_monitor.database.read import (
    get_all_students,
    get_students_by_programme,
    get_student_by_id,
    get_wellbeing_records,
)


# =========================================================
# WellbeingService 类
# =========================================================


class WellbeingService:
    """
    学生健康服务类，提供仪表盘、趋势分析、出勤率和风险学生等功能
    """

    def __init__(self):
        """初始化 WellbeingService 实例"""
        pass

    # =========================================================
    # private tool function
    # =========================================================

    def _get_student_count(self, programme_id: Optional[str]) -> int:
        """
        统计在当前筛选范围内的学生总数：
        - programme_id = None  → 所有学生
        - programme_id = 某专业 → 该专业的所有的学生
        """
        if programme_id is None:
            rows = get_all_students()
            return len(rows)
        else:
            rows = get_students_by_programme(programme_id)
            return len(rows)

    # =========================================================
    # dashboard
    #  get card: summary data
    # =========================================================

    def get_dashboard_summary(
        self,
        start_week: int,
        end_week: int,
        programme_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        对应前端接口 GET /getDashboardSummary

        输入:
            - start_week: 起始周 (含)
            - end_week:   结束周 (含)
            - programme_id: 专业 ID None 表示全部课程

        输出结构：
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

        # 1) 查询 wellbeing 原始数据
        rows = get_wellbeing_records(start_week, end_week, programme_id)
        # rows: (student_id, week, stress_level, hours_slept,programme_id)

        total_stress = 0.0
        total_sleep = 0.0
        n_stress = 0
        n_sleep = 0
        responded_students = set()

        for student_id, week, stress_level, hours_slept, programme_id in rows:
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

        # 2) 计算问卷参与人数 & 响应率
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
                "responseRate": round(response_rate, 2),
            },
        }

    # =========================================================
    # getStressSleepTrend
    # 获取每周的平均压力与平均睡眠
    # =========================================================

    def get_stress_sleep_trend(
        self,
        start_week: int,
        end_week: int,
        programme_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        对应前端接口 GET /getStressSleepTrend

        输出结构：
            {
              "items": [
                {"week": 1, "avgStress": 3.1, "avgSleep": 7.2},
                {"week": 2, "avgStress": 3.3, "avgSleep": 7.0},
                ...
              ]
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

        items: List[Dict[str, Any]] = []
        all_weeks = sorted(set(list(stress_sum.keys()) + list(sleep_sum.keys())))

        for w in all_weeks:
            avg_stress = (
                round(stress_sum[w] / stress_cnt[w], 2) if stress_cnt[w] > 0 else 0.0
            )
            avg_sleep = (
                round(sleep_sum[w] / sleep_cnt[w], 2) if sleep_cnt[w] > 0 else 0.0
            )
            items.append(
                {
                    "week": w,
                    "avgStress": avg_stress,
                    "avgSleep": avg_sleep,
                }
            )

        return {"items": items}

    # =========================================================
    # getRiskStudents: 报告的高风险学生列表
    # =========================================================

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
        对应前端接口：GET /getRiskStudents

        风险规则：
          - high_risk:
              存在连续 3 周，同时满足 stress >= threshold 且 sleep < sleep_threshold
          - potential_risk:
              有任意一周，同时满足 stress >= threshold 且 sleep < sleep_threshold
          - normal (仅当指定 student_id 且不满足风险条件时):
              不满足任何风险条件

        输入参数：
          - student_id: 可选的学生ID，如果指定则只返回该学生的信息

        输出结构：
            正常情况：
            {
              "items": [
                {
                  "studentId": "5000001",
                  "name": "学生姓名",
                  "riskType": "high_risk" 或 "potential_risk" 或 "normal",
                  "reason": "...",
                  "details": "...",
                  "modules": ["WM9QF"]
                },
                ...
              ]
            }

            当指定 student_id 但找不到学生时：
            {
              "items": [],
              "status": "not_found" 或 "no_data",
              "message": "错误信息描述"
            }
            - status="not_found": 学生不存在
            - status="no_data": 学生存在但没有wellbeing数据
        """
        if end_week < start_week:
            raise ValueError("end_week must be >= start_week")

        rows = get_wellbeing_records(start_week, end_week, programme_id)
        # rows: (student_id, week, stress_level, hours_slept,programme_id)

        # 1) 获取学生姓名映射
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

        # 如果指定了 student_id，确保该学生的姓名在映射中（即使不在当前 module_code 范围内）
        if student_id is not None:
            student_id_str = str(student_id)
            if student_id_str not in student_name_map:
                # 从所有学生中查找该学生
                all_student_rows = get_all_students()
                for sid, name, email, pid in all_student_rows:
                    if sid is not None and str(sid) == student_id_str:
                        student_name_map[student_id_str] = name
                        break

        # 2) 按学生分组
        per_student: Dict[str, List[Tuple[int, float, float, str]]] = defaultdict(list)
        for row_student_id, week, stress, sleep, programme_id in rows:
            if row_student_id is None or week is None or stress is None:
                continue
            # 如果指定了 student_id，只处理该学生的数据
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

        # 如果指定了 student_id，只处理该学生
        if student_id is not None:
            student_id_str = str(student_id)
            if student_id_str not in per_student:
                # 检查学生是否在数据库中存在
                if student_id_str in student_name_map:
                    # 学生存在但没有wellbeing数据
                    return {
                        "items": [],
                        "status": "no_data",
                        "message": f"Student {student_id_str} exists but has no wellbeing data for the specified period",
                    }
                else:
                    # 学生不存在
                    return {
                        "items": [],
                        "status": "not_found",
                        "message": f"Student {student_id_str} not found",
                    }
            # 只处理指定的学生
            students_to_process = [(student_id_str, per_student[student_id_str])]
        else:
            # 处理所有学生
            students_to_process = list(per_student.items())

        items: List[Dict[str, Any]] = []

        for sid, recs in students_to_process:
            # recs = [(week, stress, sleep, course_id), ...]
            recs.sort(key=lambda x: x[0])
            weeks = [r[0] for r in recs]
            stresses = [r[1] for r in recs]
            sleeps = [r[2] for r in recs]
            courses = list({r[3] for r in recs if r[3]})

            # ---------- High Risk：连续 3 周，同时满足 stress >= threshold 且 sleep < sleep_threshold ----------
            high_risk = False
            high_weeks: List[int] = []
            streak = 0
            streak_weeks: List[int] = []

            for w, s, sl in zip(weeks, stresses, sleeps):
                # 同时满足：压力 >= threshold 且 睡眠 < sleep_threshold
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

            # ---------- Potential Risk：至少一周，同时满足 stress >= threshold 且 sleep < sleep_threshold ----------
            potential = False
            potential_week_idx = None
            for i, (s, sl) in enumerate(zip(stresses, sleeps)):
                if s >= threshold and sl is not None and sl < sleep_threshold:
                    potential = True
                    potential_week_idx = i
                    break

            # 如果指定了 student_id，即使不满足风险条件也要返回该学生的信息
            if not (high_risk or potential):
                if student_id is not None:
                    # 返回正常状态
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
                            "riskType": risk_type,
                            "reason": reason,
                            "details": details,
                            "modules": courses if courses else [],
                        }
                    )
                continue  # 不属于任何风险，且未指定 student_id，直接跳过

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
                    "riskType": risk_type,
                    "reason": reason,
                    "details": details,
                    "modules": courses if courses else [],
                }
            )

        return {"items": items}


wellbeing_service = WellbeingService()
