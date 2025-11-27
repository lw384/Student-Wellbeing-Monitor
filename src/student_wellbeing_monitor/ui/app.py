# src/wellbeing_system/ui/app.py
from flask import Flask, render_template, request, redirect, url_for, flash
from student_wellbeing_monitor.services.upload_service import import_csv_by_type
import os

app = Flask(
    __name__,
    template_folder="templates",  #  ui/templates
    static_folder="static",  #  ui/static
)
app.config["SECRET_KEY"] = os.environ.get(
    "FLASK_SECRET_KEY", "dev-secret-key-change-me"
)


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
    """
    /dashboard/wellbeing
    /dashboard/course_leader
    """
    if role not in ("wellbeing", "course_leader"):
        # illegal role，return back
        return redirect(url_for("index"))

    return render_template(
        "dashboard.html",
        role=role,
        active_page="dashboard",
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
@app.route("/data/<role>")
def view_data(role):
    """
    显示一张数据表（先用假数据，后面再接数据库）
    URL: /data/wellbeing 或 /data/course_leader
    """
    # 示例假数据（row[0], row[1] 格式方便你之前的 data_table.html 使用）
    rows = [
        (5000001, "Alice Smith", "alice.01@warwick.ac.uk", "A"),
        (5000002, "Bob Lee", "bob.02@warwick.ac.uk", "B"),
    ]

    return render_template(
        "data_table.html",
        role=role,
        rows=rows,
        page=1,
        total_pages=1,
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
