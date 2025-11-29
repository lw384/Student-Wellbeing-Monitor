import random


def generate_attendance_by_week(
    student_modules: list[dict],
    modules: list[dict],
    weeks: int = 12,
    min_attendance_rate: float = 0.6,
    max_attendance_rate: float = 0.95,
    exam_weeks: list[int] | None = None,
) -> dict[int, list[dict]]:
    """
    Generate weekly attendance records for each course based on `student_modules`, and return them grouped by week:
    - Each (student_id, module_id) combination has its own `attendance_rate` (attendance probability).
    - This probability is used weekly to determine whether the student is present or absent from the course that week.
    - The attendance rate can be slightly reduced in `exam_weeks` (e.g., [8,9,10]) to simulate exam/busy weeks.
    """
    if exam_weeks is None:
        exam_weeks = [8, 9, 10]

    module_id_to_code: dict[int, str] = {
        m["module_id"]: m["module_code"] for m in modules
    }

    # 按周分组的结果容器
    result: dict[int, list[dict]] = {w: [] for w in range(1, weeks + 1)}

    # 为每个 student-module 对分配一个出勤概率
    attendance_profile: dict[tuple[int, int], float] = {}

    for rel in student_modules:
        key = (rel["student_id"], rel["module_id"])

        if key not in attendance_profile:
            attendance_profile[key] = random.uniform(
                min_attendance_rate, max_attendance_rate
            )

    for (student_id, module_id), base_rate in attendance_profile.items():
        module_code = module_id_to_code.get(module_id, "UNKNOWN")

        for w in range(1, weeks + 1):
            if w in exam_weeks:
                effective_rate = max(0.3, base_rate - 0.1)
            else:
                effective_rate = base_rate

            status = int(random.random() < effective_rate)  # 1 = present, 0 = absent

            row = {
                "student_id": student_id,
                "module_id": module_id,
                "module_code": module_code,
                "week": w,
                "attendance_status": status,
            }
            result[w].append(row)

    return result
