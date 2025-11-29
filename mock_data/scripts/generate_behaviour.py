"""Generate behaviour data: wellbeing submission attendance"""

# poetry run python mock_data/scripts/generate_behaviour.py
from pathlib import Path
import argparse
from mock_core import (
    DEFAULT_OUTPUT_DIR,
    WELLBEING_FIELDS,
    ATTENDANCE_FIELDS,
    SUBMISSION_FIELDS,
    generate_wellbeing_by_week,
    generate_attendance_by_week,
    generate_submissions_by_module,
    load_csv,
    write_csv,
    clean_old_behaviour_files,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]  # Student-Wellbeing-Monitor
MOCK_DIR = PROJECT_ROOT / "mock_data" / "mock"

STUDENTS_CSV = MOCK_DIR / "students.csv"
MODULES_CSV = MOCK_DIR / "modules.csv"
STU_MODULE_CSV = MOCK_DIR / "student_module.csv"

# Prefix - output filename
WELLBEING_PREFIX = "wellbeing_week"  # wellbeing_week1.csv ...
ATTENDANCE_PREFIX = "attendance_week"  # attendance_week1.csv ...
SUBMISSIONS_PREFIX = "submissions_"


def parse_args():
    parser = argparse.ArgumentParser(
        description="Generate only students, modules, and student_modules CSVs."
    )
    parser.add_argument(
        "--out",
        type=str,
        default=str(DEFAULT_OUTPUT_DIR),
        help="Output directory (default: data/mock)",
    )
    parser.add_argument(
        "--weeks",
        type=int,
        default=12,
        help="Number of weeks for attendance / wellbeing (default: 8)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    out_dir = Path(args.out)
    clean_old_behaviour_files(MOCK_DIR)

    # 1. read entities
    students = load_csv(STUDENTS_CSV)
    modules = load_csv(MODULES_CSV)
    student_modules = load_csv(STU_MODULE_CSV)

    # 2. wellbeing / attendance / submissions
    wellbeing_by_week = generate_wellbeing_by_week(students, weeks=args.weeks)
    attendance_by_week = generate_attendance_by_week(
        student_modules, modules, weeks=args.weeks
    )
    submissions = generate_submissions_by_module(student_modules, modules)

    # 3. write CSV：wellbeing_weekX / attendance_weekX / submission_.csv
    # wellbeing
    for week, rows in wellbeing_by_week.items():
        if not rows:
            continue
        path = out_dir / f"{WELLBEING_PREFIX}{week}.csv"
        write_csv(path, WELLBEING_FIELDS, rows)

    # attendance
    for week, rows in attendance_by_week.items():
        if not rows:
            continue
        path = out_dir / f"{ATTENDANCE_PREFIX}{week}.csv"
        write_csv(path, ATTENDANCE_FIELDS, rows)

    # submissions
    for module_code, rows in submissions.items():
        path = out_dir / f"submissions_{module_code}.csv"
        write_csv(path, SUBMISSION_FIELDS, rows)

    print(f"✅ Behaviour CSV generated in: {out_dir.resolve()}")
    print(f"   - wellbeing_week*.csv")
    print(f"   - attendance_week*.csv")
    print(f"   - submissions_*.csv")


if __name__ == "__main__":
    main()
