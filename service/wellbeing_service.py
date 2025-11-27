import pandas as pd
from typing import List, Dict, Any, Tuple
import sys
import os

# 添加 database 目录到路径
database_path = os.path.join(os.path.dirname(__file__), '..', 'database')
sys.path.insert(0, os.path.abspath(database_path))
from db import get_all_students, get_wellbeing_by_student, get_conn


def get_all_wellbeing_data():
    """
    辅助函数：获取所有 wellbeing 调研数据
    由于 db.py 中没有此函数，我们在这里实现
    """
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT student_id, week, stress_level, hours_slept "
        "FROM wellbeing ORDER BY student_id, week"
    )
    rows = cur.fetchall()
    conn.close()
    # 转换为字典列表格式
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
        # 不再需要 repository，直接使用 db.py 的接口
        pass

    def get_at_risk_students(self) -> Dict[str, List[Dict]]:
        """
        FR-5: 识别风险学生 (核心功能)
        """
        # 获取所有历史调研数据
        raw_data = get_all_wellbeing_data()
        df = pd.DataFrame(raw_data)
        
        # 排序确保按时间顺序处理
        df = df.sort_values(by=['student_id', 'week_num'])

        potential_risk_students = []
        high_risk_students = []
        
        # 获取所有学生名单，用于检查"未填调研"的情况
        # get_all_students() 返回元组列表 (student_id, name, email)，需要转换为字典
        students_tuples = get_all_students()
        all_students = [
            {'id': s[0], 'name': s[1], 'email': s[2]} 
            for s in students_tuples
        ]
        
        # -------------------------------------------------
        # 逻辑 A: 分析已提交数据的学生 (压力 & 睡眠)
        # -------------------------------------------------
        for student_id, group in df.groupby('student_id'):
            # 获取该学生最后一周的数据
            if group.empty: continue
            
            last_entry = group.iloc[-1]
            prev_entries = group.iloc[:-1]
            
            # 获取学生详细信息
            student_info = next((s for s in all_students if s['id'] == student_id), {})
            
            # 1. 判断 [潜在风险]: 本周突变 (压力4-5 & 睡眠<=6) 且 之前正常
            if last_entry['stress_level'] >= 4 and last_entry['sleep_hours'] <= 6:
                # 检查上周是否正常 (如果存在上周数据)
                if not prev_entries.empty:
                    prev_entry = prev_entries.iloc[-1]
                    if prev_entry['stress_level'] < 4:
                        potential_risk_students.append({
                            "id": student_id,
                            "name": student_info.get('name'),
                            "contact": student_info.get('email'),
                            "reason": f"Sudden stress spike (Level {last_entry['stress_level']}) this week."
                        })

            # 2. 判断 [高风险]: 连续3周 压力>=4 且 睡眠<=4
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
        # 逻辑 B: 分析连续未填调研的学生 (包含在 高风险 中)
        # -------------------------------------------------
        current_week = df['week_num'].max() if not df.empty else 0
        for student in all_students:
            s_id = student['id']
            # 找出该学生提交过的周
            submitted_weeks = df[df['student_id'] == s_id]['week_num'].tolist()
            
            # 检查最近3周 (current, current-1, current-2) 是否都缺失
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
        功能：查询指定学生压力最大和睡眠最少的周次
        对应需求：
        1. 哪周压力最大 (input student_id -> output week, stress)
        2. 睡眠最少 (input student_id -> output week, sleep_hour)
        """
        # 获取该学生的所有调研数据
        # get_wellbeing_by_student() 返回元组列表 (week, stress_level, hours_slept)
        raw_tuples = get_wellbeing_by_student(student_id)
        
        # 转换为字典列表格式
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
        
        # 过滤指定学生（实际上已经是该学生的数据了，但保留以保持一致性）
        student_df = df[df['student_id'] == student_id]

        if student_df.empty:
            return {"error": f"No survey data found for student {student_id}"}

        # 1. 找压力最大的一周
        # idxmax() 返回最大值的索引，然后用 loc 取该行数据
        max_stress_idx = student_df['stress_level'].idxmax()
        max_stress_row = student_df.loc[max_stress_idx]

        # 2. 找睡眠最少的一周
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


# ==================== 测试程序 ====================
if __name__ == "__main__":
    import json
    
    # 调整工作目录，确保能找到数据库文件
    # db.py 中的 DB_PATH 是 "data/student.db"，相对于 database 目录
    original_dir = os.getcwd()
    db_dir = os.path.join(os.path.dirname(__file__), '..', 'database')
    os.chdir(os.path.abspath(db_dir))
    
    print("=" * 60)
    print("WellbeingService 测试程序")
    print("=" * 60)
    print(f"数据库目录: {os.path.abspath(db_dir)}")
    print(f"数据库文件: {os.path.join(os.path.abspath(db_dir), 'data', 'student.db')}")
    print("=" * 60)
    
    # 创建服务实例
    service = WellbeingService()
    
    # 测试1: 获取风险学生
    print("\n【测试1】获取风险学生 (get_at_risk_students)")
    print("-" * 60)
    try:
        risk_result = service.get_at_risk_students()
        print(f"当前周次: {risk_result['Current_Selected_Week']}")
        print(f"\n潜在风险学生数量: {len(risk_result['potential_risk'])}")
        if risk_result['potential_risk']:
            print("潜在风险学生列表:")
            for student in risk_result['potential_risk']:
                print(f"  - ID: {student['id']}, 姓名: {student['name']}, 原因: {student['reason']}")
        else:
            print("  无潜在风险学生")
        
        print(f"\n高风险学生数量: {len(risk_result['high_risk'])}")
        if risk_result['high_risk']:
            print("高风险学生列表:")
            for student in risk_result['high_risk']:
                print(f"  - ID: {student['id']}, 姓名: {student['name']}, 原因: {student['reason']}")
        else:
            print("  无高风险学生")
        
        # 以JSON格式输出完整结果（可选）
        print("\n完整结果 (JSON格式):")
        print(json.dumps(risk_result, indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()
    
    # 测试2: 获取学生健康极值
    print("\n\n【测试2】获取学生健康极值 (get_student_health_extremes)")
    print("-" * 60)
    
    # 先获取所有学生ID
    try:
        all_students = get_all_students()
        if all_students:
            # 测试前3个学生
            test_student_ids = [s[0] for s in all_students[:3]]
            print(f"测试学生ID: {test_student_ids}\n")
            
            for student_id in test_student_ids:
                print(f"学生 ID: {student_id}")
                try:
                    extremes = service.get_student_health_extremes(student_id)
                    if "error" in extremes:
                        print(f"  {extremes['error']}")
                    else:
                        print(f"  压力最大: 第{extremes['max_stress']['week']}周, 值={extremes['max_stress']['value']}, {extremes['max_stress']['note']}")
                        print(f"  睡眠最少: 第{extremes['min_sleep']['week']}周, 值={extremes['min_sleep']['value']}小时, {extremes['min_sleep']['note']}")
                except Exception as e:
                    print(f"  错误: {e}")
                print()
        else:
            print("数据库中没有学生数据")
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()
    
    # 测试3: 数据统计
    print("\n【测试3】数据统计")
    print("-" * 60)
    try:
        wellbeing_data = get_all_wellbeing_data()
        students_data = get_all_students()
        print(f"总学生数: {len(students_data)}")
        print(f"总调研记录数: {len(wellbeing_data)}")
        if wellbeing_data:
            df = pd.DataFrame(wellbeing_data)
            print(f"周次范围: {df['week_num'].min()} - {df['week_num'].max()}")
            print(f"平均压力水平: {df['stress_level'].mean():.2f}")
            print(f"平均睡眠时长: {df['sleep_hours'].mean():.2f} 小时")
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)
    
    # 恢复原始工作目录
    os.chdir(original_dir)