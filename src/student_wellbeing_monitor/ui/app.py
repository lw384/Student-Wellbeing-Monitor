# src/wellbeing_system/ui/app.py
from flask import Flask, render_template, request, redirect, url_for, flash
import os
import math
from student_wellbeing_monitor.database.read import (
    get_programmes,
    get_all_modules,
    get_all_weeks,
    get_all_students,
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
        ("week", "Week"),
        ("stress_level", "Stress Level"),
        ("hours_slept", "Hours Slept"),
    ],
    "attendance": [
        ("student_id", "Student ID"),
        ("module_code", "Module"),
        ("week", "Week"),
        ("status", "Status"),
    ],
    "submissions": [
        ("student_id", "Student ID"),
        ("module_code", "Module"),
        ("submitted", "Submitted"),
        ("grade", "Grade"),
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
    # 简单 role 校验
    if role not in ("wellbeing", "course_leader"):
        return redirect(url_for("index"))

    # 1. weeks list
    weeks = get_all_weeks()  # [1,2,3,4,5,6,7,8]
    start_week = request.args.get(
        "start_week", type=int, default=min(weeks) if weeks else 1
    )
    end_week = request.args.get(
        "end_week", type=int, default=max(weeks) if weeks else 8
    )

    # 2. programme list
    programme_rows = get_programmes()
    programmes = [
        {
            "id": row["programme_id"],
            "code": row["programme_code"],
            "name": row["programme_name"],
        }
        for row in programme_rows
    ]
    current_programme = request.args.get("programme_id")

    # 如果是 course_leader 且没有选择 → 默认第一个 programme
    if role == "course_leader" and not current_programme and programmes:
        current_programme = programmes[0]["id"]

    # 3. module list
    current_module = request.args.get("module_id", default="", type=str)

    # ✅ 一次性查所有 modules，然后按 programme_id 分组
    all_module_rows = get_all_modules()
    modules_by_programme: dict[str, list[dict]] = {}

    for row in all_module_rows:
        pid = row["programme_id"]
        modules_by_programme.setdefault(pid, []).append(
            {
                "id": row["module_id"],
                "code": row["module_code"],
                "name": row["module_name"],
            }
        )

    if role == "wellbeing":
        # summary
        summary_card = wellbeing_service.get_dashboard_summary(
            start_week,
            end_week,
            programme_id=current_programme if current_programme else None,
        )
        summary = {
            "response_count": summary_card["surveyResponses"]["studentCount"],
            "response_rate": summary_card["surveyResponses"]["responseRate"],
            "avg_sleep": summary_card["avgHoursSlept"],
            "avg_stress": summary_card["avgStressLevel"],
        }
    elif role == "course_leader":
        summary = course_service.get_course_leader_summary(
            programme_id=current_programme,
            module_id=current_module,
            week_start=start_week,
            week_end=end_week,
        )

    # 3) line
    if role == "wellbeing":
        line = wellbeing_service.get_stress_sleep_trend(
            start_week,
            end_week,
            programme_id=current_programme if current_programme else None,
        )

        weeks_for_chart = line.get("weeks", [])
        avg_stress = line.get("stress", [])
        avg_sleep = line.get("sleep", [])
        attendance_trend = []
        grade_trend = []

    elif role == "course_leader":
        trend = attendance_service.get_attendance_trends(
            course_id=current_module,
            programme_id=current_programme if current_programme else None,
            week_start=start_week,
            week_end=end_week,
        )

        points = trend.get("points", [])

        weeks_for_chart = [p["week"] for p in points]
        attendance_trend = [p["attendanceRate"] for p in points]
        grade_trend = [
            p.get("avgGrade") for p in points
        ]  # 如果没有 avgGrade，可以先传 None

        avg_stress = []
        avg_sleep = []

    # # 4) bar
    # --------------- 课程作业提交情况：grouped bar ---------------
    submission_labels = []  # X 轴：每个 module 名
    submission_submitted = []  # dataset 1
    submission_unsubmitted = []  # dataset 2

    if role == "course_leader" and current_programme:
        # 先拿到当前 programme 下的模块列表（list[dict]）
        modules = modules_by_programme.get(current_programme, [])

        if current_module:
            # 只画当前选中的那一门课
            target_modules = [m for m in modules if m["id"] == current_module]
        else:
            # 画这个 programme 下的所有 module
            target_modules = modules

        for m in target_modules:
            summary = course_service.get_submission_summary(
                programme_id=current_programme,
                course_id=m["id"],
                assignment_no=None,
            )

            submission_labels.append(f'{m["code"]} – {m["name"]}')
            submission_submitted.append(summary.get("submit", 0))
            submission_unsubmitted.append(summary.get("unsubmit", 0))
    else:
        submission_labels = []
        submission_submitted = []
        submission_unsubmitted = []

    students_to_contact = []
    attendance_risk_students = []
    submission_risk_students = []
    if role == "wellbeing":
        table = wellbeing_service.get_risk_students(
            start_week,
            end_week,
            programme_id=current_programme if current_programme else None,
        )

        items = table.get("items", [])
        students_to_contact = []
        for item in items:
            students_to_contact.append(
                {
                    "student_id": int(item["studentId"]),  # 转 int（可选）
                    "name": item["name"],
                    "reason": item["reason"],
                    "detail": item["details"],  # 注意 key 名不同
                }
            )
    else:
        if current_programme:
            # 1）确定要检查哪些 module
            # 如果页面选了某一门 module，就只查这一门
            if current_module:
                target_modules = [
                    m
                    for m in modules_by_programme.get(current_programme, [])
                    if m["id"] == current_module
                ]
            else:
                # All modules under this programme
                target_modules = modules_by_programme.get(current_programme, [])

            # 2）对每一个 module 调用 get_low_attendance_students
            for m in target_modules:
                module_id = m.get("id")  # 看你现在的字段名
                module_code = m["code"]

                result = attendance_service.get_low_attendance_students(
                    course_id=module_id,
                    programme_id=current_programme,
                    week_start=start_week,
                    week_end=end_week,
                    threshold_rate=0.8,
                    min_absences=2,
                )

                for stu in result.get("students", []):
                    attendance_risk_students.append(
                        {
                            "module_code": module_code,
                            "student_id": stu["studentId"],
                            "name": stu["name"],
                            "email": stu["email"],
                            "attendance_rate": stu["attendanceRate"],  # 0.6 这种
                            "absent_sessions": stu["absentSessions"],  # 缺勤次数
                        }
                    )
        repeated = course_service.get_repeated_missing_students(
            course_id=(
                current_module if current_module else None
            ),  # 选中某 module 就只看这一门，不选就看所有
            programme_id=current_programme if current_programme else None,
            start_week=start_week,
            end_week=end_week,
            min_offending_modules=2,  # 至少在 2 门课有未交
        )

        submission_risk_students = []
        for stu in repeated.get("students", []):
            submission_risk_students.append(
                {
                    "student_id": stu["studentId"],
                    "name": stu["name"],
                    "email": stu["email"],
                    "offending_module_count": stu["offendingModuleCount"],
                    # details 里是一个列表：每门课具体哪次作业没交
                    # 我们先原样传到前端，Jinja 里再展开
                    "details": stu.get("details", []),
                }
            )

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
        weeks_for_chart=weeks_for_chart,  # 如果你想区分，可以改前端变量名
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

    # ========== students ==========
    if data_type == "students":
        total = count_students()
        raw_rows = get_all_students(limit=per_page, offset=offset)
        rows = enrich_student_programme(raw_rows, programme_map)

    # ========== wellbeing ==========
    elif data_type == "wellbeing":
        total = count_wellbeing()
        rows = get_wellbeing_page(limit=per_page, offset=offset)

    # ========== attendance ==========
    elif data_type == "attendance":
        headers = ["Student ID", "Module Code", "Week", "Status"]

        total = count_attendance()  # ✅ 总数
        rows = get_attendance_page(limit=per_page, offset=offset)  # ✅ 分页

    # ========== submissions ==========
    elif data_type == "submissions":
        headers = ["Student ID", "Module Code", "Submitted", "Grade"]

        total = count_submission()  # ✅ 总数
        rows = get_submission_page(limit=per_page, offset=offset)  # ✅ 分页

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
