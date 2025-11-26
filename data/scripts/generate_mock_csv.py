from faker import Faker
import csv
import random
from pathlib import Path
import csv

fake = Faker()

# output path
OUTPUT_DIR = Path("data/mock")


def generate_students(n=20):
    """student_id 为以 5 开头的随机 7 位数字"""
    students = []
    used_ids = set()
    while len(students) < n:
        # 5000000 ~ 5999999 的区间
        student_id = random.randint(5000000, 5999999)

        # void repeat
        if student_id in used_ids:
            continue

        used_ids.add(student_id)

        name = fake.name()

        email_local = (
            name.lower().replace(" ", ".").replace("-", "").replace("'", "")  # add .
        )
        email = f"{email_local}.{random.randint(1,99)}@warwick.ac.uk"

        students.append(
            {
                "student_id": student_id,
                "name": name,
                "email": email,
                "cohort": random.choice(["A", "B", "C"]),
            }
        )

    return students


def generate_wellbeing_records(students, weeks=12):
    """wellbeing 数据引用 students 里的 student_id"""
    records = []
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


def write_csv(filename, fieldnames, rows):
    filename = Path(filename)  # 安全转换为 Path 对象
    filename.parent.mkdir(parents=True, exist_ok=True)  # 自动创建目录

    with filename.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main():
    students = generate_students(30)  # ★ 生成一次学生
    wellbeing = generate_wellbeing_records(students, weeks=8)  # ★ 在这里复用

    write_csv(
        OUTPUT_DIR / "students.csv", ["student_id", "name", "email", "cohort"], students
    )
    write_csv(
        OUTPUT_DIR / "wellbeing.csv",
        ["student_id", "week", "stress_level", "hours_slept", "comment"],
        wellbeing,
    )

    print("CSV generated with shared student IDs.")


if __name__ == "__main__":
    main()
