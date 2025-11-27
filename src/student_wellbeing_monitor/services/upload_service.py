# src/student_wellbeing_monitor/services/upload_service.py
import csv
import io
from typing import TextIO

from student_wellbeing_monitor.database import create  # 你自己的插入函数模块


# from student_wellbeing_monitor.database import db_core  # connect
def read_csv(file_storage) -> list[dict]:
    """把 Flask 上传的文件对象转换成 Dict 列表"""
    # file_storage 是 werkzeug.datastructures.FileStorage
    text_stream: TextIO = io.TextIOWrapper(file_storage.stream, encoding="utf-8")
    reader = csv.DictReader(text_stream)
    return list(reader)


def import_wellbeing_csv(file_storage):
    rows = read_csv(file_storage)
    for row in rows:
        create.add_wellbeing(
            int(row["student_id"]),
            int(row["week"]),
            int(row["stress_level"]),
            int(row["hours_slept"]),
        )


def import_attendance_csv(file_storage):
    rows = read_csv(file_storage)
    for row in rows:
        # 假设字段：student_id, module_code, week, attendance_status
        create.insert_attendance(
            student_id=int(row["student_id"]),
            module_code=row["module_code"],
            week=int(row["week"]),
            status=int(row["attendance_status"]),  # 0/1
        )


def import_submissions_csv(file_storage):
    rows = read_csv(file_storage)
    for row in rows:
        # 假设字段：student_id, module_code, submitted, grade, due_date, submit_date
        create.insert_submission(
            student_id=int(row["student_id"]),
            module_code=row["module_code"],
            submitted=int(row["submitted"]),
            grade=row["grade"] or None,
            due_date=row.get("due_date"),
            submit_date=row.get("submit_date"),
        )


def import_csv_by_type(data_type: str, file_storage):
    """UI 层只调用这一层的统一入口"""
    if data_type == "wellbeing":
        import_wellbeing_csv(file_storage)
    elif data_type == "attendance":
        import_attendance_csv(file_storage)
    elif data_type == "submissions":
        import_submissions_csv(file_storage)
    else:
        raise ValueError(f"Unsupported data_type: {data_type}")
