import os
from student_wellbeing_monitor.database.db_core import DB_PATH
from student_wellbeing_monitor.database.schema import init_db_schema


def reset_database():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        print("🗑 Old database removed.")

    init_db_schema()
    print("📦 New database schema created.")
