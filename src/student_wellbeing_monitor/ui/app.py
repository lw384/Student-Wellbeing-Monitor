"""src/wellbeing_system/ui/app.py"""

import math
import os

from dotenv import load_dotenv
from flask import Flask, flash, redirect, render_template, request, url_for

from student_wellbeing_monitor.database.read import (
    count_attendance,
    count_students,
    count_submission,
    count_wellbeing,
    get_all_modules,
    get_all_students,
    get_all_weeks,
    get_attendance_by_id,
    get_attendance_page,
    get_programmes,
    get_student_by_id,
    get_submission_by_id,
    get_submission_page,
    # get_course_summary,
    get_wellbeing_by_id,
    get_wellbeing_page,
)
from student_wellbeing_monitor.database.update import (
    update_attendance,
    update_submission,
    update_wellbeing,
)
from student_wellbeing_monitor.services.attendance_service import attendance_service
from student_wellbeing_monitor.services.course_service import course_service
from student_wellbeing_monitor.services.upload_service import import_csv_by_type
from student_wellbeing_monitor.services.wellbeing_service import wellbeing_service

load_dotenv()


app = Flask(
    __name__,
    template_folder="templates",  #  ui/templates
    static_folder="static",  #  ui/static
)
app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET_KEY", "dev-secret-key")

TABLE_FIELDS = {
    "students": [
        ("student_id", "Student ID"),
        ("name", "Name"),
        ("email", "Email"),
        ("programme", "Programme"),
    ],
    "wellbeing": [
        ("student_id", "Student ID"),
        ("name", "Student Name"),
        ("week", "Week"),
        ("stress_level", "Stress Level"),
        ("hours_slept", "Hours Slept"),
    ],
    "attendance": [
        ("student_id", "Student ID"),
        ("name", "Name"),
        ("module_code", "Module Code"),
        ("module_name", "Module"),
        ("week", "Week"),
        ("status", "Status"),
    ],
    "submissions": [
        ("student_id", "Student ID"),
        ("student_name", "Name"),
        ("programme_name", "Programme"),
        ("module_name", "Module"),
        ("submitted", "Submitted"),
        ("grade", "Grade"),
        ("due_date", "Due"),
        ("submit_date", "Submit"),
    ],
}


# -------- 1. entrance: select role --------
@app.route("/")
def index():
    """
    Home page: Let user choose role (Wellbeing Officer / Course Director)
    """
    return render_template("index.html")


def resolve_week_range(args):
    weeks = get_all_weeks() or [1]
    return {
        "weeks": weeks,
        "start_week": args.get("start_week", type=int, default=min(weeks)),
        "end_week": args.get("end_week", type=int, default=max(weeks)),
    }


def resolve_programme_and_module(args, role):
    programme_rows = get_programmes()
    programmes = [
        {
            "id": r["programme_id"],
            "code": r["programme_code"],
            "name": r["programme_name"],
        }
        for r in programme_rows
    ]

    current_programme = args.get("programme_id") or None
    if role == "course_leader" and not current_programme and programmes:
        current_programme = programmes[0]["id"]

    current_module = args.get("module_id", default="", type=str) or None

    return {
        "programmes": programmes,
        "current_programme": current_programme,
        "current_module": current_module,
    }


def load_modules_by_programme():
    modules_by_programme = {}
    for r in get_all_modules():
        pid = r["programme_id"]
        modules_by_programme.setdefault(pid, []).append(
            {"id": r["module_id"], "code": r["module_code"], "name": r["module_name"]}
        )
    return modules_by_programme


def get_target_modules(modules_by_programme, programme_id, module_id=None):
    programme_modules = modules_by_programme.get(programme_id, [])
    if module_id:
        return [m for m in programme_modules if m["id"] == module_id]
    return programme_modules


def build_summary(role, start_week, end_week, current_programme, current_module):
    if role == "wellbeing":
        s = wellbeing_service.get_dashboard_summary(
            start_week, end_week, programme_id=current_programme or None
        )
        return {
            "response_count": s["surveyResponses"]["studentCount"],
            "response_rate": s["surveyResponses"]["responseRate"],
            "avg_sleep": s["avgHoursSlept"],
            "avg_stress": s["avgStressLevel"],
        }
    else:
        return course_service.get_course_leader_summary(
            programme_id=current_programme,
            module_id=current_module,
            week_start=start_week,
            week_end=end_week,
        )


