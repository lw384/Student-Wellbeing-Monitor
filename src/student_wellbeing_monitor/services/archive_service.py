# src/student_wellbeing_monitor/services/archive_service.py

import csv
import os
from collections import defaultdict

from student_wellbeing_monitor.database.delete import (
    delete_all_attendance,
    delete_all_student_modules,
    delete_all_students,
    delete_all_submissions,
    delete_all_wellbeing,
)
from student_wellbeing_monitor.database.read import (
    count_attendance,
    count_submission,
    get_attendance_page,
    get_submission_page,
    get_wellbeing_records,
)


def write_csv(path, rows, header):
    """Save a list of tuples/dicts into CSV."""
    os.makedirs(os.path.dirname(path), exist_ok=True)

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        for row in rows:
            writer.writerow(row)


# -----------------------------
# 1. Export Aggregated Summaries
# -----------------------------


def export_wellbeing_summary(output_dir: str) -> None:
    """
    Export an anonymised wellbeing summary.

    Aggregation:
      - Group by (programme_id, week)
      - For each group: avg_stress, avg_hours_slept, record_count

    No student-level rows are exported.
    """
    # get_wellbeing_records(start_week, end_week, programme_id=None, student_id=None)
    rows = get_wellbeing_records(1, 99, programme_id=None, student_id=None)

    # rows: (student_id, week, stress_level, hours_slept, programme_id)
    grouped = defaultdict(
        lambda: {
            "stress_sum": 0.0,
            "sleep_sum": 0.0,
            "stress_count": 0,
            "sleep_count": 0,
        }
    )

    for student_id, week, stress, hours_slept, programme_id in rows:
        # We ignore student_id completely here for privacy.
        key = (programme_id, week)

        # Stress
        if stress is not None:
            try:
                grouped[key]["stress_sum"] += float(stress)
                grouped[key]["stress_count"] += 1
            except (TypeError, ValueError):
                pass

        # Sleep
        if hours_slept is not None:
            try:
                grouped[key]["sleep_sum"] += float(hours_slept)
                grouped[key]["sleep_count"] += 1
            except (TypeError, ValueError):
                pass

    # Build aggregated rows
    out_rows = []
    for (programme_id, week), agg in grouped.items():
        stress_avg = (
            agg["stress_sum"] / agg["stress_count"] if agg["stress_count"] > 0 else None
        )
        sleep_avg = (
            agg["sleep_sum"] / agg["sleep_count"] if agg["sleep_count"] > 0 else None
        )
        record_count = max(agg["stress_count"], agg["sleep_count"])

        out_rows.append(
            (
                programme_id,
                week,
                round(stress_avg, 2) if stress_avg is not None else None,
                round(sleep_avg, 2) if sleep_avg is not None else None,
                record_count,
            )
        )

    path = os.path.join(output_dir, "wellbeing_summary.csv")
    header = ["programme_id", "week", "avg_stress", "avg_hours_slept", "record_count"]
    write_csv(path, out_rows, header)
    print(f"✓ Wellbeing summary (aggregated) exported → {path}")


def export_attendance_summary(output_dir: str) -> None:
    """
    Export an anonymised attendance summary.

    Assumes get_attendance_page returns:
      (id, student_id, module_id, week, status)
    Aggregation:
      - Group by (module_id, week)
      - For each group: attendance_rate, present_count, total_count

    No student-level rows are exported.
    """
    total = count_attendance()
    if total == 0:
        print("ℹ No attendance data to export.")
        return

    rows = get_attendance_page(limit=total, offset=0)

    # Use dict-based access, NOT unpacking
    grouped = defaultdict(lambda: {"present": 0, "total": 0})

    for row in rows:
        module_id = row["module_id"]
        week = row["week"]
        status = row["status"]

        key = (module_id, week)
        grouped[key]["total"] += 1

        try:
            if status is not None and int(status) == 1:
                grouped[key]["present"] += 1
        except:
            pass

    out_rows = []
    for (module_id, week), agg in grouped.items():
        total_count = agg["total"]
        present_count = agg["present"]
        rate = present_count / total_count if total_count > 0 else 0.0

        out_rows.append(
            (
                module_id,
                week,
                round(rate, 3),
                present_count,
                total_count,
            )
        )

    path = os.path.join(output_dir, "attendance_summary.csv")
    header = ["module_id", "week", "attendance_rate", "present_count", "total_count"]
    write_csv(path, out_rows, header)

    print(f"✓ Attendance summary (aggregated) exported → {path}")


