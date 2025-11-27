import pandas as pd
from typing import List, Dict, Any
import sys
import os

# 添加项目路径以支持导入
current_dir = os.path.dirname(os.path.abspath(__file__))
database_dir = os.path.join(current_dir, '..', 'database')
project_root = os.path.abspath(os.path.join(current_dir, '..', '..'))
sys.path.insert(0, database_dir)

from db import get_conn
import db

# 确保数据库路径正确（相对于项目根目录）
# db.py 中的 DB_PATH 是 "data/student.db"，需要从项目根目录运行
if os.path.exists(project_root):
    # 更新数据库路径为绝对路径
    db_path_abs = os.path.join(project_root, "data", "student.db")
    if os.path.exists(db_path_abs):
        db.DB_PATH = db_path_abs

class CourseService:
    def __init__(self, attendance_repo=None, student_repo=None):
        # 保留 repository 参数以保持向后兼容，但不再必须
        self.attendance_repo = attendance_repo
        self.student_repo = student_repo

    def get_course_attendance_trends(self, course_id: int) -> Dict[str, Any]:
        """
        FR-7 & FR-9: 课程出勤趋势与缺勤名单
        """
        # 1. 从 database 直接获取数据
        conn = get_conn()
        cur = conn.cursor()
        
        # 获取该课程所有学生的出勤数据
        # 注意：数据库中使用 attended 字段（INTEGER: 0=缺席, 1=出席）
        cur.execute("""
            SELECT 
                a.student_id,
                a.week AS week_num,
                a.attended
            FROM attendance a
            JOIN students s ON a.student_id = s.student_id
            WHERE s.course_id = ?
            ORDER BY a.student_id, a.week
        """, (str(course_id),))
        
        rows = cur.fetchall()
        conn.close()
        
        # 转换为字典列表
        raw_data = []
        for row in rows:
            raw_data.append({
                'student_id': row[0],
                'week_num': row[1],
                'attended': row[2]  # 0 或 1
            })
        
        df = pd.DataFrame(raw_data)
        
        if df.empty:
            return {"error": "No attendance data"}

        # 2. 计算每周出勤率 (FR-7)
        # attended: 1=出席, 0=缺席
        df['is_present'] = df['attended']
        
        weekly_trends = df.groupby('week_num')['is_present'].mean() * 100
        
        # 3. 识别缺勤学生 (FR-9)
        # 逻辑：连续缺勤 >= 2次 或 总出勤率 < 50%
        flagged_students = []
        
        # 从 database 直接获取该课程的所有学生
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("""
            SELECT student_id, name
            FROM students
            WHERE course_id = ?
            ORDER BY student_id
        """, (str(course_id),))
        
        student_rows = cur.fetchall()
        conn.close()
        
        all_students = []
        for row in student_rows:
            all_students.append({
                'id': row[0],
                'name': row[1]
            })
        
        for student in all_students:
            s_id = student['id']
            s_records = df[df['student_id'] == s_id].sort_values('week_num')
            
            if s_records.empty:
                continue

            # 检查总出勤率
            total_rate = s_records['is_present'].mean()
            
            # 检查连续缺勤
            # attended: 1=出席, 0=缺席
            attended_list = s_records['attended'].tolist()
            consecutive_absent = 0
            max_consecutive = 0
            for attended in attended_list:
                if attended == 0:  # 缺席
                    consecutive_absent += 1
                else:  # 出席
                    max_consecutive = max(max_consecutive, consecutive_absent)
                    consecutive_absent = 0
            max_consecutive = max(max_consecutive, consecutive_absent)  # 检查最后一段

            reason = []
            if total_rate < 0.5: # 50% 阈值
                reason.append(f"Low overall attendance ({total_rate:.0%})")
            if max_consecutive >= 2:
                reason.append(f"Consecutive absence ({max_consecutive} weeks)")
            
            if reason:
                flagged_students.append({
                    "id": s_id,
                    "name": student['name'],
                    "reason": ", ".join(reason)
                })

        return {
            "course_id": course_id,
            "chart_data": {
                "x_axis": weekly_trends.index.tolist(),
                "y_axis": weekly_trends.values.round(2).tolist()
            },
            "flagged_students": flagged_students
        }


