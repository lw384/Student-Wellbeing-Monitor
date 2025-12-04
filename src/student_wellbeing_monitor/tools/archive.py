# src/student_wellbeing_monitor/scripts/archive.py

import argparse
from pathlib import Path

from student_wellbeing_monitor.services.archive_service import run_archive

PROJECT_ROOT = Path(__file__).resolve().parents[3]


def main():
    parser = argparse.ArgumentParser(description="Archive and delete student data.")
    parser.add_argument(
        "--output",
        type=str,
        default=str(PROJECT_ROOT / "archive"),
        help="Directory to save exported aggregate CSV files.",
    )
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Actually delete data. Without this flag, the CLI runs in dry-run mode.",
    )

    args = parser.parse_args()

    run_archive(output_dir=args.output, delete_confirm=args.confirm)


if __name__ == "__main__":
    main()
