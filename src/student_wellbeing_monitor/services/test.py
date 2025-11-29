from wellbeing_service import WellbeingService

# 你本地 student.db 里的课程，例如：
# WM9AA0, WM9YJ0, WM9A1, WM9CD0, WM96X
# 可以任选一个当 moduleCode 测试

if __name__ == "__main__":
    # 创建服务实例
    service = WellbeingService()

    # 1) 仪表盘概览 - 所有课程
    print("=== Dashboard (all modules, week 1-5) ===")
    print(service.get_dashboard_summary(1, 5, None))

    # 2) 仪表盘概览 - 指定课程
    print("\n=== Dashboard (course WM9AA0, week 1-5) ===")
    print(service.get_dashboard_summary(1, 5, "WM9AA0"))

    # 3) 压力 & 睡眠趋势 - 所有课程
    print("\n=== Stress & Sleep Trend (all modules, week 1-5) ===")
    print(service.get_stress_sleep_trend(1, 5, None))

    # 4) 压力 & 睡眠趋势 - 指定课程
    print("\n=== Stress & Sleep Trend (course WM9AA0, week 1-5) ===")
    print(service.get_stress_sleep_trend(1, 5, "WM9AA0"))

    # 5) 模块出勤率（所有模块）
    print("\n=== Attendance by Module (week 1-5) ===")
    print(service.get_attendance_by_module(1, 5))

    # 6) 风险学生（所有课程）
    print("\n=== Risk Students (all modules, week 1-5) ===")
    print(service.get_risk_students(1, 5, None))

    # 7) 风险学生（某课程）
    print("\n=== Risk Students (course WM9AA0, week 1-5) ===")
    print(service.get_risk_students(1, 5, "WM9AA0"))

    # 8) 风险学生（指定学生ID - 所有课程）
    print("\n=== Risk Students (student_id=U222200006, all modules, week 1-5) ===")
    print(service.get_risk_students(1, 5, None, student_id="U222200006"))

    # 9) 风险学生（指定学生ID - 指定课程）
    print("\n=== Risk Students (student_id=U222200006, course WM9AA0, week 1-5) ===")
    print(service.get_risk_students(1, 5, "WM9AA0", student_id="U222200006"))

    # 10) 风险学生（指定学生ID - 不存在的学生）
    print("\n=== Risk Students (student_id=9999999, all modules, week 1-5) ===")
    print(service.get_risk_students(1, 5, None, student_id="9999999"))