def build_charts_for_wellbeing(start_week, end_week, current_programme):
    line = wellbeing_service.get_stress_sleep_trend(
        start_week, end_week, programme_id=current_programme or None
    )
    weeks_for_chart = line.get("weeks", [])
    avg_stress = line.get("stress", [])
    avg_sleep = line.get("sleep", [])

    prog_stats = course_service.get_programme_wellbeing_engagement(
        programme_id=current_programme or None,
        week_start=start_week,
        week_end=end_week,
    )
    programme_bar = prog_stats.get("programmes", [])

    programme_labels = [
        p.get("programmeName") or p.get("programmeId") or "Unknown"
        for p in programme_bar
    ]
    programme_avg_stress = [p.get("avgStress") for p in programme_bar]
    programme_attendance_rate = [p.get("attendanceRate") for p in programme_bar]
    programme_submission_rate = [p.get("submissionRate") for p in programme_bar]
    programme_avg_grade = [p.get("avgGrade") for p in programme_bar]

    return {
        "weeks_for_chart": weeks_for_chart,
        "avg_stress": avg_stress,
        "avg_sleep": avg_sleep,
        "attendance_trend": [],
        "grade_trend": [],
        "programme_stats": {
            "labels": programme_labels,
            "avgStress": programme_avg_stress,
            "attendanceRate": programme_attendance_rate,
            "submissionRate": programme_submission_rate,
            "avgGrade": programme_avg_grade,
        },
        "scatter_points": [],
    }


def build_charts_for_course_leader(
    start_week, end_week, current_programme, current_module, modules_by_programme
):
    trend = attendance_service.get_attendance_trends(
        course_id=current_module,
        programme_id=current_programme,
        week_start=start_week,
        week_end=end_week,
    )
    points = trend.get("points", [])

    weeks_for_chart = [p["week"] for p in points]
    attendance_trend = [p["attendanceRate"] for p in points]
    grade_trend = [p.get("avgGrade") for p in points]

    scatter = {}
    scatter_points = []

    submission_labels = []
    submission_submitted = []
    submission_unsubmitted = []
    if current_programme:
        scatter = course_service.get_attendance_vs_grades(
            course_id=current_module,
            programme_id=current_programme,
            week_start=start_week,
            week_end=end_week,
        )
        scatter_points = scatter.get("points", [])

        target_modules = get_target_modules(
            modules_by_programme,
            programme_id=current_programme,
            module_id=current_module,
        )

        for m in target_modules:
            ss = course_service.get_submission_summary(
                programme_id=current_programme,
                course_id=m["id"],
                assignment_no=None,
            )
            submission_labels.append(m["code"])
            submission_submitted.append(ss.get("submit", 0))
            submission_unsubmitted.append(ss.get("unsubmit", 0))

    return {
        "weeks_for_chart": weeks_for_chart,
        "avg_stress": [],
        "avg_sleep": [],
        "attendance_trend": attendance_trend,
        "submission_labels": submission_labels,
        "submission_submitted": submission_submitted,
        "submission_unsubmitted": submission_unsubmitted,
        "grade_trend": grade_trend,
        "programme_stats": {
            "labels": [],
            "avgStress": [],
            "attendanceRate": [],
            "submissionRate": [],
            "avgGrade": [],
        },
        "scatter_points": scatter_points,
    }


def build_charts(
    role, start_week, end_week, current_programme, current_module, modules_by_programme
):
    if role == "wellbeing":
        return build_charts_for_wellbeing(start_week, end_week, current_programme)
    return build_charts_for_course_leader(
        start_week, end_week, current_programme, current_module, modules_by_programme
    )


def build_risks_for_wellbeing(start_week, end_week, current_programme, run_ai):
    students_to_contact = []
    table = wellbeing_service.get_risk_students(
        start_week, end_week, programme_id=current_programme or None
    )
    for item in table.get("items", []):
        students_to_contact.append(
            {
                "student_id": int(item["studentId"]),
                "name": item["name"],
                "email": item["email"],
                "reason": item["reason"],
                "detail": item["details"],
            }
        )

    ai_result = None
    if current_programme and run_ai:
        ai_result = course_service.analyze_high_stress_sleep_with_ai(
            programme_id=current_programme,
            week_start=start_week,
            week_end=end_week,
        )

    return {
        "students_to_contact": students_to_contact,
        "attendance_risk_students": [],
        "submission_risk_students": [],
        "ai_result": ai_result,
    }


