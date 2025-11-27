import random
from .base import fake


def generate_wellbeing_by_week(
    students: list[dict],
    weeks: int = 12,
    min_response_rate: float = 0.5,
    max_response_rate: float = 0.95,
    exam_weeks: list[int] | None = None,
) -> dict[int, list[dict]]:
    """
    Wellbeing data is generated weekly, simulating three patterns:
    1) Students under chronic stress (stress increases weekly)
    2) Students who are sleep-deprived but do not report stress
    3) Normal students
    Several weeks are also supported as "exam weeks," with overall increased stress and decreased sleep.

    Return structure:
    { week_number: [ { student_id, week, stress_level, hours_slept, comment }, ... ], ... }
    """
    if exam_weeks is None:
        # assume exam week, could change
        exam_weeks = [8, 9, 10]

    result: dict[int, list[dict]] = {w: [] for w in range(1, weeks + 1)}

    for s in students:
        # possibilty of finish survey
        response_rate = random.uniform(min_response_rate, max_response_rate)

        #
        profile = random.choices(
            population=["normal", "chronic_stress", "low_sleep_hidden_stress"],
            weights=[
                0.6,
                0.2,
                0.2,
            ],  # 60% normal，20% high stress，20% low sleep and low stress
            k=1,
        )[0]

        base_stress = random.randint(1, 3)

        for w in range(1, weeks + 1):
            # write survey or not
            if random.random() > response_rate:
                continue

            # 生成 stress 和 sleep
            # basic random fluctuation
            stress = base_stress + random.choice([-1, 0, 0, 1])
            hours_slept = random.randint(6, 8)

            if profile == "chronic_stress":
                stress = base_stress + int(w / (weeks / 3)) + random.choice([0, 0, 1])
                hours_slept = random.randint(5, 7)

            elif profile == "low_sleep_hidden_stress":
                hours_slept = random.randint(1, 6)
                stress = random.randint(1, 3)

            else:
                # normal 学生：stress 1–4 之间小波动
                stress = base_stress + random.choice([-1, 0, 0, 1])

            # exam_week
            if w in exam_weeks:
                stress += 1  # 全体压力更大
                hours_slept -= 1  # 睡得更少

            stress = max(1, min(5, stress))
            hours_slept = max(1, min(9, hours_slept))

            row = {
                "student_id": s["student_id"],
                "week": w,
                "stress_level": stress,
                "hours_slept": hours_slept,
                "comment": fake.sentence(nb_words=8),
            }
            result[w].append(row)

    return result
