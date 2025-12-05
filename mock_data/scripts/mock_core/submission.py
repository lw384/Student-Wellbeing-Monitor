"""
mock_data.scripts.mock_core.submission
"""

import random
from datetime import datetime, timedelta
from .base import fake


def generate_submissions_by_module(
    student_modules: list[dict],
    modules: list[dict],
    not_submitted_rate: float = 0.1,
    multi_non_submit_ratio: float = 0.05,  # The proportion of multi-module students who submit nothing
) -> dict[str, list[dict]]:
    """
    Generate one submission record for each (student, module) pair,
    and return the results grouped by module_code.

    Return structure:
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

    Constraints:
    - If a student has enrolled in a module (from student_modules), they must appear in that module's submissions.
    - A small proportion of students who take multiple modules are marked as “submit nothing for all modules”.
    - Other students have submitted = 1 or 0; the not-submitted rate approximates `not_submitted_rate`.
    - Grades range 40-80; >=70 is minority; 50 is the pass line.
    - Each module has a fixed due_date (same for all students).
    - submit_date is generated only when submitted == 1; can be early or late.
    """

    # Map: module_id -> module_code
    module_id_to_code: dict[int, str] = {
        m["module_id"]: m["module_code"] for m in modules
    }

    # Generate a fixed due_date for each module (ISO date string)
    module_due_date: dict[int, str] = {}
    for m in modules:
        mid = m["module_id"]
        # Random due date within a reasonable window
        due = fake.date_between(start_date="+7d", end_date="+60d")
        module_due_date[mid] = due.isoformat()

    # Count how many modules each student takes
    student_to_modules: dict[int, set[int]] = {}
    for rel in student_modules:
        sid = rel["student_id"]
        mid = rel["module_id"]
        student_to_modules.setdefault(sid, set()).add(mid)

    # Identify students who take >= 2 modules
    multi_module_students = [
        sid for sid, mids in student_to_modules.items() if len(mids) >= 2
    ]

    # Select a small group of these students who will submit *nothing*
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
        due_date = module_due_date[module_id]

        if module_code not in submissions_by_module:
            submissions_by_module[module_code] = []

        #  Determine submission status
        if student_id in always_not_submit_students:
            # These students submit nothing across all modules
            submitted = 0
            grade = ""
            submit_date = ""
        else:
            # Regular students: majority submit; minority do not
            submitted = int(random.random() > not_submitted_rate)
            if submitted == 0:
                grade = ""
                submit_date = ""
            else:
                # Generate grade between 40–80
                r = random.random()
                if r < 0.2:
                    grade = random.randint(70, 80)
                elif r < 0.8:
                    grade = random.randint(50, 69)
                else:
                    grade = random.randint(40, 49)

                # ===== Generate submit_date =====
                # 80% submit early or on time; 20% submit late
                due_dt = datetime.fromisoformat(due_date)
                if random.random() < 0.8:
                    # 0–3 days early
                    delta_days = random.randint(-3, 0)
                else:
                    # 1–5 days late
                    delta_days = random.randint(1, 5)

                submit_dt = due_dt + timedelta(days=delta_days)
                submit_date = submit_dt.date().isoformat()

        submissions_by_module[module_code].append(
            {
                "student_id": student_id,
                "module_id": module_id,
                "module_code": module_code,
                "submitted": submitted,
                "grade": grade,
                "due_date": due_date,
                "submit_date": submit_date,
            }
        )

    return submissions_by_module