def build_risks_for_course_leader(
    start_week, end_week, current_programme, current_module, modules_by_programme
):
    attendance_risk_students = []
    submission_risk_students = []

    if current_programme:
        target_modules = get_target_modules(
            modules_by_programme, current_programme, current_module
        )
        # A. attendance risk
        for m in target_modules:
            low = attendance_service.get_low_attendance_students(
                course_id=m["id"],
                programme_id=current_programme,
                week_start=start_week,
                week_end=end_week,
                threshold_rate=0.8,
                min_absences=2,
            )
            for stu in low.get("students", []):
                attendance_risk_students.append(
                    {
                        "module_code": m["code"],
                        "student_id": stu["studentId"],
                        "name": stu["name"],
                        "email": stu["email"],
                        "attendance_rate": stu["attendanceRate"],
                        "absent_sessions": stu["absentSessions"],
                    }
                )

        # B. submission risk
        repeated = course_service.get_repeated_missing_students(
            course_id=current_module or None,
            programme_id=current_programme or None,
            start_week=start_week,
            end_week=end_week,
            min_offending_modules=2,
        )
        for stu in repeated.get("students", []):
            submission_risk_students.append(
                {
                    "student_id": stu["studentId"],
                    "name": stu["name"],
                    "email": stu["email"],
                    "offending_module_count": stu["offendingModuleCount"],
                    "details": stu.get("details", []),
                }
            )

    return {
        "students_to_contact": [],
        "attendance_risk_students": attendance_risk_students,
        "submission_risk_students": submission_risk_students,
        "ai_result": None,
    }


def build_risks(
    role,
    start_week,
    end_week,
    current_programme,
    current_module,
    modules_by_programme,
    run_ai,
):
    if role == "wellbeing":
        return build_risks_for_wellbeing(
            start_week, end_week, current_programme, run_ai
        )
    return build_risks_for_course_leader(
        start_week, end_week, current_programme, current_module, modules_by_programme
    )


# -------- 2. Dashboard：based on roles --------
@app.route("/dashboard/<role>")
def dashboard(role):

    # ---------- 0. Validation ----------
    if role not in ("wellbeing", "course_leader"):
        return redirect(url_for("index"))

    # ---------- 1. Base parameters ----------
    week_ctx = resolve_week_range(request.args)
    prog_ctx = resolve_programme_and_module(request.args, role)
    modules_by_programme = load_modules_by_programme()

    # ---------- 2. Summary cards ----------
    summary = build_summary(
        role,
        week_ctx["start_week"],
        week_ctx["end_week"],
        prog_ctx["current_programme"],
        prog_ctx["current_module"],
    )

    # ---------- 3. chart ----------
    # wellbeing: stress/sleep line + programme bar
    # course: attendance/ line + submission vs module bar + attendance vs grade scatter
    charts = build_charts(
        role,
        week_ctx["start_week"],
        week_ctx["end_week"],
        prog_ctx["current_programme"],
        prog_ctx["current_module"],
        modules_by_programme,
    )

    # ---------- 5. chart ----------
    run_ai = request.args.get("run_ai") == "1"
    risks = build_risks(
        role,
        week_ctx["start_week"],
        week_ctx["end_week"],
        prog_ctx["current_programme"],
        prog_ctx["current_module"],
        modules_by_programme,
        run_ai,
    )

    # ---------- 7. Render ----------
    return render_template(
        "dashboard.html",
        role=role,
        weeks=week_ctx["weeks"],
        current_start_week=week_ctx["start_week"],
        current_end_week=week_ctx["end_week"],
        programmes=prog_ctx["programmes"],
        modules_by_programme=modules_by_programme,
        current_programme=prog_ctx["current_programme"],
        current_module=prog_ctx["current_module"],
        summary=summary,
        **charts,
        **risks,
    )


@app.route("/upload/<role>", methods=["GET", "POST"])
def upload_data(role):
    if request.method == "POST":
        file = request.files.get("file")
        data_type = request.form.get(
            "data_type"
        )  # wellbeing / attendance / submissions
        # TODO: Parse CSV based on data_type and write to database
        # After processing, redirect back to corresponding list page:
        if not file or file.filename == "":
            flash("Please select a CSV file to upload.", "warning")
            return redirect(url_for("upload_data", role=role))

        try:
            import_csv_by_type(data_type, file)
            flash(f"Successfully imported {data_type} data.", "success")
            return redirect(url_for("view_data", role=role))
        except Exception as e:
            # In real project can log, here keep it simple
            print("Upload error:", e)
            flash(f"Failed to import {data_type} data: {e}", "danger")

    return render_template(
        "upload.html",
        role=role,
        active_page="upload",
    )


def enrich_student_programme(raw_rows, programme_map):
    """
    raw_rows: sqlite3.Row list, fields include student_id, name, email, programme_id
    programme_map: { programme_id: "CODE – NAME" }
    """
    enriched = []
    for row in raw_rows:
        enriched.append(
            {
                "student_id": row["student_id"],
                "name": row["name"],
                "email": row["email"],
                # Convert to human-readable text using map, fallback to programme_id if not found
                "programme": programme_map.get(
                    row["programme_id"], row["programme_id"]
                ),
                # Optional: keep id
                "programme_id": row["programme_id"],
            }
        )
    return enriched


