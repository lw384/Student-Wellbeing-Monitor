import pandas as pd
import numpy as np
from scipy import stats # 用于线性回归
from typing import Dict, Any
import sys
import os

# 添加项目路径以支持导入
current_dir = os.path.dirname(os.path.abspath(__file__))
database_dir = os.path.join(current_dir, '..', 'database')
sys.path.insert(0, database_dir)

from db import (
    get_all_wellbeing_data,
    get_attendance_by_student,
    get_attendance_rate,
    get_conn
)

class AnalyticsService:
    def __init__(self):
        """初始化分析服务，直接使用 db.py 的方法"""
        pass
    
    def _get_students_by_course(self, course_id: str = None):
        """获取指定课程的学生ID列表"""
        if course_id is None:
            # 获取所有学生
            conn = get_conn()
            cur = conn.cursor()
            cur.execute("SELECT student_id FROM students")
            student_ids = [row[0] for row in cur.fetchall()]
            conn.close()
            return student_ids
        else:
            # 获取指定课程的学生
            conn = get_conn()
            cur = conn.cursor()
            cur.execute("SELECT student_id FROM students WHERE course_id = ?", (course_id,))
            student_ids = [row[0] for row in cur.fetchall()]
            conn.close()
            return student_ids
    
    def _filter_by_course(self, data_list, course_id: str = None):
        """按课程ID过滤数据"""
        if course_id is None:
            return data_list
        
        student_ids = set(self._get_students_by_course(course_id))
        return [item for item in data_list if item.get('student_id') in student_ids]

    def get_weekly_overview(self, course_id: str = None) -> Dict[str, Any]:
        """
        FR-3: 获取周报总览数据
        返回用于绘制折线图的数据 (x, y) 和用于显示的表格数据
        """
        # 1. 从 DB 获取原始数据
        raw_data = get_all_wellbeing_data()
        
        # 按课程过滤
        if course_id is not None:
            raw_data = self._filter_by_course(raw_data, course_id)
        
        df = pd.DataFrame(raw_data)

        if df.empty:
            return {"error": "No data available"}

        # 2. 计算每周平均值
        # 聚合：按周分组，计算压力和睡眠的平均值，以及回复数量
        weekly_stats = df.groupby('week_num').agg({
            'stress_level': 'mean',
            'sleep_hours': 'mean',
            'student_id': 'count'  # 用来计算回复率
        }).reset_index()

        # 获取总学生数来计算完成率
        total_students = len(self._get_students_by_course(course_id))
        if total_students > 0:
            weekly_stats['response_rate'] = (weekly_stats['student_id'] / total_students * 100).round(2)
        else:
            weekly_stats['response_rate'] = 0
        
        # 3. 准备输出数据
        
        # 阈值设定
        STRESS_THRESHOLD = 3.5  # 假设超过 3.5 算高压力
        
        # 准备 High Stress Points (用于图表高亮)
        high_stress_weeks = weekly_stats[weekly_stats['stress_level'] > STRESS_THRESHOLD]['week_num'].tolist()

        result = {
            "chart_data": {
                "x_axis": weekly_stats['week_num'].tolist(),
                "y_stress": weekly_stats['stress_level'].round(2).tolist(),
                "y_sleep": weekly_stats['sleep_hours'].round(2).tolist(),
                "y_response_rate": weekly_stats['response_rate'].tolist(),
                "highlight_weeks": high_stress_weeks  # 前端绘图时，这些周的点标红
            },
            "table_data": weekly_stats.to_dict('records') # 返回字典列表供表格展示
        }
        return result

    def get_stress_vs_attendance(self, course_id: str = None) -> Dict[str, Any]:
        """
        FR-6: 压力水平 vs 出勤率 对比趋势
        """
        # 获取wellbeing数据
        wellbeing_data = get_all_wellbeing_data()
        if course_id is not None:
            wellbeing_data = self._filter_by_course(wellbeing_data, course_id)
        surveys = pd.DataFrame(wellbeing_data)

        # 直接查询数据库获取出勤数据
        conn = get_conn()
        if course_id is None:
            cur = conn.cursor()
            cur.execute("""
                SELECT a.student_id, a.week, a.attended
                FROM attendance a
            """)
        else:
            cur = conn.cursor()
            cur.execute("""
                SELECT a.student_id, a.week, a.attended
                FROM attendance a
                JOIN students s ON a.student_id = s.student_id
                WHERE s.course_id = ?
            """, (course_id,))
        
        attendance_rows = cur.fetchall()
        conn.close()
        
        attendance_records = []
        for sid, week, attended in attendance_rows:
            attendance_records.append({
                'student_id': sid,
                'week_num': week,
                'attended': attended
            })
        attendance = pd.DataFrame(attendance_records)

        if surveys.empty or attendance.empty:
            return {}

        # 按周聚合
        stress_weekly = surveys.groupby('week_num')['stress_level'].mean()
        
        # attended 字段已经是 0 或 1，直接使用
        attendance_weekly = attendance.groupby('week_num')['attended'].mean() * 100

        # 合并索引 (确保周数对齐)
        combined = pd.DataFrame({'stress': stress_weekly, 'attendance': attendance_weekly}).dropna()

        return {
            "x_axis": combined.index.tolist(),
            "y_stress": combined['stress'].tolist(),
            "y_attendance": combined['attendance'].tolist()
        }

    def get_submission_stats(self, course_id: str = None) -> Dict[str, Any]:
        """
        FR-8: 作业提交情况饼图数据
        注意：当前数据库中没有 submissions 表，此方法返回空结果
        """
        # 由于数据库中没有 submissions 表，返回空结果
        # 如果需要实现此功能，需要先创建 submissions 表
        return {
            "labels": [],
            "values": []
        }

    def get_performance_correlation(self, course_id: str = None) -> Dict[str, Any]:
        """
        FR-11: 出勤率 vs 成绩 线性回归
        Output: 散点图数据 (Points) + 拟合线数据 (Line)
        """
        # 直接查询数据库获取出勤率和成绩数据
        conn = get_conn()
        if course_id is None:
            cur = conn.cursor()
            cur.execute("""
                SELECT 
                    a.student_id,
                    AVG(a.attended) AS attendance_rate,
                    g.final_grade AS grade
                FROM attendance a
                JOIN grades g ON a.student_id = g.student_id
                GROUP BY a.student_id, g.final_grade
            """)
        else:
            cur = conn.cursor()
            cur.execute("""
                SELECT 
                    a.student_id,
                    AVG(a.attended) AS attendance_rate,
                    g.final_grade AS grade
                FROM attendance a
                JOIN grades g ON a.student_id = g.student_id
                JOIN students s ON a.student_id = s.student_id
                WHERE s.course_id = ?
                GROUP BY a.student_id, g.final_grade
            """, (course_id,))
        
        data = cur.fetchall()
        conn.close()
        
        # 转换为 DataFrame
        df = pd.DataFrame(data, columns=['student_id', 'attendance', 'grade'])
        df['attendance'] = df['attendance'] * 100  # 转换为百分比
        df = df[['attendance', 'grade']].dropna()

        if len(df) < 2:
            return {"error": "Not enough data for correlation"}

        # 线性回归分析
        slope, intercept, r_value, p_value, std_err = stats.linregress(df['attendance'], df['grade'])

        # 生成拟合线数据 (两个点即可确定直线: x_min 和 x_max)
        x_line = [df['attendance'].min(), df['attendance'].max()]
        y_line = [slope * x + intercept for x in x_line]

        return {
            "scatter_points": {
                "x": df['attendance'].tolist(), # 出勤率
                "y": df['grade'].tolist()       # 成绩
            },
            "regression_line": {
                "x": x_line,
                "y": y_line,
                "equation": f"y = {slope:.2f}x + {intercept:.2f}",
                "r_squared": r_value**2
            }
        }


