"""CSV Import Service"""

import csv
import io
from typing import TextIO

from student_wellbeing_monitor.database import create

# from student_wellbeing_monitor.database import db_core  # connect


def read_csv(file_storage) -> list[dict]:
    """
    Read a CSV file uploaded via Flask FileStorage and return a list of row dicts.
    Args:
        file_storage: werkzeug.datastructures.FileStorage uploaded by user.
    Returns:
        List[dict]: Each dictionary represents a row parsed by csv.DictReader.
    """
    text_stream: TextIO = io.TextIOWrapper(file_storage.stream, encoding="utf-8")
    reader = csv.DictReader(text_stream)
    return list(reader)


def import_wellbeing_csv(file_storage):
    """
    Import wellbeing data from CSV and insert into the wellbeing table.
    """
    rows = read_csv(file_storage)
    for row in rows:
        # Hypothetical field：student_id, week, stress_level, hours_slept
        create.insert_wellbeing(
            int(row["student_id"]),
            int(row["week"]),
            int(row["stress_level"]),
            int(row["hours_slept"]),
        )


def import_attendance_csv(file_storage):
    """
    Import attendance data from CSV and insert into the attendance table.
    """
    rows = read_csv(file_storage)
    for row in rows:
        # Hypothetical field：student_id, module_id, week, status, session_number=1
        create.insert_attendance(
            student_id=int(row["student_id"]),
            module_id=row["module_id"],
            week=int(row["week"]),
            status=int(row["attendance_status"]),  # 0/1
        )


def import_submissions_csv(file_storage):
    """
    Import submission data from CSV and insert into the attendance table.
    """
    rows = read_csv(file_storage)
    for row in rows:
        # Hypothetical field： student_id,module_id,due_date,submit_date,
        create.insert_submission(
            student_id=int(row["student_id"]),
            module_id=row["module_id"],
            submitted=int(row["submitted"]),
            grade=row["grade"] or None,
            due_date=row.get("due_date"),
            submit_date=row.get("submit_date"),
        )


def import_csv_by_type(data_type: str, file_storage):
    """check data types and call corresponding import function"""
    if data_type == "wellbeing":
        import_wellbeing_csv(file_storage)
    elif data_type == "attendance":
        import_attendance_csv(file_storage)
    elif data_type == "submissions":
        import_submissions_csv(file_storage)
    else:
        raise ValueError(f"Unsupported data_type: {data_type}")
