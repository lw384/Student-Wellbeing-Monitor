import pandas as pd
from typing import List, Dict, Any, Tuple
import sys
import os

# Add database directory to path
database_path = os.path.join(os.path.dirname(__file__), '..', 'database')
sys.path.insert(0, os.path.abspath(database_path))
from db import get_all_students, get_wellbeing_by_student, get_conn


def get_all_wellbeing_data():
    """
    Helper function: Get all wellbeing survey data
    Since this function doesn't exist in db.py, we implement it here
    """
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT student_id, week, stress_level, hours_slept "
        "FROM wellbeing ORDER BY student_id, week"
    )
    rows = cur.fetchall()
    conn.close()
    # Convert to list of dictionaries format
    return [
        {
            'student_id': row[0],
            'week_num': row[1],
            'stress_level': row[2],
            'sleep_hours': row[3]
        }
        for row in rows
    ]


class WellbeingService:
    def __init__(self):
        # No longer need repository, directly use db.py interface
        pass

    def get_at_risk_students(self) -> Dict[str, List[Dict]]:
        """
        FR-5: Identify at-risk students (core functionality)
        """
        # Get all historical survey data
        raw_data = get_all_wellbeing_data()
        df = pd.DataFrame(raw_data)
        
        # Sort to ensure processing in chronological order
        df = df.sort_values(by=['student_id', 'week_num'])

        potential_risk_students = []
        high_risk_students = []
        
        # Get all student list to check for "missing survey" cases
        # get_all_students() returns list of tuples (student_id, name, email), need to convert to dictionary
        students_tuples = get_all_students()
        all_students = [
            {'id': s[0], 'name': s[1], 'email': s[2]} 
            for s in students_tuples
        ]
        
        # -------------------------------------------------
        # Logic A: Analyze students who have submitted data (stress & sleep)
        # -------------------------------------------------
        for student_id, group in df.groupby('student_id'):
            # Get the last week's data for this student
            if group.empty: continue
            
            last_entry = group.iloc[-1]
            prev_entries = group.iloc[:-1]
            
            # Get student detailed information
            student_info = next((s for s in all_students if s['id'] == student_id), {})
            
            # 1. Determine [Potential Risk]: Sudden change this week (stress 4-5 & sleep <=6) and previous was normal
            if last_entry['stress_level'] >= 4 and last_entry['sleep_hours'] <= 6:
                # Check if last week was normal (if last week data exists)
                if not prev_entries.empty:
                    prev_entry = prev_entries.iloc[-1]
                    if prev_entry['stress_level'] < 4:
                        potential_risk_students.append({
                            "id": student_id,
                            "name": student_info.get('name'),
                            "contact": student_info.get('email'),
                            "reason": f"Sudden stress spike (Level {last_entry['stress_level']}) this week."
                        })

            # 2. Determine [High Risk]: Consecutive 3 weeks stress >=4 and sleep <=4
            if len(group) >= 3:
                last_3_weeks = group.iloc[-3:]
                if (last_3_weeks['stress_level'] >= 4).all() and (last_3_weeks['sleep_hours'] <= 4).all():
                     high_risk_students.append({
                            "id": student_id,
                            "name": student_info.get('name'),
                            "contact": student_info.get('email'),
                            "reason": "Chronic high stress and low sleep (3+ weeks)."
                        })

        # -------------------------------------------------
        # Logic B: Analyze students who haven't submitted surveys consecutively (included in high risk)
        # -------------------------------------------------
        current_week = df['week_num'].max() if not df.empty else 0
        for student in all_students:
            s_id = student['id']
            # Find the weeks this student has submitted
            submitted_weeks = df[df['student_id'] == s_id]['week_num'].tolist()
            
            # Check if the last 3 weeks (current, current-1, current-2) are all missing
            missed_count = 0
            for w in range(current_week, current_week - 3, -1):
                if w > 0 and w not in submitted_weeks:
                    missed_count += 1
            
            if missed_count >= 3:
                high_risk_students.append({
                    "id": s_id,
                    "name": student.get('name'),
                    "contact": student.get('email'),
                    "reason": "No survey response for 3+ consecutive weeks."
                })

        return {
            "Current_Selected_Week": current_week,
            "potential_risk": potential_risk_students,
            "high_risk": high_risk_students
        }


    def get_student_health_extremes(self, student_id: int) -> Dict[str, Any]:
        """
        Function: Query the week with maximum stress and minimum sleep for a specified student
        Corresponding requirements:
        1. Which week has maximum stress (input student_id -> output week, stress)
        2. Minimum sleep (input student_id -> output week, sleep_hour)
        """
        # Get all survey data for this student
        # get_wellbeing_by_student() returns list of tuples (week, stress_level, hours_slept)
        raw_tuples = get_wellbeing_by_student(student_id)
        
        # Convert to list of dictionaries format
        raw_data = [
            {
                'student_id': student_id,
                'week_num': row[0],
                'stress_level': row[1],
                'sleep_hours': row[2]
            }
            for row in raw_tuples
        ]
        df = pd.DataFrame(raw_data)
        
        # Filter for specified student (actually already this student's data, but kept for consistency)
        student_df = df[df['student_id'] == student_id]

        if student_df.empty:
            return {"error": f"No survey data found for student {student_id}"}

        # 1. Find the week with maximum stress
        # idxmax() returns the index of maximum value, then use loc to get that row's data
        max_stress_idx = student_df['stress_level'].idxmax()
        max_stress_row = student_df.loc[max_stress_idx]

        # 2. Find the week with minimum sleep
        min_sleep_idx = student_df['sleep_hours'].idxmin()
        min_sleep_row = student_df.loc[min_sleep_idx]

        return {
            "student_id": student_id,
            "max_stress": {
                "week": int(max_stress_row['week_num']),
                "value": float(max_stress_row['stress_level']),
                "note": "Critical" if max_stress_row['stress_level'] >= 4 else "Normal"
            },
            "min_sleep": {
                "week": int(min_sleep_row['week_num']),
                "value": float(min_sleep_row['sleep_hours']),
                "note": "Critical" if min_sleep_row['sleep_hours'] <= 4 else "Normal"
            }
        }


