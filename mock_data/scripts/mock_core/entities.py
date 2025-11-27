import random
from .base import fake


def generate_students(n: int = 20) -> list[dict]:
    """
    Generate a list of students.
    - student_id: 7-digit number starting with 5 (5000000–5999999)
    - email: based on name + @warwick.ac.uk
    """
    students: list[dict] = []
    used_ids: set[int] = set()

    while len(students) < n:
        student_id = random.randint(5000000, 5999999)
        if student_id in used_ids:
            continue
        used_ids.add(student_id)

        name = fake.name()

        email_local = name.lower().replace(" ", ".").replace("-", "").replace("'", "")
        email = f"{email_local}.{random.randint(1, 99)}@warwick.ac.uk"

        students.append(
            {
                "student_id": student_id,
                "name": name,
                "email": email,
                "modules": "",
            }
        )

    return students


def generate_modules(n: int = 6) -> list[dict]:
    """
    Generate modules with:
    - module_id: 7-digit internal code
    - module_code: readable course code (e.g. WG1F6)
    - module_name: random chosen name
    """
    module_names = [
        "AI Fundamentals",
        "Python Programming",
        "Data Analytics",
        "Software Engineering",
        "Machine Learning",
        "Statistics for Data Science",
    ]

    subjects = {
        "WG": 87,
        "CS": 31,
        "ML": 92,
        "DS": 44,
        "SE": 53,
        "MA": 62,
        "EC": 75,
    }

    letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    modules = []

    used_ids = set()

    for i in range(n):
        # Pick subject prefix
        subject = random.choice(list(subjects.keys()))
        subject_num = subjects[subject]

        # Build module_code
        level = str(random.randint(1, 3))
        mid_letter = random.choice(letters)
        tail_digit = str(random.randint(1, 9))
        module_code = subject + level + mid_letter + tail_digit

        # Build module_id = subject_num * 10000 + random 4 digits
        while True:
            internal_suffix = random.randint(1000, 9999)
            module_id = subject_num * 10000 + internal_suffix
            if module_id not in used_ids:
                used_ids.add(module_id)
                break
        modules.append(
            {
                "module_id": module_id,  # 7-digit internal ID
                "module_code": module_code,  # readable course code
                "module_name": random.choice(module_names),
            }
        )

    return modules


def generate_student_modules(
    students: list[dict],
    modules: list[dict],
    min_courses: int = 2,
    max_courses: int = 4,
) -> list[dict]:
    """
    Assign 2-4 courses to each student and generate a `student_modules` table.
    Also, add a 'modules' field (comma-separated string of `module_code`) to the `students` table
    """
    records: list[dict] = []

    for s in students:
        count = random.randint(min_courses, max_courses)
        selected = random.sample(modules, count)

        # 关系表记录
        for m in selected:
            records.append(
                {
                    "student_id": s["student_id"],
                    "module_id": m["module_id"],
                }
            )
        s["modules"] = ", ".join(m["module_code"] for m in selected)

    return records
