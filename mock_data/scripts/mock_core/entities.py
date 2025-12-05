import random
from .base import fake
import random
import string
from collections import defaultdict
import random
from typing import List, Dict


# ------------------------------
# 1. Programme
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
# 2. Student (with one programme)
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

        # random programme
        prog = random.choice(programmes)

        students.append(
            {
                "student_id": student_id,
                "name": name,
                "email": email,
                "programme_id": prog["programme_id"],
                "modules": "",  #
            }
        )

    return students


# ------------------------------
# 3. Module (with programme)
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
        # Use the first two letters of programme_id as a prefix, such as "AI"/"DS"
        prefix = prog_id[:2].upper()

        num_modules = random.randint(min_per_prog, max_per_prog)

        for _ in range(num_modules):
            # module_code：AI1F6 / DS2B3
            prefix = random.choice(letters) + random.choice(letters)
            level = str(random.randint(1, 3))
            mid_letter = random.choice(letters)
            tail_digit = str(random.randint(1, 9))
            module_code = prefix + level + mid_letter + tail_digit

            # module_id：7 numbers
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
# 4. Student-Modules Relationship Table
# ------------------------------


def generate_student_modules(
    students: list[dict],
    modules: list[dict],
    min_courses: int = 3,  # Each student must take at least three courses
    max_courses: int = 5,  # Each student can take up to five courses at most
) -> list[dict]:
    """
    Requirements:
        At least five students are required for each module
        Each student takes 3 to 5 courses
        students belong to only one programme (there is already programme_id in students).
        Each module in the modules also has programme_id

    Return
    - records: [{ "student_id": ..., "module_id": ... }, ...]
    students[i]["modules"] = "AY2V2, FK1E6, ..."
    """

    records: list[dict] = []
    assignment_set: set[tuple[int, int]] = (
        set()
    )  # (student_id, module_id) deduplication

    # 1) Group modules & students by programme
    modules_by_prog: dict[str, list[dict]] = defaultdict(list)
    for m in modules:
        modules_by_prog[m["programme_id"]].append(m)

    students_by_prog: dict[str, list[dict]] = defaultdict(list)
    for s in students:
        students_by_prog[s["programme_id"]].append(s)

    # Count the number of courses each student has selected
    student_course_count: dict[int, int] = defaultdict(int)

    # Round One: Ensure that each module has at least five students
    MIN_PER_MODULE = 5

    for m in modules:
        prog_id = m["programme_id"]
        module_id = m["module_id"]

        # Give priority to choosing from the students of this programme
        candidates = students_by_prog.get(prog_id, [])

        # If there are too few students in this major, they will be supplemented from all the students
        if len(candidates) < MIN_PER_MODULE:
            candidates = students

        if not candidates:
            continue

        # Try to give priority to students who haven't taken five courses yet
        flexible_candidates = [
            s for s in candidates if student_course_count[s["student_id"]] < max_courses
        ]
        if len(flexible_candidates) >= MIN_PER_MODULE:
            pool = flexible_candidates
        else:
            #  If it's really not enough, the upper limit can be relaxed (to avoid deadlock)
            pool = candidates

        k = min(MIN_PER_MODULE, len(pool))
        chosen_students = random.sample(pool, k)

        for s in chosen_students:
            sid = s["student_id"]
            key = (sid, module_id)
            if key in assignment_set:
                continue
            assignment_set.add(key)
            records.append({"student_id": sid, "module_id": module_id})
            student_course_count[sid] += 1

    # 3) Round Two: Ensure that each student takes at least three courses (within the range of 3 to 5)
    for s in students:
        sid = s["student_id"]
        prog_id = s["programme_id"]

        current_count = student_course_count.get(sid, 0)
        if current_count >= min_courses:
            continue

        need = min_courses - current_count
        max_extra = max_courses - current_count
        if max_extra <= 0:
            continue  # This student has taken the most classes

        need = min(need, max_extra)
        #   Candidate Courses: Modules under this programme are preferred
        candidate_modules = modules_by_prog.get(prog_id, [])

        # Filter out the courses that the student has already selected
        available_modules = [
            m for m in candidate_modules if (sid, m["module_id"]) not in assignment_set
        ]

        #  If the courses in one's own major are insufficient, it is allowed to make up for them from a global perspective
        if len(available_modules) < need:
            more_modules = [
                m for m in modules if (sid, m["module_id"]) not in assignment_set
            ]
            available_modules = more_modules

        if not available_modules:
            continue

        k = min(need, len(available_modules))
        extra_modules = random.sample(available_modules, k)

        for m in extra_modules:
            mid = m["module_id"]
            key = (sid, mid)
            if key in assignment_set:
                continue
            assignment_set.add(key)
            records.append({"student_id": sid, "module_id": mid})
            student_course_count[sid] += 1

    # write module_code in student["modules"]
    modules_by_id: dict[int, str] = {m["module_id"]: m["module_code"] for m in modules}
    modules_for_student: dict[int, list[str]] = defaultdict(list)

    for r in records:
        sid = r["student_id"]
        mid = r["module_id"]
        code = modules_by_id.get(mid)
        if code and code not in modules_for_student[sid]:
            modules_for_student[sid].append(code)

    for s in students:
        sid = s["student_id"]
        codes = modules_for_student.get(sid, [])
        s["modules"] = ", ".join(codes)

    return records
