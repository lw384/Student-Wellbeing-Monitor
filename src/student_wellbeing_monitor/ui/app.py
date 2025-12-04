# src/wellbeing_system/ui/app.py
from flask import Flask, render_template, request, redirect, url_for, flash
import os
import math
from student_wellbeing_monitor.database.read import (
    get_programmes,
    get_all_modules,
    get_all_weeks,
    get_all_students,
    get_student_by_id,
    count_students,
    count_wellbeing,
    count_attendance,
    count_submission,
    get_wellbeing_by_id,
    get_wellbeing_page,
    get_attendance_page,
    get_submission_page,
    # get_course_summary,
)
from student_wellbeing_monitor.database.update import update_wellbeing
from student_wellbeing_monitor.services.upload_service import import_csv_by_type
from student_wellbeing_monitor.services.wellbeing_service import wellbeing_service
from student_wellbeing_monitor.services.course_service import course_service
from student_wellbeing_monitor.services.attendance_service import attendance_service


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
    首页：让用户选择角色（Wellbeing Officer / Course Director）
    """
    return render_template("index.html")


# -------- 2. Dashboard：based on roles --------
@app.route("/dashboard/<role>")
def dashboard(role):

    # ---------- 0. 校验 ----------
    if role not in ("wellbeing", "course_leader"):
        return redirect(url_for("index"))

    # ---------- 1. 基础参数 ----------
    weeks = get_all_weeks() or [1]
    start_week = request.args.get("start_week", type=int, default=min(weeks))
    end_week = request.args.get("end_week", type=int, default=max(weeks))

    # programme
    programme_rows = get_programmes()
    programmes = [
        {
            "id": r["programme_id"],
            "code": r["programme_code"],
            "name": r["programme_name"],
        }
        for r in programme_rows
    ]
    current_programme = request.args.get("programme_id")

    # 如果是 course_leader 强制默认第一个 programme
    if role == "course_leader" and not current_programme and programmes:
        current_programme = programmes[0]["id"]

    # module
    current_module = request.args.get("module_id", default="", type=str)

    # ---------- 2. 模块数据（统一加载一次） ----------
    modules_by_programme = {}
    all_module_rows = get_all_modules()

    for r in all_module_rows:
        pid = r["programme_id"]
        modules_by_programme.setdefault(pid, []).append(
            {"id": r["module_id"], "code": r["module_code"], "name": r["module_name"]}
        )

    # ---------- 3. Summary 卡片 ----------
    if role == "wellbeing":
        s = wellbeing_service.get_dashboard_summary(
            start_week, end_week, programme_id=current_programme or None
        )
        summary = {
            "response_count": s["surveyResponses"]["studentCount"],
            "response_rate": s["surveyResponses"]["responseRate"],
            "avg_sleep": s["avgHoursSlept"],
            "avg_stress": s["avgStressLevel"],
        }
    else:
        summary = course_service.get_course_leader_summary(
            programme_id=current_programme,
            module_id=current_module,
            week_start=start_week,
            week_end=end_week,
        )

    # ---------- 4. 折线图 ----------
    weeks_for_chart = []
    avg_stress = []
    avg_sleep = []
    attendance_trend = []
    grade_trend = []

    if role == "wellbeing":
        line = wellbeing_service.get_stress_sleep_trend(
            start_week, end_week, programme_id=current_programme or None
        )
        weeks_for_chart = line.get("weeks", [])
        avg_stress = line.get("stress", [])
        avg_sleep = line.get("sleep", [])

    else:  # course_leader
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

    # ---------- 5. 作业提交柱状图 ----------
    submission_labels = []
    submission_submitted = []
    submission_unsubmitted = []

    if role == "course_leader" and current_programme:
        programme_modules = modules_by_programme.get(current_programme, [])

        # 决定绘制哪些 module
        if current_module:
            target_modules = [m for m in programme_modules if m["id"] == current_module]
        else:
            target_modules = programme_modules

        for m in target_modules:
            ss = course_service.get_submission_summary(
                programme_id=current_programme,
                course_id=m["id"],
                assignment_no=None,
            )
            submission_labels.append(m["code"])
            submission_submitted.append(ss.get("submit", 0))
            submission_unsubmitted.append(ss.get("unsubmit", 0))

    # ---------- 6. 风险学生 ----------
    students_to_contact = []
    attendance_risk_students = []
    submission_risk_students = []

    if role == "wellbeing":
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

    else:  # course leader
        # -------- A. 出勤风险 --------
        if current_programme:
            programme_modules = modules_by_programme.get(current_programme, [])
            if current_module:
                target_modules = [
                    m for m in programme_modules if m["id"] == current_module
                ]
            else:
                target_modules = programme_modules

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

        # -------- B. 作业提交风险（跨课程） --------
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

    # ---------- 7. 渲染 ----------
    return render_template(
        "dashboard.html",
        role=role,
        weeks=weeks,
        current_start_week=start_week,
        current_end_week=end_week,
        programmes=programmes,
        modules_by_programme=modules_by_programme,
        current_programme=current_programme,
        current_module=current_module,
        summary=summary,
        weeks_for_chart=weeks_for_chart,
        avg_stress=avg_stress,
        avg_sleep=avg_sleep,
        attendance_trend=attendance_trend,
        grade_trend=grade_trend,
        submission_labels=submission_labels,
        submission_submitted=submission_submitted,
        submission_unsubmitted=submission_unsubmitted,
        students_to_contact=students_to_contact,
        attendance_risk_students=attendance_risk_students,
        submission_risk_students=submission_risk_students,
    )


@app.route("/upload/<role>", methods=["GET", "POST"])
def upload_data(role):
    if request.method == "POST":
        file = request.files.get("file")
        data_type = request.form.get(
            "data_type"
        )  # wellbeing / attendance / submissions
        # TODO: 根据 data_type 解析 CSV，写入数据库
        # 处理完之后跳回对应列表页：
        if not file or file.filename == "":
            flash("Please select a CSV file to upload.", "warning")
            return redirect(url_for("upload_data", role=role))

        try:
            import_csv_by_type(data_type, file)
            flash(f"Successfully imported {data_type} data.", "success")
            return redirect(url_for("view_data", role=role))
        except Exception as e:
            # 真项目里可以 log，这里简单一点
            print("Upload error:", e)
            flash(f"Failed to import {data_type} data: {e}", "danger")

    return render_template(
        "upload.html",
        role=role,
        active_page="upload",
    )


def enrich_student_programme(raw_rows, programme_map):
    """
    raw_rows: sqlite3.Row 列表，字段包含 student_id, name, email, programme_id
    programme_map: { programme_id: "CODE – NAME" }
    """
    enriched = []
    for row in raw_rows:
        enriched.append(
            {
                "student_id": row["student_id"],
                "name": row["name"],
                "email": row["email"],
                # 用 map 转成人类可读的文本，如果找不到就回退到原来的 programme_id
                "programme": programme_map.get(
                    row["programme_id"], row["programme_id"]
                ),
                # 可选保留 id
                "programme_id": row["programme_id"],
            }
        )
    return enriched


# -------- 3. 查看数据表 --------
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
                rows = [row]  # 存入列表，以便模板正常渲染
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

    # 统一计算总页数
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
        # 先查记录
        record = get_wellbeing_by_id(record_id)
        if not record:
            flash("Record not found", "danger")
            return redirect(
                url_for("view_data", role=role, data_type=data_type, page=page)
            )

        if request.method == "POST":
            # 1. 取表单数据
            stress = int(request.form["stress_level"])
            sleep = float(request.form["hours_slept"])

            # 2. 更新数据库
            update_wellbeing(record_id, stress, sleep)

            # 3. 给提示 + 回到列表页（或留在 edit 页，按你需求）
            flash("Wellbeing record updated", "success")
            return redirect(
                url_for("view_data", role=role, data_type=data_type, page=page)
            )

        # GET：渲染编辑表单页面，用当前记录预填
        return render_template(
            "edit.html",  # 确保这个模板存在
            role=role,
            data_type=data_type,
            record=record,
            page=page,
        )

    # 其他 data_type 还没实现
    flash("Editing this data type is not supported yet.", "warning")
    return redirect(url_for("view_data", role=role, data_type=data_type, page=page))


@app.post("/data/<role>/<data_type>/<int:record_id>/delete")
def delete_record(role, data_type, record_id):
    page = request.args.get("page", default=1, type=int)

    if data_type == "wellbeing":

        delete_wellbeing(record_id)
        flash("Wellbeing record deleted", "success")

    # elif data_type == "attendance": delete_attendance(record_id)
    # elif data_type == "submissions": delete_submissions(record_id)

    else:
        flash("Delete not supported for this data type.", "warning")

    return redirect(url_for("view_data", role=role, data_type=data_type, page=page))


def run_app():
    # 你 pyproject.toml 里 wellbeing-web 脚本会调用这个
    app.run(debug=True)


if __name__ == "__main__":
    run_app()
