# src/wellbeing_system/ui/app.py
from flask import Flask, render_template, request, redirect, url_for, flash
from student_wellbeing_monitor.services.upload_service import import_csv_by_type
from student_wellbeing_monitor.database import read
import os
import math

app = Flask(
    __name__,
    template_folder="templates",  #  ui/templates
    static_folder="static",  #  ui/static
)
app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET_KEY", "dev-secret-key")


# -------- 1. entrance: select role --------
@app.route("/")
def index():
    """
    首页：让用户选择角色（Wellbeing Officer / Course Director）
    """
    return render_template("index.html")


# -------- 2. Dashboard：based on roles --------
@app.route("/dashboard/<role>")
@app.route("/dashboard/<role>")
def dashboard(role):
    # 简单 role 校验
    if role not in ("wellbeing", "course_leader"):
        return redirect(url_for("index"))

    # 1. 读取筛选参数（week / module_code），支持 ?week=3&module_code=WG1F6
    week = request.args.get("week", type=int) or 1
    module_code = request.args.get("module_code", default="")

    # 2. 先给一些假数据 / 占位数据，保证模板里的变量都有
    weeks = list(range(1, 13))  # week 1–12

    # 这里先写死两个 module，后面可以从数据库读
    modules = [
        {"code": "WG1F6", "name": "AI Fundamentals"},
        {"code": "CS2A4", "name": "Python Programming"},
    ]

    # 统计摘要（后面可以用你写的分析函数算出来）
    summary = {
        "avg_sleep": 7.1,
        "avg_stress": 3.2,
        "response_count": 38,
        "response_rate": 76,
    }

    # 3. 渲染模板时，把这些变量都传进去
    return render_template(
        "dashboard.html",
        role=role,
        weeks=weeks,
        current_week=week,
        modules=modules,
        current_module=module_code,
        summary=summary,
        # 先用占位图，后面换成真正的折线图 PNG 路径
        trend_chart_path="images/placeholder_trend.png",
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


# -------- 3. 查看数据表 --------
@app.route("/data/<role>", defaults={"data_type": "students"})
@app.route("/data/<role>/<data_type>")
def view_data(role, data_type):
    page = request.args.get("page", default=1, type=int)
    if page < 1:
        page = 1

    per_page = 20
    offset = (page - 1) * per_page
    total = 0

    if data_type == "students":
        headers = ["Student ID", "Name", "Email"]
        rows = read.get_all_students()

    elif data_type == "wellbeing":
        headers = ["Student ID", "Week", "Stress Level", "Hours Slept"]
        total = read.count_wellbeing()
        rows = read.get_wellbeing_page(limit=per_page, offset=offset)

    # TODO
    elif data_type == "attendance":
        headers = ["Student ID", "Module Code", "Week", "Status"]
        rows = read.get_all_attendance()

    elif data_type == "submissions":
        headers = ["Student ID", "Module Code", "Submitted", "Grade"]
        rows = read.get_all_submissions()

    else:
        flash("Unknown data type", "danger")
        return redirect(url_for("dashboard", role=role))

    total_pages = max(1, math.ceil(total / per_page))

    # 防止 page 超出范围
    if page > total_pages:
        page = total_pages

    return render_template(
        "data_table.html",
        role=role,
        data_type=data_type,
        headers=headers,
        rows=rows,
        page=page,
        total_pages=total_pages,
        active_page="data",
    )


# -------- 4. 查看图表 --------
@app.route("/charts/<role>")
def view_charts(role):
    """
    显示图表页面（先假设 static/charts 下有两个 png）
    """
    chart_files = [
        "attendance_overview.png",
        "stress_trend.png",
    ]
    return render_template(
        "charts.html",
        role=role,
        charts=chart_files,
        active_page="charts",
    )


# -------- 5. 编辑 / 删除（先放空实现，后面再接 DB） --------
@app.route("/students/edit/<int:student_id>", methods=["GET", "POST"])
def edit_student(student_id):
    """
    GET  -> 渲染编辑表单页面
    POST -> 保存修改后，跳回 data 表页面
    """
    if request.method == "POST":
        # TODO: 从 request.form 拿数据，更新数据库
        # 然后重定向到列表页
        role = request.args.get("role", "wellbeing")  # 你可以自己约定
        return redirect(url_for("view_data", role=role))

    # GET：先用假数据填表单，后面换成从 DB 读取
    dummy_student = {
        "student_id": student_id,
        "name": "Demo Name",
        "email": "demo@warwick.ac.uk",
        "cohort": "A",
    }
    return render_template("edit_student.html", student=dummy_student)


@app.route("/students/delete/<int:student_id>")
def delete_student(student_id):
    """
    删除学生后，跳回列表
    """
    # TODO: 在这里调用 DB 层：删除学生记录
    role = request.args.get("role", "wellbeing")
    # 删除完成后重定向回列表页
    return redirect(url_for("view_data", role=role))


def run_app():
    # 你 pyproject.toml 里 wellbeing-web 脚本会调用这个
    app.run(debug=True)


if __name__ == "__main__":
    run_app()