# ==================== 测试代码 ====================
if __name__ == "__main__":
    # 确保数据库路径已正确设置（已在文件开头设置）
    db_path_check = db.DB_PATH
    
    print("=" * 60)
    print("CourseService 功能测试")
    print("=" * 60)
    print(f"项目根目录: {project_root}")
    print(f"数据库文件路径: {db_path_check}")
    print(f"数据库文件存在: {os.path.exists(db_path_check)}")
    print("=" * 60)
    
    try:
        # 创建服务实例
        service = CourseService()
        
        # 检查数据库中是否有课程数据
        conn = get_conn()
        cur = conn.cursor()
        
        # 检查是否有课程
        cur.execute("SELECT course_id, course_name FROM courses LIMIT 5")
        courses = cur.fetchall()
        conn.close()
        
        if not courses:
            print("\n❌ 数据库中没有课程数据！")
            print("请先运行以下脚本生成测试数据：")
            print("  1. python src/database/1_create_database.py")
            print("  2. python src/database/2_generate_data.py")
        else:
            print(f"\n✅ 找到 {len(courses)} 个课程")
            print("\n可用课程列表：")
            for course_id, course_name in courses:
                print(f"  - {course_id}: {course_name}")
            
            # 测试所有课程
            print("\n" + "=" * 60)
            print("开始测试所有课程...")
            print("=" * 60)
            
            for idx, (course_id, course_name) in enumerate(courses, 1):
                print(f"\n【测试 {idx}/{len(courses)}】课程: {course_id} - {course_name}")
                print("-" * 60)
                
                try:
                    # 调用服务方法
                    result = service.get_course_attendance_trends(course_id)
                    
                    # 检查是否有错误
                    if "error" in result:
                        print(f"⚠️  警告: {result['error']}")
                        continue
                    
                    # 打印结果
                    print(f"✅ 课程ID: {result['course_id']}")
                    
                    # 打印图表数据
                    chart_data = result['chart_data']
                    print(f"\n📈 每周出勤趋势数据:")
                    print(f"  周数 (x_axis): {chart_data['x_axis']}")
                    print(f"  出勤率% (y_axis): {[round(x, 2) for x in chart_data['y_axis']]}")
                    
                    # 打印标记的学生
                    flagged = result['flagged_students']
                    print(f"\n⚠️  标记的缺勤学生 (共 {len(flagged)} 人):")
                    if flagged:
                        for i, student in enumerate(flagged, 1):
                            print(f"  {i}. {student['name']} (ID: {student['id']})")
                            print(f"     原因: {student['reason']}")
                    else:
                        print("  (无)")
                    
                    # 验证数据格式
                    print(f"\n✅ 数据验证:")
                    print(f"  - 图表数据周数数量: {len(chart_data['x_axis'])}")
                    print(f"  - 图表数据出勤率数量: {len(chart_data['y_axis'])}")
                    print(f"  - 周数与出勤率数量匹配: {len(chart_data['x_axis']) == len(chart_data['y_axis'])}")
                    
                    # 验证出勤率范围
                    if chart_data['y_axis']:
                        min_rate = min(chart_data['y_axis'])
                        max_rate = max(chart_data['y_axis'])
                        avg_rate = sum(chart_data['y_axis']) / len(chart_data['y_axis'])
                        print(f"  - 出勤率范围: {min_rate:.2f}% - {max_rate:.2f}%")
                        print(f"  - 平均出勤率: {avg_rate:.2f}%")
                        print(f"  - 出勤率在有效范围内 (0-100): {0 <= min_rate <= 100 and 0 <= max_rate <= 100}")
                    
                    print(f"\n✅ 测试 {idx} 通过！")
                    
                except Exception as e:
                    print(f"\n❌ 测试 {idx} 失败: {str(e)}")
                    import traceback
                    traceback.print_exc()
            
            print("\n" + "=" * 60)
            print("✅ 所有测试完成！")
            print("=" * 60)
            
    except Exception as e:
        print(f"\n❌ 初始化测试失败: {str(e)}")
        import traceback
        traceback.print_exc()