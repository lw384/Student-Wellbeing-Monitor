import random
from datetime import datetime, timedelta
from .base import fake


def generate_submissions_by_module(
    student_modules: list[dict],
    modules: list[dict],
    not_submitted_rate: float = 0.1,
    multi_non_submit_ratio: float = 0.05,  # 选多门课但全部不交作业的学生比例
) -> dict[str, list[dict]]:
    """
    为每个 (student, module) 生成一条 submission 记录，并按 module_code 分组返回。

    返回结构：
        {
          "WG1F6": [
            {
              student_id, module_id, module_code,
              submitted, grade,
              due_date, submit_date
            }, ...
          ],
          ...
        }

    约束：
    - 学生只要在 student_modules 里选了该课程，就一定在该课程的 submissions 中出现一行
    - 一小部分选了多门课的学生，被设定为“所有课都不交作业”
    - 其他学生 submitted 二元（1=提交, 0=未提交），未提交比例接近 not_submitted_rate
    - 成绩范围 40～80，>=70 为少数，50 为及格线
    - due_date 为每门课固定的一个日期（所有学生相同）
    - submit_date 只在 submitted == 1 时生成，可能早交或晚交
    """
    # module_id -> module_code 映射
    module_id_to_code: dict[int, str] = {
        m["module_id"]: m["module_code"] for m in modules
    }

    # ⭐ 为每个 module_id 生成一个固定的截止日期（ISO 格式字符串）
    module_due_date: dict[int, str] = {}
    for m in modules:
        mid = m["module_id"]
        # 在一个合理范围内随机一个日期（你也可以固定月份）
        due = fake.date_between(start_date="+7d", end_date="+60d")
        module_due_date[mid] = due.isoformat()  # '2025-02-10' 这种格式

    # 统计每个 student 选了多少门课
    student_to_modules: dict[int, set[int]] = {}
    for rel in student_modules:
        sid = rel["student_id"]
        mid = rel["module_id"]
        student_to_modules.setdefault(sid, set()).add(mid)

    # 找出选了 >=2 门课的学生
    multi_module_students = [
        sid for sid, mids in student_to_modules.items() if len(mids) >= 2
    ]

    # 从这些学生中选一小部分，标记为“所有课都不交作业”的高风险学生
    num_multi_non_submit = (
        max(1, int(len(multi_module_students) * multi_non_submit_ratio))
        if multi_module_students
        else 0
    )
    always_not_submit_students: set[int] = (
        set(random.sample(multi_module_students, num_multi_non_submit))
        if num_multi_non_submit > 0
        else set()
    )

    submissions_by_module: dict[str, list[dict]] = {}

    for rel in student_modules:
        student_id = rel["student_id"]
        module_id = rel["module_id"]
        module_code = module_id_to_code.get(module_id, "UNKNOWN")
        due_date = module_due_date[module_id]  # 这一门课的统一截止日期

        if module_code not in submissions_by_module:
            submissions_by_module[module_code] = []

        # 🎯 决定是否提交
        if student_id in always_not_submit_students:
            # 这一类学生：所有课都不交
            submitted = 0
            grade = ""
            submit_date = ""   # 没交作业，没有提交日期
        else:
            # 普通学生：大部分提交，少数不交
            submitted = int(random.random() > not_submitted_rate)
            if submitted == 0:
                grade = ""
                submit_date = ""
            else:
                # 已提交：生成 40–80 分的成绩（和你原来一样）
                r = random.random()
                if r < 0.2:
                    grade = random.randint(70, 80)
                elif r < 0.8:
                    grade = random.randint(50, 69)
                else:
                    grade = random.randint(40, 49)

                # ====== 生成 submit_date ======
                # 80% 学生按时或提前提交，20% 晚交
                due_dt = datetime.fromisoformat(due_date)
                if random.random() < 0.8:
                    # 提前 0~3 天
                    delta_days = random.randint(-3, 0)
                else:
                    # 晚交 1~5 天
                    delta_days = random.randint(1, 5)

                submit_dt = due_dt + timedelta(days=delta_days)
                submit_date = submit_dt.date().isoformat()

        submissions_by_module[module_code].append(
            {
                "student_id": student_id,
                "module_id": module_id,
                "module_code": module_code,
                "submitted": submitted,   # 0/1
                "grade": grade,           # 未提交为空字符串
                "due_date": due_date,     # '2025-02-10'
                "submit_date": submit_date,  # '' 或 '2025-02-09'
            }
        )

    return submissions_by_module