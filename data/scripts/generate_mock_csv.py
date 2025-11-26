from faker import Faker
from pathlib import Path
import csv
import random
import argparse

fake = Faker()

# 默认输出目录
DEFAULT_OUTPUT_DIR = Path("data/mock")

# 各表字段
STUDENT_FIELDS = ["student_id", "name", "email", "modules"]
MODULE_FIELDS = ["module_id", "module_name", "module_code"]
STUDENT_MODULE_FIELDS = ["student_id", "module_id"]
WELLBEING_FIELDS = ["student_id", "week", "stress_level", "hours_slept", "comment"]


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
    Generate n modules with Warwick-style module codes, e.g. WG1F6.
    Pattern: Letter + Letter + Digit + Letter + Digit
    """
    module_names = [
        "AI Fundamentals",
        "Python Programming",
        "Data Analytics",
        "Software Engineering",
        "Machine Learning",
        "Statistics for Data Science",
    ]

    subjects = ["WG", "CS", "MA", "EC", "DS", "SE", "ML"]
    letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

    modules: list[dict] = []

    for i in range(n):
        subject_code = random.choice(subjects)
        level = str(random.randint(1, 3))
        mid_letter = random.choice(letters)
        tail_digit = str(random.randint(1, 9))

        module_code = subject_code + level + mid_letter + tail_digit

        modules.append(
            {
                "module_id": i + 1,
                "module_name": random.choice(module_names),
                "module_code": module_code,
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


def generate_wellbeing_records(students: list[dict], weeks: int = 12) -> list[dict]:
    """
    Generate weekly wellbeing records for each student.
    - stress_level: 1–5
    - hours_slept: 4–9
    """
    records: list[dict] = []
    for s in students:
        for w in range(1, weeks + 1):
            records.append(
                {
                    "student_id": s["student_id"],
                    "week": w,
                    "stress_level": random.randint(1, 5),
                    "hours_slept": random.randint(4, 9),
                    "comment": fake.sentence(nb_words=8),
                }
            )
    return records


def generate_wellbeing_by_week(
    students: list[dict],
    weeks: int = 12,
    min_response_rate: float = 0.5,
    max_response_rate: float = 0.95,
    exam_weeks: list[int] | None = None,
) -> dict[int, list[dict]]:
    """
    Wellbeing data is generated weekly, simulating three patterns:
    1) Students under chronic stress (stress increases weekly)
    2) Students who are sleep-deprived but do not report stress
    3) Normal students
    Several weeks are also supported as "exam weeks," with overall increased stress and decreased sleep.

    Return structure:
    { week_number: [ { student_id, week, stress_level, hours_slept, comment }, ... ], ... }
    """
    if exam_weeks is None:
        # assume exam week, could change
        exam_weeks = [8, 9, 10]

    result: dict[int, list[dict]] = {w: [] for w in range(1, weeks + 1)}

    for s in students:
        # possibilty of finish survey
        response_rate = random.uniform(min_response_rate, max_response_rate)

        #
        profile = random.choices(
            population=["normal", "chronic_stress", "low_sleep_hidden_stress"],
            weights=[
                0.6,
                0.2,
                0.2,
            ],  # 60% normal，20% high stress，20% low sleep and low stress
            k=1,
        )[0]

        base_stress = random.randint(1, 3)

        for w in range(1, weeks + 1):
            # write survey or not
            if random.random() > response_rate:
                continue

            # 生成 stress 和 sleep
            # basic random fluctuation
            stress = base_stress + random.choice([-1, 0, 0, 1])
            hours_slept = random.randint(6, 8)

            if profile == "chronic_stress":
                stress = base_stress + int(w / (weeks / 3)) + random.choice([0, 0, 1])
                hours_slept = random.randint(5, 7)

            elif profile == "low_sleep_hidden_stress":
                hours_slept = random.randint(1, 6)
                stress = random.randint(1, 3)

            else:
                # normal 学生：stress 1–4 之间小波动
                stress = base_stress + random.choice([-1, 0, 0, 1])

            # exam_week
            if w in exam_weeks:
                stress += 1  # 全体压力更大
                hours_slept -= 1  # 睡得更少

            stress = max(1, min(5, stress))
            hours_slept = max(1, min(9, hours_slept))

            row = {
                "student_id": s["student_id"],
                "week": w,
                "stress_level": stress,
                "hours_slept": hours_slept,
                "comment": fake.sentence(nb_words=8),
            }
            result[w].append(row)

    return result


def write_csv(filename: Path, fieldnames: list[str], rows: list[dict]) -> None:
    """
    Write a list of dict rows into a CSV file at the given path.
    Automatically creates parent directories if needed.
    """
    filename = Path(filename)
    filename.parent.mkdir(parents=True, exist_ok=True)

    with filename.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames,
            extrasaction="ignore",  # 忽略多余字段，防止小拼写错误直接崩掉
        )
        writer.writeheader()
        writer.writerows(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate mock CSV data for students, modules, student_modules and wellbeing."
    )
    parser.add_argument(
        "--out",
        type=str,
        default=str(DEFAULT_OUTPUT_DIR),
        help="Output directory for generated CSV files (default: data/mock)",
    )
    parser.add_argument(
        "--students",
        type=int,
        default=30,
        help="Number of students to generate (default: 50)",
    )
    parser.add_argument(
        "--weeks",
        type=int,
        default=8,
        help="Number of weeks for wellbeing records (default: 8)",
    )
    parser.add_argument(
        "--modules",
        type=int,
        default=6,
        help="Number of modules to generate (default: 6)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_dir = Path(args.out)

    students = generate_students(args.students)
    modules = generate_modules(args.modules)

    # student_modules = generate_student_modules(students, modules)
    # wellbeing = generate_wellbeing_records(students, weeks=args.weeks)

    wellbeing_by_week = generate_wellbeing_by_week(
        students,
        weeks=args.weeks,
    )

    # write in csv
    write_csv(output_dir / "students.csv", STUDENT_FIELDS, students)
    write_csv(output_dir / "modules.csv", MODULE_FIELDS, modules)
    # write_csv(
    #     output_dir / "student_modules.csv", STUDENT_MODULE_FIELDS, student_modules
    # )
    # write_csv(output_dir / "wellbeing.csv", WELLBEING_FIELDS, wellbeing)

    for week, rows in wellbeing_by_week.items():
        # 没有人填这周 survey → 可以选择跳过这一周的文件
        if not rows:
            continue

        filename = output_dir / f"wellbeing_week{week}.csv"
        write_csv(filename, WELLBEING_FIELDS, rows)

    print(f"✅ CSV generated in: {output_dir.resolve()}")
    print(f"   - students.csv ({len(students)} rows)")
    print(f"   - modules.csv ({len(modules)} rows)")
    # print(f"   - student_modules.csv ({len(student_modules)} rows)")
    print(f"   - wellbeing.csv ({len(wellbeing_by_week)} rows)")


if __name__ == "__main__":
    main()
