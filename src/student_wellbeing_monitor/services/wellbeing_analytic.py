from typing import List, Dict, Any, Tuple, Optional
from student_wellbeing_monitor.services.service_utils import group_stress_by_student


# flag the high-stress students
def flag_high_stress_students(
    records: List[Dict[str, Any]],
    threshold: float = 4.0,
    max_weeks: int = 3,
    max_level: float = 5.0,
    start_week: Optional[int] = None,
    end_week: Optional[int] = None,
) -> Tuple[List[str], Dict[str, List[Tuple[int, float]]]]:
    if start_week is not None:
        records = [
            r for r in records if r.get("week") is not None and r["week"] >= start_week
        ]
    if end_week is not None:
        records = [
            r for r in records if r.get("week") is not None and r["week"] <= end_week
        ]
    if not records:
        return [], {}
    stress_by_student = group_stress_by_student(records)
    risky_ids = []
    risky_weeks = {}
    for sid, stresses in stress_by_student.items():
        stresses = [float(s) for s in stresses if s not in [None, ""]]
        if not stresses:
            continue
        if stresses[-1] == max_level:
            risky_ids.append(sid)
        else:
            count = 0
            for s in stresses:
                if s >= threshold:  # stress >= 4
                    count += 1
                    if count >= max_weeks:  # ≥ 3周连续高压
                        risky_ids.append(sid)
                        break
                else:
                    count = 0

        if sid in risky_ids:
            risky_weeks[sid] = [
                (i, s) for i, s in enumerate(stresses, start=1) if s >= threshold
            ]
    return risky_ids, risky_weeks


# calculate the average sleep hours by week, find the least sleep hours week
def weekly_sleep_trend(
    records: List[Dict[str, Any]],
    start_week: Optional[int] = None,
    end_week: Optional[int] = None,
) -> Tuple[Dict[int, float], Optional[int]]:
    if start_week is not None:
        records = [
            r for r in records if r.get("week") is not None and r["week"] >= start_week
        ]
    if end_week is not None:
        records = [
            r for r in records if r.get("week") is not None and r["week"] <= end_week
        ]
    if not records:
        return [], {}
    by_week: Dict[int, Dict[str, float]] = {}
    counts: Dict[int, int] = {}
    for r in records:
        week = r.get("week")
        if week is None:
            continue
        sleep_val = r.get("sleep_hours")
        if sleep_val is None:
            continue
        if week not in by_week:
            by_week[week] = {"sleep_sum": 0.0}
            counts[week] = 0
        by_week[week]["sleep_sum"] += float(sleep_val)
        counts[week] += 1
    # average sleep hours
    y_sleep: Dict[int, float] = {}
    for week, sums in by_week.items():
        c = counts[week]
        if c > 0:
            y_sleep[week] = round(sums["sleep_sum"] / c, 2)
        else:
            y_sleep[week] = 0.0
    # find the least sleep hours week
    if y_sleep:
        week_lowest_sleep = min(y_sleep, key=lambda w: y_sleep[w])
    else:
        week_lowest_sleep = None

    return y_sleep, week_lowest_sleep


# calculate the average stress by week, find the highest stress week
def weekly_stress_trend(
    records: List[Dict[str, Any]],
    start_week: Optional[int] = None,
    end_week: Optional[int] = None,
) -> Tuple[Dict[int, float], Optional[int]]:
    if start_week is not None:
        records = [
            r for r in records if r.get("week") is not None and r["week"] >= start_week
        ]
    if end_week is not None:
        records = [
            r for r in records if r.get("week") is not None and r["week"] <= end_week
        ]
    if not records:
        return [], {}
    by_week: Dict[int, Dict[str, float]] = {}
    counts: Dict[int, int] = {}
    for r in records:
        week = r.get("week")
        if week is None:
            continue
        stress_val = r.get("stress")
        if stress_val is None:
            continue
        if week not in by_week:
            by_week[week] = {"stress_sum": 0.0}
            counts[week] = 0
        by_week[week]["stress_sum"] += float(stress_val)
        counts[week] += 1
    # average stress
    y_stress: Dict[int, float] = {}
    for week, sums in by_week.items():
        c = counts[week]
        if c > 0:
            y_stress[week] = round(sums["stress_sum"] / c, 2)
        else:
            y_stress[week] = 0.0
    # find the highest stress week
    if y_stress:
        week_highest_stress = max(y_stress, key=lambda w: y_stress[w])
    else:
        week_highest_stress = None

    return y_stress, week_highest_stress
