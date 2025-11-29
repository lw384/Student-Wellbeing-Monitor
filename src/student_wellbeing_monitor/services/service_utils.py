from typing import List, Optional
import numpy as np
from typing import List, Optional, Any, Dict


# 1. mean
def mean_value(data: List[float]) -> float:
    return float(np.mean(data))


# 2. submission rate
def completion_rate(total_list: List[Any], mark_submitted: Any = 1) -> float:
    if not total_list:
        return 0.0
    submitted = sum(1 for i in total_list if i == mark_submitted)
    total = len(total_list)
    return round(submitted / total, 4)


# 3. the number of x greater than y
def count_above_threshold(data: List[float], x: float) -> int:
    return sum(1 for i in data if i > x)


# 4. the number of x lower than y
def count_below_threshold(data: List[float], x: float) -> int:
    return sum(1 for i in data if i < x)


# 5. count(x)
def count_occurrences(data: List, value) -> int:
    return data.count(value)


# 6. sum
def sum_value(data: List[float]) -> float:
    return sum(data) if data else 0.0


# 7.group_stress_by_student
def group_stress_by_student(records: List[Dict[str, Any]]) -> Dict[str, List[float]]:
    result = {}
    for r in records:
        sid = r.get("student_id")
        stress = r.get("stress")
        if sid is None:
            continue
        if sid not in result:
            result[sid] = []
        if stress is not None:
            result[sid].append(stress)
    return result
