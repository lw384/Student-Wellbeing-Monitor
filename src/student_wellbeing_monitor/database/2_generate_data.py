# 2_generate_data.py
# 作用：自动生成 40 个真实名字 + 真实学号 + 12周考勤/问卷/成绩
import os
import sqlite3
import random
from faker import Faker
fake = Faker('en_GB')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))  
DB_PATH = os.path.join(
    BASE_DIR,
    "..", "..", "..",   
    "database", "data", "student.db"
)
DB_PATH = os.path.normpath(DB_PATH)  


conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# 插入真实课程
print("正在插入真实 Warwick 课程...")
courses = [
    ("WM9AA0", "Programming for Artificial Intelligence", "WMG"),
    ("WM9YJ0", "Data Analytics", "WMG"),
    ("WM9A1", "Machine Learning", "Computer Science"),
    ("WM9CD0", "Business Analytics", "WBS"),
    ("WM96X", "Cyber Security", "WMG")
]
for c in courses:
    cur.execute("INSERT OR IGNORE INTO courses VALUES (?, ?, ?)", c)

# 生成学生 —— 重点：只插 course_id！
available_course_ids = [c[0] for c in courses]

for i in range(40):
    student_id = f"U22{2200000 + i:07d}"  # 固定递增，永不重复
    name = fake.name()
    email = f"{student_id}@warwick.ac.uk".lower()
    course_id = random.choice(available_course_ids)
    
    cur.execute("""
        INSERT INTO students (student_id, name, email, course_id)
        VALUES (?, ?, ?, ?)
    """, (student_id, name, email, course_id))

# 生成 40 个学生
# 把这整段替换掉原来的生成学生代码
print("正在生成 40 个真实学生...")

# 先获取所有可用的 course_id
cur.execute("SELECT course_id FROM courses")
available_course_ids = [row[0] for row in cur.fetchall()]



# 为每个学生生成 12 周数据
students = cur.execute("SELECT student_id FROM students").fetchall()

for sid_tuple in students:
    sid = sid_tuple[0]
    for week in range(1, 13):
        # 考勤（80% 出席率）
        attended = 1 if random.random() < 0.80 else 0
        cur.execute("INSERT INTO attendance (student_id, week, attended) VALUES (?, ?, ?)", (sid, week, attended))
        
        # 问卷（70% 填写率）
        if random.random() < 0.7:
            stress = random.choices([1,2,3,4,5], weights=[5,15,40,30,10])[0]
            sleep = round(random.uniform(4.5, 10), 1)
            cur.execute("INSERT INTO wellbeing (student_id, week, stress_level, hours_slept) VALUES (?, ?, ?, ?)",
                        (sid, week, stress, sleep))

# 随机生成 final_grade
for sid_tuple in students:
    sid = sid_tuple[0]
    # 出勤高 → 成绩高（模拟真实情况）
    att_rate = cur.execute("SELECT AVG(attended) FROM attendance WHERE student_id=?", (sid,)).fetchone()[0]
    grade = round(50 + att_rate*40 + random.uniform(-10, 15), 1)   # 50~100 分
    grade = max(0, min(100, grade))  # 限制在 0-100 分之间
    cur.execute("INSERT INTO grades VALUES (?, ?)", (sid, grade))

# 创建两个账号
cur.execute("INSERT INTO users (username, password_hash, role) VALUES ('swo', '123', 'swo')")
cur.execute("INSERT INTO users (username, password_hash, role) VALUES ('cd', '123', 'cd')")

conn.commit()
conn.close()
print("第二步完成！40个真实学生 + 12周数据 + 成绩 全都塞好了！")