# -------- 3. View data tables --------
@app.route("/data/<role>", defaults={"data_type": "students"})
@app.route("/data/<role>/<data_type>")
def view_data(role, data_type):
    page = request.args.get("page", default=1, type=int)
    if page < 1:
        page = 1

    per_page = 10
    offset = (page - 1) * per_page

    programme_rows = get_programmes()
    programme_map = {
        row["programme_id"]: f"{row['programme_code']} – {row['programme_name']}"
        for row in programme_rows
    }

    fields = TABLE_FIELDS[data_type]

    student_id_filter = request.args.get("student_id", "", type=str).strip()
    sort_week = request.args.get("sort_week", "", type=str).strip()

    # ========== students ==========
    if data_type == "students":
        if student_id_filter:
            row = get_student_by_id(student_id_filter)
            if row:
                rows = [row]  # Put into list for template rendering
                total = 1
            else:
                rows = []
                total = 0
        else:
            total = count_students()
            raw_rows = get_all_students(limit=per_page, offset=offset)
            rows = raw_rows

        rows = enrich_student_programme(rows, programme_map)

    # ========== wellbeing ==========
    elif data_type == "wellbeing":
        total = count_wellbeing(student_id_filter or None)
        rows = get_wellbeing_page(
            limit=per_page,
            offset=offset,
            student_id=student_id_filter or None,
            sort_week=sort_week or None,
        )

    # ========== attendance ==========
    elif data_type == "attendance":
        total = count_attendance(student_id_filter or None)
        rows = get_attendance_page(
            limit=per_page,
            offset=offset,
            student_id=student_id_filter or None,
            sort_week=sort_week or None,
        )

    # ========== submissions ==========
    elif data_type == "submissions":
        total = count_submission(student_id_filter or None)
        rows = get_submission_page(
            limit=per_page,
            offset=offset,
            student_id=student_id_filter or None,
        )

    else:
        flash("Unknown data type", "danger")
        return redirect(url_for("dashboard", role=role))

    # Calculate total pages uniformly
    total_pages = max(1, math.ceil(total / per_page))

    if page > total_pages:
        page = total_pages

    return render_template(
        "data_table.html",
        role=role,
        data_type=data_type,
        rows=rows,
        page=page,
        fields=fields,
        total_pages=total_pages,
        active_page="data",
    )


# app.py
@app.route("/data/<role>/<data_type>/<int:record_id>/edit", methods=["GET", "POST"])
def edit_record(role, data_type, record_id):
    page = request.args.get("page", default=1, type=int)

    if data_type == "wellbeing":
        # First find the record
        record = get_wellbeing_by_id(record_id)
        if not record:
            flash("Record not found", "danger")
            return redirect(
                url_for("view_data", role=role, data_type=data_type, page=page)
            )

        if request.method == "POST":
            # 1. Get form data
            stress = int(request.form["stress_level"])
            sleep = float(request.form["hours_slept"])

            # 2. Update database
            update_wellbeing(record_id, stress, sleep)

            # 3. Show message + return to list page (or stay on edit page, depends on needs)
            flash("Wellbeing record updated", "success")
            return redirect(
                url_for("view_data", role=role, data_type=data_type, page=page)
            )

        # GET: Render edit form page with current record pre-filled
        return render_template(
            "edit.html",  # Make sure this template exists
            role=role,
            data_type=data_type,
            record=record,
            page=page,
        )
    elif data_type == "attendance":
        record = get_attendance_by_id(record_id)
        if not record:
            flash("Record not found", "danger")
            return redirect(
                url_for("view_data", role=role, data_type=data_type, page=page)
            )

        if request.method == "POST":
            status = int(request.form["status"])
            current_week = record["week"]
            update_attendance(record_id, status, current_week)

            flash("Attendance record updated", "success")
            return redirect(
                url_for("view_data", role=role, data_type=data_type, page=page)
            )

        return render_template(
            "edit_attendance.html",
            role=role,
            data_type=data_type,
            record=record,
            page=page,
        )
    elif data_type == "submissions":
        record = get_submission_by_id(record_id)
        if not record:
            flash("Record not found", "danger")
            return redirect(
                url_for("view_data", role=role, data_type=data_type, page=page)
            )

        if request.method == "POST":
            submitted = int(request.form["submitted"])
            grade = float(request.form["grade"] or 0)
            due_date = request.form["due_date"]
            submit_date = request.form["submit_date"]

            update_submission(record_id, submitted, grade, due_date, submit_date)

            flash("Submission record updated", "success")
            return redirect(
                url_for("view_data", role=role, data_type=data_type, page=page)
            )

        return render_template(
            "edit_submission.html",
            role=role,
            data_type=data_type,
            record=record,
            page=page,
        )
        # Other data_type not implemented yet
    else:
        flash("Editing this data type is not supported yet.", "warning")

    return redirect(url_for("view_data", role=role, data_type=data_type, page=page))


def run_app():
    # The wellbeing-web script in pyproject.toml will call this
    app.run(debug=True)


if __name__ == "__main__":
    run_app()
