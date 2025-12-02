# 生成假数据、插入数据库中
# 只插入student\programme\module相关数据
# poetry run setup-demo
# 所有数据全部都插入，运行下边这条命令
# poetry run setup-demo --with-mock
import csv
import subprocess
import sys
import argparse
from pathlib import Path
from student_wellbeing_monitor.database import create
from student_wellbeing_monitor.database.schema import init_db_schema
from student_wellbeing_monitor.tools.reset_db import reset_database

BASE_DIR = Path(__file__).resolve().parents[3]
MOCK_DIR = BASE_DIR / "mock_data" / "mock"

MOCK_SCRIPT = BASE_DIR / "mock_data" / "scripts" / "generate_entities.py"
BEHAVIOUR_SCRIPT = BASE_DIR / "mock_data" / "scripts" / "generate_behaviour.py"

print("Path------------", BASE_DIR, "----", MOCK_DIR, MOCK_SCRIPT)



def parse_args():
    parser = argparse.ArgumentParser(description="Setup demo database")
    parser.add_argument(
        "--with-mock",
        action="store_true",
        help="Import mock wellbeing/attendance/submission data into database",
    )
    return parser.parse_args()


def run_generate_entities():
    print("🛠 Generating mock entities CSV...")
    result = subprocess.run(
        [sys.executable, str(MOCK_SCRIPT)], capture_output=True, text=True
    )
    print(result.stdout)
    if result.returncode != 0:
        print(result.stderr)
        raise RuntimeError("❌ CSV generation failed!")
    print("✅ CSV generated.")


def run_generate_mock():
    print("🛠 Generating mock wellbeing/submission/attendance CSV...")
    result = subprocess.run(
        [sys.executable, str(BEHAVIOUR_SCRIPT)], capture_output=True, text=True
    )
    print(result.stdout)
    if result.returncode != 0:
        print(result.stderr)
        raise RuntimeError("❌ CSV generation failed!")
    print("✅ CSV generated.")


def seed_programme():
    csv_path = MOCK_DIR / "programmes.csv"
    print(f"🌱 Seeding programme from: {csv_path}")

    with csv_path.open("r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            create.insert_programme(
                programme_id=row["programme_id"],
                programme_name=row["programme_name"],
                programme_code=row["programme_code"],
            )
    print("✅ Programme inserted.")


def seed_student():
    csv_path = MOCK_DIR / "students.csv"
    print(f"🌱 Seeding students from: {csv_path}")

    with csv_path.open("r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            create.insert_student(
                student_id=row["student_id"],
                name=row["name"],
                email=row["email"],
                programme_id=row["programme_id"],
            )
    print("✅ Students inserted.")


def seed_module():
    csv_path = MOCK_DIR / "modules.csv"
    print(f"🌱 Seeding modules from: {csv_path}")

    with csv_path.open("r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            create.insert_module(
                module_id=row["module_id"],
                module_name=row["module_name"],
                module_code=row["module_code"],
                programme_id=row["programme_id"],
            )
    print("✅ Modules inserted.")


def seed_student_module():
    csv_path = MOCK_DIR / "student_module.csv"
    print(f"🌱 Seeding student_module from: {csv_path}")

    with csv_path.open("r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            create.insert_student_module(
                student_id=row["student_id"],
                module_id=row["module_id"],
            )
    print("✅ student_module inserted.")


def seed_wellbeing():
    csv_path = MOCK_DIR / "student_module.csv"
    print(f"🌱 Seeding student_module from: {csv_path}")

    with csv_path.open("r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            create.insert_wellbeing(
                student_id=row["student_id"],
                module_id=row["module_id"],
            )
    print("✅ student_module inserted.")


def seed_wellbeing():
    files = sorted(MOCK_DIR.glob("wellbeing_week*.csv"))
    if not files:
        print("⚠️ No wellbeing_week*.csv found, skip seeding wellbeing.")
        return

    print("🌱 Seeding wellbeing records from weekly CSVs...")

    total_rows = 0
    for csv_path in files:
        print(f"  - {csv_path.name}")
        with csv_path.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                create.insert_wellbeing(
                    student_id=row["student_id"],
                    week=int(row["week"]),
                    stress_level=int(row["stress_level"]),
                    hours_slept=float(row["hours_slept"]),
                    comment=row["comment"],
                )
                total_rows += 1

    print(f"✅ Wellbeing records inserted: {total_rows}")


def seed_attendance():
    files = sorted(MOCK_DIR.glob("attendance_week*.csv"))
    if not files:
        print("⚠️ No attendance_week*.csv found, skip seeding wellbeing.")
        return

    print("🌱 Seeding attendance records from weekly CSVs...")

    total_rows = 0
    for csv_path in files:
        print(f"  - {csv_path.name}")
        with csv_path.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                create.insert_attendance(
                    student_id=row["student_id"],
                    module_id=int(row["module_id"]),
                    week=int(row["week"]),
                    status=int(row["attendance_status"]),
                )
                total_rows += 1

    print(f"✅ Attendance records inserted: {total_rows}")


def seed_submission():
    files = sorted(MOCK_DIR.glob("submissions_*.csv"))
    if not files:
        print("⚠️ No submissions_*.csv found, skip seeding wellbeing.")
        return

    print("🌱 Seeding submission records from weekly CSVs...")

    total_rows = 0
    for csv_path in files:
        print(f"  - {csv_path.name}")
        with csv_path.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # grade may = ""
                grade_str = row.get("grade", "").strip()
                grade = float(grade_str) if grade_str != "" else None

                create.insert_submission(
                    student_id=row["student_id"],
                    module_id=int(row["module_id"]),
                    submitted=int(row["submitted"]),
                    due_date=row["due_date"],
                    submit_date=row["submit_date"],
                    grade=grade,
                )
                total_rows += 1

    print(f"✅ Submission records inserted: {total_rows}")


def setup_demo():
    args = parse_args()

    # 1. generate mock data
    run_generate_entities()
    # 2. clear database
    reset_database()
    # 3. create data schema
    init_db_schema()

    # 4. insert basic data
    seed_programme()
    seed_student()
    seed_module()
    seed_student_module()
    print("🎉 Mock basic data inserted.")

    # 5. insert addtional data: poetry run setup-demo --with-mock
    if args.with_mock:
        run_generate_mock()
        print(" Importing mock wellbeing / attendance / submission.")
        seed_wellbeing()
        seed_attendance()
        seed_submission()
        print("🎉 Mock dynamic data inserted.")

    print("🎉 Demo database ready!")


if __name__ == "__main__":
    setup_demo()
