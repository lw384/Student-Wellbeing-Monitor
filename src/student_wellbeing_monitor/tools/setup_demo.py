import csv
import subprocess
import sys
from pathlib import Path
from student_wellbeing_monitor.database import create
from student_wellbeing_monitor.database.schema import init_db_schema
from student_wellbeing_monitor.tools.reset_db import reset_database

BASE_DIR = Path(__file__).resolve().parents[3]
MOCK_DIR = BASE_DIR / "mock_data" / "mock"
MOCK_SCRIPT = BASE_DIR / "mock_data" / "scripts" / "generate_entities.py"

print("Path------------", BASE_DIR, "----", MOCK_DIR, MOCK_SCRIPT)


def run_generate_mock():
    print("🛠 Generating mock CSV...")
    result = subprocess.run(
        [sys.executable, str(MOCK_SCRIPT)], capture_output=True, text=True
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


def setup_demo():
    run_generate_mock()
    reset_database()
    init_db_schema()

    seed_programme()
    seed_student()
    seed_module()
    seed_student_module()

    print("🎉 Demo database ready!")


if __name__ == "__main__":
    setup_demo()