# ==================== Test Code ====================
if __name__ == "__main__":
    print("=" * 60)
    print("AnalyticsService Test")
    print("=" * 60)
    
    # Create service instance
    service = AnalyticsService()
    
    # Test 1: Get weekly overview for all courses
    print("\n[Test 1] Get weekly overview for all courses")
    print("-" * 60)
    result1 = service.get_weekly_overview()
    if "error" in result1:
        print(f"Error: {result1['error']}")
    else:
        print(f"Weeks: {result1['chart_data']['x_axis']}")
        print(f"Stress levels: {result1['chart_data']['y_stress']}")
        print(f"Sleep hours: {result1['chart_data']['y_sleep']}")
        print(f"High stress weeks: {result1['chart_data']['highlight_weeks']}")
        print(f"Table data rows: {len(result1['table_data'])}")
    
    # Test 2: Get weekly overview for specific course
    print("\n[Test 2] Get weekly overview for course WM9AA0")
    print("-" * 60)
    result2 = service.get_weekly_overview(course_id="WM9AA0")
    if "error" in result2:
        print(f"Error: {result2['error']}")
    else:
        print(f"Weeks: {result2['chart_data']['x_axis']}")
        print(f"Stress levels: {result2['chart_data']['y_stress']}")
        print(f"Sleep hours: {result2['chart_data']['y_sleep']}")
        print(f"Response rates: {result2['chart_data']['y_response_rate']}")
    
    # Test 3: Stress vs Attendance comparison
    print("\n[Test 3] Stress level vs Attendance rate comparison")
    print("-" * 60)
    result3 = service.get_stress_vs_attendance(course_id="WM9AA0")
    if result3:
        print(f"Weeks: {result3['x_axis']}")
        print(f"Stress levels: {[round(x, 2) for x in result3['y_stress']]}")
        print(f"Attendance rates: {[round(x, 2) for x in result3['y_attendance']]}")
    else:
        print("No data")
    
    # Test 4: Attendance vs Grade correlation
    print("\n[Test 4] Attendance rate vs Grade linear regression")
    print("-" * 60)
    result4 = service.get_performance_correlation(course_id="WM9AA0")
    if "error" in result4:
        print(f"Error: {result4['error']}")
    else:
        print(f"Scatter points count: {len(result4['scatter_points']['x'])}")
        print(f"Regression equation: {result4['regression_line']['equation']}")
        print(f"R-squared value: {result4['regression_line']['r_squared']:.4f}")
        print(f"Regression line X: {result4['regression_line']['x']}")
        print(f"Regression line Y: {[round(y, 2) for y in result4['regression_line']['y']]}")
    
    # Test 5: Submission statistics
    print("\n[Test 5] Submission statistics")
    print("-" * 60)
    result5 = service.get_submission_stats(course_id="WM9AA0")
    print(f"Labels: {result5['labels']}")
    print(f"Values: {result5['values']}")
    
    # Test 6: Get student list
    print("\n[Test 6] Get student list for course")
    print("-" * 60)
    students = service._get_students_by_course("WM9AA0")
    print(f"Course WM9AA0 student count: {len(students)}")
    if students:
        print(f"First 5 student IDs: {students[:5]}")
    
    print("\n" + "=" * 60)
    print("Test completed!")
    print("=" * 60)