def export_submission_summary(output_dir: str) -> None:
    """
    Export anonymised, aggregated submission summary, grouped by (module_id, due_date).

    Output columns:
      - module_id
      - due_date
      - total_students
      - submitted_count
      - avg_grade_submitted
    """
    total = count_submission()
    if total == 0:
        print("ℹ No submission data to export.")
        return

    rows = get_submission_page(limit=total, offset=0)

    # key: (module_id, due_date)  -> aggregated stats
    grouped = defaultdict(
        lambda: {
            "total": 0,
            "submitted": 0,
            "grade_sum": 0.0,
            "grade_count": 0,
        }
    )

    for row in rows:
        module_id = row["module_id"]
        due_date = row[
            "due_date"
        ]  # It can be either str or datetime. CSV will be written out according to str
        submitted = row["submitted"]
        grade = row["grade"]

        key = (module_id, due_date)
        agg = grouped[key]

        agg["total"] += 1

        # submitted: 0 / 1
        try:
            if submitted is not None and int(submitted) == 1:
                agg["submitted"] += 1

                # Only calculate the average score for those that have been submitted
                if grade is not None:
                    try:
                        g = float(grade)
                        agg["grade_sum"] += g
                        agg["grade_count"] += 1
                    except (TypeError, ValueError):
                        pass
        except (TypeError, ValueError):
            #  If "submitted" is not 0/1, it is treated as unsubmitted and skipped
            pass

    out_rows = []
    for (module_id, due_date), agg in grouped.items():
        total = agg["total"]
        submitted = agg["submitted"]
        if agg["grade_count"] > 0:
            avg_grade = agg["grade_sum"] / agg["grade_count"]
        else:
            avg_grade = None

        out_rows.append(
            (
                module_id,
                due_date,
                total,
                submitted,
                round(avg_grade, 2) if avg_grade is not None else "",
            )
        )

    path = os.path.join(output_dir, "submission_summary.csv")
    header = [
        "module_id",
        "due_date",
        "total_students",
        "submitted_count",
        "avg_grade_submitted",
    ]
    write_csv(path, out_rows, header)

    print(f"✓ Submission summary (aggregated) exported → {path}")


# -----------------------------
# 2. Delete All Personal Data
# -----------------------------


def delete_all_data():
    """
    Delete all student-related records in the correct order:
    1. Child tables (wellbeing, attendance, submission, student_module)
    2. Parent table (student)
    """
    # 1) Delete child tables that reference student_id
    delete_all_wellbeing()
    delete_all_attendance()
    delete_all_submissions()
    delete_all_student_modules()  # delete relationship first

    # 2) Finally delete from student
    delete_all_students()

    print("✓ All student-related records have been deleted.")


# -----------------------------
# 3. Main Workflow
# -----------------------------


def run_archive(output_dir: str, delete_confirm: bool) -> None:
    print("=== Exporting anonymised aggregated summaries ===")

    export_wellbeing_summary(output_dir)
    export_attendance_summary(output_dir)
    export_submission_summary(output_dir)

    print("\n=== Export completed ===")

    if not delete_confirm:
        print("\n⚠️ Dry run mode: No data has been deleted.")
        print("   Use --confirm to actually delete all personal data.")
        return

    print("\n⚠️ WARNING: You are about to delete ALL student-level data.")
    confirm = input("Type 'DELETE' to proceed: ")

    if confirm == "DELETE":
        delete_all_data()
        print("✔ Archive complete — all individual data removed.")
    else:
        print("✗ Operation cancelled. No data deleted.")
