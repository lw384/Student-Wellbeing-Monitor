"""Generate basic data: programme module student"""

# poetry run python mock_data/scripts/generate_entities.py
from pathlib import Path
import argparse
from mock_core import (
    DEFAULT_OUTPUT_DIR,
    PROGRAMME_FIELDS,
    STUDENT_FIELDS,
    MODULE_FIELDS,
    STUDENT_MODULE_FIELDS,
    generate_students,
    generate_programmes,
    generate_modules,
    generate_student_modules,
    write_csv,
    clean_mock_csv,
)


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
        "--students",
        type=int,
        default=30,
        help="Number of students (default: 30)",
    )
    parser.add_argument(
        "--modules",
        type=int,
        default=6,
        help="Number of modules (default: 6)",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    out_dir = Path(args.out)
    clean_mock_csv(out_dir)

    programmes = generate_programmes()
    students = generate_students(programmes, args.students)
    modules = generate_modules(programmes, min_per_prog=3, max_per_prog=5)
    student_modules = generate_student_modules(students, modules)

    write_csv(out_dir / "programmes.csv", PROGRAMME_FIELDS, programmes)
    write_csv(out_dir / "students.csv", STUDENT_FIELDS, students)
    write_csv(out_dir / "modules.csv", MODULE_FIELDS, modules)
    write_csv(out_dir / "student_module.csv", STUDENT_MODULE_FIELDS, student_modules)

    print(f"✅ Core tables generated in: {out_dir.resolve()}")
    print(f"   - programmes.csv ({len(programmes)} rows)")
    print(f"   - students.csv ({len(students)} rows)")
    print(f"   - modules.csv ({len(modules)} rows)")
    print(f"   - student_module.csv ({len(student_modules)} rows)")


if __name__ == "__main__":
    main()
