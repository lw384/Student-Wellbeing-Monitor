# data/scripts/generate_all_mock.py
from pathlib import Path
import argparse

from mock_core import (
    DEFAULT_OUTPUT_DIR,
    STUDENT_FIELDS,
    MODULE_FIELDS,
    STUDENT_MODULE_FIELDS,
    ATTENDANCE_FIELDS,
    SUBMISSION_FIELDS,
    WELLBEING_FIELDS,
    generate_students,
    generate_modules,
    generate_student_modules,
    generate_attendance_by_week,
    generate_submissions_by_module,
    generate_wellbeing_by_week,
    write_csv,
    clean_mock_csv,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate mock CSV data for students, modules, attendance, submissions and wellbeing."
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
        help="Number of students to generate (default: 30)",
    )
    parser.add_argument(
        "--weeks",
        type=int,
        default=8,
        help="Number of weeks for attendance / wellbeing (default: 8)",
    )
    parser.add_argument(
        "--modules",
        type=int,
        default=6,
        help="Number of modules to generate (default: 6)",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Clean existing mock CSV files before generating new ones.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_dir = Path(args.out)

    if args.clean:
        print("🧹 Cleaning existing mock CSV files...")
        clean_mock_csv(output_dir)
        print("✨ Clean completed.\n")

    # 1. core entities
    students = generate_students(args.students)
    modules = generate_modules(args.modules)
    student_modules = generate_student_modules(students, modules)

    # 2. derived data
    attendance_by_week = generate_attendance_by_week(
        student_modules,
        modules,
        weeks=args.weeks,
    )
    submissions_by_module = generate_submissions_by_module(
        student_modules,
        modules,
    )
    wellbeing_by_week = generate_wellbeing_by_week(
        students,
        weeks=args.weeks,
    )

    # 3. write core CSVs
    write_csv(output_dir / "students.csv", STUDENT_FIELDS, students)
    write_csv(output_dir / "modules.csv", MODULE_FIELDS, modules)
    write_csv(
        output_dir / "student_modules.csv", STUDENT_MODULE_FIELDS, student_modules
    )

    # 4. submissions-<module_code>.csv
    for module_code, rows in submissions_by_module.items():
        filename = output_dir / f"submissions-{module_code}.csv"
        write_csv(filename, SUBMISSION_FIELDS, rows)

    # 5. wellbeing_weekX.csv
    for week, rows in wellbeing_by_week.items():
        if not rows:
            continue
        filename = output_dir / f"wellbeing_week{week}.csv"
        write_csv(filename, WELLBEING_FIELDS, rows)

    # 6. attendance_weekX.csv
    for week, rows in attendance_by_week.items():
        if not rows:
            continue
        filename = output_dir / f"attendance_week{week}.csv"
        write_csv(filename, ATTENDANCE_FIELDS, rows)

    print(f"CSV generated in: {output_dir.resolve()}")
    print(f"   - students.csv ({len(students)} rows)")
    print(f"   - modules.csv ({len(modules)} rows)")
    print(f"   - student_modules.csv ({len(student_modules)} rows)")
    print(f"   - wellbeing weeks: {len(wellbeing_by_week)}")
    print(f"   - attendance weeks: {len(attendance_by_week)}")
    print(f"   - submissions files: {len(submissions_by_module)}")


if __name__ == "__main__":
    main()
