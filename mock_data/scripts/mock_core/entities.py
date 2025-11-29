import random
from .base import fake
import random
import string


# ------------------------------
# 1. Programme（专业）生成
# ------------------------------
def generate_programmes() -> list[dict]:
    """
    Generate programmes in fixed order:
    - programme_id: unique 5-digit numeric ID
    - programme_code: 2 uppercase letters + 2 digits (e.g., AI23)
    - programme_name: fixed list, no randomness in name order
    """
    programme_names = [
        "MSc Applied Artificial Intelligence",
        "MSc Cyber Security Engineering",
        "MSc Supply Chain and Logistics Management",
        "MSc Engineering Design Management",
        "MSc Games Engineering",
        "Msc e-Business Management",
        "Msc Programme and Project Management",
    ]

    programmes: list[dict] = []
    used_ids: set[str] = set()

    for pname in programme_names:
        # programme id
        while True:
            pid = str(random.randint(10000, 99999))
            if pid not in used_ids:
                used_ids.add(pid)
                break

        # programme_code: 2 letters + 2 nums ----
        prefix = "".join(random.choices(string.ascii_uppercase, k=2))
        suffix = str(random.randint(10, 99))
        pcode = prefix + suffix

        programmes.append(
            {
                "programme_id": pid,
                "programme_code": pcode,
                "programme_name": pname,
            }
        )

    return programmes


# ------------------------------
# 2. Student 生成（每个绑定一个 programme）
# ------------------------------


def generate_students(programmes: list[dict], n: int = 20) -> list[dict]:
    """
    Generate a list of students.
    - student_id: 7-digit number starting with 5 (5000000–5999999)
    - email: based on name + @warwick.ac.uk
    - programme_id: each student belongs to ONE programme
    """
    students: list[dict] = []
    used_ids: set[int] = set()

    while len(students) < n:
        student_id = random.randint(5000000, 5999999)
        if student_id in used_ids:
            continue
        used_ids.add(student_id)

        name = fake.name()
        email_local = name.lower().replace(" ", ".").replace("-", "").replace("'", "")
        email = f"{email_local}.{random.randint(1, 99)}@warwick.ac.uk"

        # 随机分配一个 programme
        prog = random.choice(programmes)

        students.append(
            {
                "student_id": student_id,
                "name": name,
                "email": email,
                "programme_id": prog["programme_id"],  # 绑定专业
                "modules": "",  # 后面 generate_student_modules 再填
            }
        )

    return students


# ------------------------------
# 3. Module 生成（按 programme 分配课程）
# ------------------------------


def generate_modules(
    programmes: list[dict],
    min_per_prog: int = 3,
    max_per_prog: int = 5,
) -> list[dict]:
    """
    Generate modules with:
    - module_id: 7-digit internal code
    - module_code: readable course code (e.g. AI1F6)
    - programme_id: which programme this module belongs to
    - module_name: random chosen name
    每个 programme 拥有 3–5 门课。
    """

    module_names_pool = [
        "Foundations",
        "Introduction to Python",
        "Data Analytics",
        "Machine Learning",
        "Deep Learning",
        "Database Systems",
        "Cloud Computing",
        "Research Methods",
        "Fundamentals of Games Research, Development and Management",
        "Computer Graphics",
        "Supply Chain Management",
        "Sustainable Supply Chain Management and the Circular Economy",
        "Interdisciplinary Research Methods",
        "Strategy and Operations Management",
        "Energy Storage Systems",
    ]

    letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    modules: list[dict] = []
    used_ids: set[int] = set()

    for prog in programmes:
        prog_id = prog["programme_id"]
        # 用 programme_id 的前两个字母作为前缀，例如 "AI" / "DS"
        prefix = prog_id[:2].upper()

        num_modules = random.randint(min_per_prog, max_per_prog)

        for _ in range(num_modules):
            # module_code：如 AI1F6 / DS2B3
            prefix = random.choice(letters) + random.choice(letters)
            level = str(random.randint(1, 3))
            mid_letter = random.choice(letters)
            tail_digit = str(random.randint(1, 9))
            module_code = prefix + level + mid_letter + tail_digit

            # module_id：7 位数字
            while True:
                module_id = random.randint(1000000, 9999999)
                if module_id not in used_ids:
                    used_ids.add(module_id)
                    break

            modules.append(
                {
                    "module_id": module_id,
                    "module_code": module_code,
                    "module_name": random.choice(module_names_pool),
                    "programme_id": prog_id,
                }
            )

    return modules


# ------------------------------
# 4. Student-Modules 关系表
# ------------------------------


def generate_student_modules(
    students: list[dict],
    modules: list[dict],
    min_courses: int = 2,
    max_courses: int = 4,
    cross_programme_prob: float = 0.1,
) -> list[dict]:
    """
    Assign 2-4 modules to each student and generate a `student_modules` table.
    规则：
    - 默认从“学生所属 programme 下的 module”中选课
    - 少量课程可以跨专业（cross_programme_prob）
    - 同时把学生选的 module_code 写入 students['modules'] 方便导出到 CSV

    返回：
    - records: 关系表列表，每行 { student_id, module_id }
    """
    records: list[dict] = []

    # 先按 programme 分组 modules，方便针对某专业筛选可选课程
    modules_by_prog: dict[str, list[dict]] = {}
    for m in modules:
        modules_by_prog.setdefault(m["programme_id"], []).append(m)

    for s in students:
        prog_id = s["programme_id"]
        same_prog_modules = modules_by_prog.get(prog_id, [])

        # 选课数量
        count = random.randint(min_courses, max_courses)

        chosen_modules: list[dict] = []

        if same_prog_modules:
            # 绝大部分课从自己专业选
            k = min(count, len(same_prog_modules))
            chosen_modules = random.sample(same_prog_modules, k)

            # 有少量概率加一两门跨专业课
            if random.random() < cross_programme_prob:
                other_modules = [m for m in modules if m["programme_id"] != prog_id]
                if other_modules:
                    extra = random.choice(other_modules)
                    if extra not in chosen_modules:
                        chosen_modules.append(extra)

        else:
            # 极端情况：该专业暂时没有绑课程，就全局抽
            chosen_modules = random.sample(modules, min(count, len(modules)))

        # 写入关系表
        for m in chosen_modules:
            records.append(
                {
                    "student_id": s["student_id"],
                    "module_id": m["module_id"],
                }
            )

        # 同时在 student 记录上加一个易读字段：module_code 列表
        s["modules"] = ", ".join(m["module_code"] for m in chosen_modules)

    return records
