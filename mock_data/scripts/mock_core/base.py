from faker import Faker
from pathlib import Path
import csv

fake = Faker()

# 默认输出目录
DEFAULT_OUTPUT_DIR = Path("mock_data/mock")

# 各表字段
STUDENT_FIELDS = ["student_id", "name", "email", "programme_id", "modules"]
PROGRAMME_FIELDS = ["programme_id", "programme_name", "programme_code"]
MODULE_FIELDS = ["module_id", "module_name", "module_code", "programme_id"]
STUDENT_MODULE_FIELDS = ["student_id", "module_id"]
ATTENDANCE_FIELDS = [
    "student_id",
    "module_id",
    "module_code",
    "week",
    "attendance_status",
]
SUBMISSION_FIELDS = ["student_id", "module_id", "module_code", "submitted", "grade"]
WELLBEING_FIELDS = ["student_id", "week", "stress_level", "hours_slept", "comment"]


def write_csv(filename: Path, fieldnames: list[str], rows: list[dict]) -> None:
    """
    Write a list of dict rows into a CSV file at the given path.
    Automatically creates parent directories if needed.
    """
    filename = Path(filename)
    filename.parent.mkdir(parents=True, exist_ok=True)

    with filename.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames,
            extrasaction="ignore",  # 忽略多余字段，防止小拼写错误直接崩掉
        )
        writer.writeheader()
        writer.writerows(rows)


def clean_mock_csv(output_dir: Path):
    """
    删除 output_dir 里的所有 .csv 文件（但保留目录本身）。
    """
    if not output_dir.exists():
        return

    for f in output_dir.glob("*.csv"):
        print(f"Removing {f}")
        f.unlink()  # 删除文件
