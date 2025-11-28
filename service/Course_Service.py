import pandas as pd
from typing import List, Dict, Any
import sys
import os

# Add project path to support imports
current_dir = os.path.dirname(os.path.abspath(__file__))
database_dir = os.path.join(current_dir, '..', 'database')
project_root = os.path.abspath(os.path.join(current_dir, '..', '..'))
sys.path.insert(0, database_dir)

from db import get_conn
import db

# Ensure database path is correct (relative to project root)
# DB_PATH in db.py is "data/student.db", needs to run from project root
if os.path.exists(project_root):
    # Update database path to absolute path
    db_path_abs = os.path.join(project_root, "data", "student.db")
    if os.path.exists(db_path_abs):
        db.DB_PATH = db_path_abs

class CourseService:
    def __init__(self, attendance_repo=None, student_repo=None):
        # Keep repository parameters for backward compatibility, but no longer required
        self.attendance_repo = attendance_repo
        self.student_repo = student_repo

    def get_course_attendance_trends(self, course_id: int) -> Dict[str, Any]:
        """
        FR-7 & FR-9: Course attendance trends and absence list
        """
        # 1. Get data directly from database
        conn = get_conn()
        cur = conn.cursor()
        
        # Get attendance data for all students in this course
        # Note: Database uses attended field (INTEGER: 0=absent, 1=present)
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
        
        # Convert to list of dictionaries
        raw_data = []
        for row in rows:
            raw_data.append({
                'student_id': row[0],
                'week_num': row[1],
                'attended': row[2]  # 0 or 1
            })
        
        df = pd.DataFrame(raw_data)
        
        if df.empty:
            return {"error": "No attendance data"}

        # 2. Calculate weekly attendance rate (FR-7)
        # attended: 1=present, 0=absent
        df['is_present'] = df['attended']
        
        weekly_trends = df.groupby('week_num')['is_present'].mean() * 100
        
        # 3. Identify absent students (FR-9)
        # Logic: consecutive absences >= 2 times OR total attendance rate < 50%
        flagged_students = []
        
        # Get all students for this course directly from database
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

            # Check total attendance rate
            total_rate = s_records['is_present'].mean()
            
            # Check consecutive absences
            # attended: 1=present, 0=absent
            attended_list = s_records['attended'].tolist()
            consecutive_absent = 0
            max_consecutive = 0
            for attended in attended_list:
                if attended == 0:  # absent
                    consecutive_absent += 1
                else:  # present
                    max_consecutive = max(max_consecutive, consecutive_absent)
                    consecutive_absent = 0
            max_consecutive = max(max_consecutive, consecutive_absent)  # Check last segment

            reason = []
            if total_rate < 0.5: # 50% threshold
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


# ==================== Test Code ====================
if __name__ == "__main__":
    # Ensure database path is correctly set (already set at the beginning of the file)
    db_path_check = db.DB_PATH
    
    print("=" * 60)
    print("CourseService Functionality Test")
    print("=" * 60)
    print(f"Project root directory: {project_root}")
    print(f"Database file path: {db_path_check}")
    print(f"Database file exists: {os.path.exists(db_path_check)}")
    print("=" * 60)
    
    try:
        # Create service instance
        service = CourseService()
        
        # Check if there is course data in the database
        conn = get_conn()
        cur = conn.cursor()
        
        # Check if there are any courses
        cur.execute("SELECT course_id, course_name FROM courses LIMIT 5")
        courses = cur.fetchall()
        conn.close()
        
        if not courses:
            print("\nNo course data in database!")
            print("Please run the following scripts to generate test data:")
            print("  1. python src/database/1_create_database.py")
            print("  2. python src/database/2_generate_data.py")
        else:
            print(f"\nFound {len(courses)} courses")
            print("\nAvailable course list:")
            for course_id, course_name in courses:
                print(f"  - {course_id}: {course_name}")
            
            # Test all courses
            print("\n" + "=" * 60)
            print("Starting to test all courses...")
            print("=" * 60)
            
            for idx, (course_id, course_name) in enumerate(courses, 1):
                print(f"\n[Test {idx}/{len(courses)}] Course: {course_id} - {course_name}")
                print("-" * 60)
                
                try:
                    # Call service method
                    result = service.get_course_attendance_trends(course_id)
                    
                    # Check if there is an error
                    if "error" in result:
                        print(f"Warning: {result['error']}")
                        continue
                    
                    # Print results
                    print(f"Course ID: {result['course_id']}")
                    
                    # Print chart data
                    chart_data = result['chart_data']
                    print(f"\nWeekly attendance trend data:")
                    print(f"  Week numbers (x_axis): {chart_data['x_axis']}")
                    print(f"  Attendance rate % (y_axis): {[round(x, 2) for x in chart_data['y_axis']]}")
                    
                    # Print flagged students
                    flagged = result['flagged_students']
                    print(f"\nFlagged absent students (total {len(flagged)}):")
                    if flagged:
                        for i, student in enumerate(flagged, 1):
                            print(f"  {i}. {student['name']} (ID: {student['id']})")
                            print(f"     Reason: {student['reason']}")
                    else:
                        print("  (None)")
                    
                    # Validate data format
                    print(f"\nData validation:")
                    print(f"  - Number of weeks in chart data: {len(chart_data['x_axis'])}")
                    print(f"  - Number of attendance rates in chart data: {len(chart_data['y_axis'])}")
                    print(f"  - Week numbers match attendance rates: {len(chart_data['x_axis']) == len(chart_data['y_axis'])}")
                    
                    # Validate attendance rate range
                    if chart_data['y_axis']:
                        min_rate = min(chart_data['y_axis'])
                        max_rate = max(chart_data['y_axis'])
                        avg_rate = sum(chart_data['y_axis']) / len(chart_data['y_axis'])
                        print(f"  - Attendance rate range: {min_rate:.2f}% - {max_rate:.2f}%")
                        print(f"  - Average attendance rate: {avg_rate:.2f}%")
                        print(f"  - Attendance rates within valid range (0-100): {0 <= min_rate <= 100 and 0 <= max_rate <= 100}")
                    
                    print(f"\nTest {idx} passed!")
                    
                except Exception as e:
                    print(f"\nTest {idx} failed: {str(e)}")
                    import traceback
                    traceback.print_exc()
            
            print("\n" + "=" * 60)
            print("All tests completed!")
            print("=" * 60)
            
    except Exception as e:
        print(f"\nInitialization test failed: {str(e)}")
        import traceback
        traceback.print_exc()