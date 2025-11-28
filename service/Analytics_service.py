import pandas as pd
import numpy as np
from scipy import stats # For linear regression
from typing import Dict, Any
import sys
import os

# Add project path to support imports
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
        """Initialize analytics service, directly using methods from db.py"""
        pass
    
    def _get_students_by_course(self, course_id: str = None):
        """Get list of student IDs for specified course"""
        if course_id is None:
            # Get all students
            conn = get_conn()
            cur = conn.cursor()
            cur.execute("SELECT student_id FROM students")
            student_ids = [row[0] for row in cur.fetchall()]
            conn.close()
            return student_ids
        else:
            # Get students for specified course
            conn = get_conn()
            cur = conn.cursor()
            cur.execute("SELECT student_id FROM students WHERE course_id = ?", (course_id,))
            student_ids = [row[0] for row in cur.fetchall()]
            conn.close()
            return student_ids
    
    def _filter_by_course(self, data_list, course_id: str = None):
        """Filter data by course ID"""
        if course_id is None:
            return data_list
        
        student_ids = set(self._get_students_by_course(course_id))
        return [item for item in data_list if item.get('student_id') in student_ids]

    def get_weekly_overview(self, course_id: str = None) -> Dict[str, Any]:
        """
        FR-3: Get weekly overview data
        Returns data for drawing line charts (x, y) and table data for display
        """
        # 1. Get raw data from DB
        raw_data = get_all_wellbeing_data()
        
        # Filter by course
        if course_id is not None:
            raw_data = self._filter_by_course(raw_data, course_id)
        
        df = pd.DataFrame(raw_data)

        if df.empty:
            return {"error": "No data available"}

        # 2. Calculate weekly averages
        # Aggregate: group by week, calculate averages of stress and sleep, and response count
        weekly_stats = df.groupby('week_num').agg({
            'stress_level': 'mean',
            'sleep_hours': 'mean',
            'student_id': 'count'  # Used to calculate response rate
        }).reset_index()

        # Get total number of students to calculate completion rate
        total_students = len(self._get_students_by_course(course_id))
        if total_students > 0:
            weekly_stats['response_rate'] = (weekly_stats['student_id'] / total_students * 100).round(2)
        else:
            weekly_stats['response_rate'] = 0
        
        # 3. Prepare output data
        
        # Set threshold
        STRESS_THRESHOLD = 3.5  # Assume above 3.5 is considered high stress
        
        # Prepare High Stress Points (for chart highlighting)
        high_stress_weeks = weekly_stats[weekly_stats['stress_level'] > STRESS_THRESHOLD]['week_num'].tolist()

        result = {
            "chart_data": {
                "x_axis": weekly_stats['week_num'].tolist(),
                "y_stress": weekly_stats['stress_level'].round(2).tolist(),
                "y_sleep": weekly_stats['sleep_hours'].round(2).tolist(),
                "y_response_rate": weekly_stats['response_rate'].tolist(),
                "highlight_weeks": high_stress_weeks  # Frontend will mark these weeks' points in red when drawing
            },
            "table_data": weekly_stats.to_dict('records') # Return list of dictionaries for table display
        }
        return result

    def get_stress_vs_attendance(self, course_id: str = None) -> Dict[str, Any]:
        """
        FR-6: Stress level vs Attendance rate comparison trend
        """
        # Get wellbeing data
        wellbeing_data = get_all_wellbeing_data()
        if course_id is not None:
            wellbeing_data = self._filter_by_course(wellbeing_data, course_id)
        surveys = pd.DataFrame(wellbeing_data)

        # Query database directly to get attendance data
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

        # Aggregate by week
        stress_weekly = surveys.groupby('week_num')['stress_level'].mean()
        
        # attended field is already 0 or 1, use directly
        attendance_weekly = attendance.groupby('week_num')['attended'].mean() * 100

        # Merge indices (ensure week numbers are aligned)
        combined = pd.DataFrame({'stress': stress_weekly, 'attendance': attendance_weekly}).dropna()

        return {
            "x_axis": combined.index.tolist(),
            "y_stress": combined['stress'].tolist(),
            "y_attendance": combined['attendance'].tolist()
        }

    def get_submission_stats(self, course_id: str = None) -> Dict[str, Any]:
        """
        FR-8: Assignment submission statistics pie chart data
        Note: Currently there is no submissions table in the database, this method returns empty result
        """
        # Since there is no submissions table in the database, return empty result
        # If this functionality is needed, create the submissions table first
        return {
            "labels": [],
            "values": []
        }

    def get_performance_correlation(self, course_id: str = None) -> Dict[str, Any]:
        """
        FR-11: Attendance rate vs Grade linear regression
        Output: Scatter plot data (Points) + Fitted line data (Line)
        """
        # Query database directly to get attendance rate and grade data
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
        
        # Convert to DataFrame
        df = pd.DataFrame(data, columns=['student_id', 'attendance', 'grade'])
        df['attendance'] = df['attendance'] * 100  # Convert to percentage
        df = df[['attendance', 'grade']].dropna()

        if len(df) < 2:
            return {"error": "Not enough data for correlation"}

        # Linear regression analysis
        slope, intercept, r_value, p_value, std_err = stats.linregress(df['attendance'], df['grade'])

        # Generate fitted line data (two points are sufficient to determine a line: x_min and x_max)
        x_line = [df['attendance'].min(), df['attendance'].max()]
        y_line = [slope * x + intercept for x in x_line]

        return {
            "scatter_points": {
                "x": df['attendance'].tolist(), # Attendance rate
                "y": df['grade'].tolist()       # Grade
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