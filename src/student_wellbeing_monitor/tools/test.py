from student_wellbeing_monitor.database.db_core import get_conn

conn = get_conn()
cur = conn.cursor()
cur.execute("SELECT COUNT(*) FROM student")
print("rows in student:", cur.fetchone()[0])
cur.execute("SELECT * FROM student LIMIT 5")
print(cur.fetchall())
conn.close()
