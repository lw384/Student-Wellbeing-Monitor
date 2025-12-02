from pprint import pprint
import os
import sys

# Current file: src/student_wellbeing_monitor/services/test.py
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
# Add .../Student-Wellbeing-Monitor/src to sys.path
SRC_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "..", ".."))

if SRC_ROOT not in sys.path:
    sys.path.insert(0, SRC_ROOT)

from student_wellbeing_monitor.database.db_core import get_conn
from student_wellbeing_monitor.services.attendance_service import AttendanceService
from student_wellbeing_monitor.services.course_service import CourseService

# -------------------------------------------------------------------
# Utility: fetch several modules from the database as sample test data
# -------------------------------------------------------------------
def get_example_modules(limit: int = 3):
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("SELECT module_id, module_name FROM module LIMIT ?", (limit,))
        rows = cur.fetchall()
    except Exception as e:
        print("Failed to query table 'module', please check table or column names:", e)
        rows = []
    finally:
        conn.close()
    return rows


def print_header(title: str):
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)


def main():
    # 1. Print some modules so we know what is being tested
    modules = get_example_modules(limit=3)
    if not modules:
        print("No module records found in the database, cannot test Course Leader APIs.")
        return

    print_header("Available modules (first 3)")
    for mid, mname in modules:
        print(f"- module_id={mid}, module_name={mname}")

    # Select a course as the test target
    # test_course_id, test_course_name = modules[0]
    test_course_id = "4530893"
    test_course_name = "Energy Storage Systems"
    print_header(f"Selected course for testing: {test_course_id} ({test_course_name})")

    # 2. Create service instances
    att_service = AttendanceService()
    course_service = CourseService()

    # Week range for the mock data
    WEEK_START = 1
    WEEK_END = 8
    ASSIGNMENT_NO = 1  # Assume there is assignment 1

    # ------------------------------------------------------------------
    # 1. AttendanceService.get_attendance_trends
    # ------------------------------------------------------------------
    print_header("1. AttendanceService.get_attendance_trends")
    try:
        result = att_service.get_attendance_trends(
            course_id=test_course_id,
            programme_id=None,     # Do not filter by programme for now
            week_start=WEEK_START,
            week_end=WEEK_END,
        )
        pprint(result)
    except Exception as e:
        print("Error in get_attendance_trends:", e)

    # ------------------------------------------------------------------
    # 2. CourseService.get_submission_summary
    # ------------------------------------------------------------------
    print_header("2. CourseService.get_submission_summary")
    try:
        result = course_service.get_submission_summary(
            course_id=test_course_id,
            assignment_no=ASSIGNMENT_NO,  # Use the real assignment number if available
            programme_id=None,
        )
        pprint(result)
    except Exception as e:
        print("Error in get_submission_summary:", e)

    # ------------------------------------------------------------------
    # 3. AttendanceService.get_low_attendance_students
    # ------------------------------------------------------------------
    print_header("3. AttendanceService.get_low_attendance_students")
    try:
        result = att_service.get_low_attendance_students(
            course_id=test_course_id,
            programme_id=None,
            week_start=WEEK_START,
            week_end=WEEK_END,
            threshold_rate=0.8,   # Attendance rate below 0.8 is considered problematic
            min_absences=2,       # Or at least 2 absences
        )
        pprint(result)
    except Exception as e:
        print("Error in get_low_attendance_students:", e)

    # ------------------------------------------------------------------
    # 4. CourseService.get_repeated_missing_students
    # ------------------------------------------------------------------
    print_header("4. CourseService.get_repeated_missing_students")
    try:
        result = course_service.get_repeated_missing_students(
            course_id=None,            # None = search across all modules for students with missing submissions
            programme_id=None,
            start_week=None,
            end_week=None,
            min_offending_modules=2,   # At least 2 modules with missing submissions
        )
        pprint(result)
    except Exception as e:
        print("Error in get_repeated_missing_students:", e)

    # ------------------------------------------------------------------
    # 5. CourseService.get_attendance_vs_grades
    # ------------------------------------------------------------------
    print_header("5. CourseService.get_attendance_vs_grades")
    try:
        result = course_service.get_attendance_vs_grades(
            course_id=test_course_id,
            programme_id=None,
            week_start=WEEK_START,
            week_end=WEEK_END,
        )
        pprint(result)
    except Exception as e:
        print("Error in get_attendance_vs_grades:", e)

    # ------------------------------------------------------------------
    # 6. CourseService.get_programme_wellbeing_engagement
    # ------------------------------------------------------------------
    print_header("6. CourseService.get_programme_wellbeing_engagement")
    try:
        result = course_service.get_programme_wellbeing_engagement(
            course_id=test_course_id,
            week_start=WEEK_START,
            week_end=WEEK_END,
        )
        pprint(result)
    except Exception as e:
        print("Error in get_programme_wellbeing_engagement:", e)

    print_header("All test calls finished (does not guarantee business correctness, only that functions executed)")


if __name__ == "__main__":
    main()