# ==================== Test Program ====================
if __name__ == "__main__":
    import json
    
    # Adjust working directory to ensure database file can be found
    # DB_PATH in db.py is "data/student.db", relative to database directory
    original_dir = os.getcwd()
    db_dir = os.path.join(os.path.dirname(__file__), '..', 'database')
    os.chdir(os.path.abspath(db_dir))
    
    print("=" * 60)
    print("WellbeingService Test Program")
    print("=" * 60)
    print(f"Database directory: {os.path.abspath(db_dir)}")
    print(f"Database file: {os.path.join(os.path.abspath(db_dir), 'data', 'student.db')}")
    print("=" * 60)
    
    # Create service instance
    service = WellbeingService()
    
    # Test 1: Get at-risk students
    print("\n[Test 1] Get at-risk students (get_at_risk_students)")
    print("-" * 60)
    try:
        risk_result = service.get_at_risk_students()
        print(f"Current week: {risk_result['Current_Selected_Week']}")
        print(f"\nPotential risk student count: {len(risk_result['potential_risk'])}")
        if risk_result['potential_risk']:
            print("Potential risk student list:")
            for student in risk_result['potential_risk']:
                print(f"  - ID: {student['id']}, Name: {student['name']}, Reason: {student['reason']}")
        else:
            print("  No potential risk students")
        
        print(f"\nHigh risk student count: {len(risk_result['high_risk'])}")
        if risk_result['high_risk']:
            print("High risk student list:")
            for student in risk_result['high_risk']:
                print(f"  - ID: {student['id']}, Name: {student['name']}, Reason: {student['reason']}")
        else:
            print("  No high risk students")
        
        # Output complete result in JSON format (optional)
        print("\nComplete result (JSON format):")
        print(json.dumps(risk_result, indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 2: Get student health extremes
    print("\n\n[Test 2] Get student health extremes (get_student_health_extremes)")
    print("-" * 60)
    
    # First get all student IDs
    try:
        all_students = get_all_students()
        if all_students:
            # Test first 3 students
            test_student_ids = [s[0] for s in all_students[:3]]
            print(f"Test student IDs: {test_student_ids}\n")
            
            for student_id in test_student_ids:
                print(f"Student ID: {student_id}")
                try:
                    extremes = service.get_student_health_extremes(student_id)
                    if "error" in extremes:
                        print(f"  {extremes['error']}")
                    else:
                        print(f"  Max stress: Week {extremes['max_stress']['week']}, Value={extremes['max_stress']['value']}, {extremes['max_stress']['note']}")
                        print(f"  Min sleep: Week {extremes['min_sleep']['week']}, Value={extremes['min_sleep']['value']} hours, {extremes['min_sleep']['note']}")
                except Exception as e:
                    print(f"  Error: {e}")
                print()
        else:
            print("No student data in database")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 3: Data statistics
    print("\n[Test 3] Data statistics")
    print("-" * 60)
    try:
        wellbeing_data = get_all_wellbeing_data()
        students_data = get_all_students()
        print(f"Total student count: {len(students_data)}")
        print(f"Total survey record count: {len(wellbeing_data)}")
        if wellbeing_data:
            df = pd.DataFrame(wellbeing_data)
            print(f"Week range: {df['week_num'].min()} - {df['week_num'].max()}")
            print(f"Average stress level: {df['stress_level'].mean():.2f}")
            print(f"Average sleep duration: {df['sleep_hours'].mean():.2f} hours")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("Test completed!")
    print("=" * 60)
    
    # Restore original working directory
    os.chdir(original_dir)