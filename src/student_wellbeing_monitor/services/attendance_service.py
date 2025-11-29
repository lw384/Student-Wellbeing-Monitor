# attendance_service.py
from typing import Optional, Dict, Any, List, Tuple
from collections import defaultdict


class AttendanceService:
    # =========================================================
    # 3️ getAttendanceByModule #TODO: 这个函数应该分到 属于 attendance 的服务里
    # =========================================================

    def get_attendance_by_module(
        self,
        start_week: int,
        end_week: int,
    ) -> Dict[str, Any]:
        """
        对应前端接口：GET /getAttendanceByModule

        输出结构：
            {
              "items": [
                {"moduleCode": "WM9QF", "moduleName": "WM9QF", "attendanceRate": 0.92},
                ...
              ]
            }
        """
        if end_week < start_week:
            raise ValueError("end_week must be >= start_week")

        rows = get_attendance_by_module_weeks(start_week, end_week)
        # rows: (course_id, week, attended)

        att_sum = defaultdict(float)
        att_cnt = defaultdict(int)

        for course_id, week, attended in rows:
            if course_id is None:
                continue
            cid = str(course_id)
            try:
                val = float(attended)  # 假定 0/1
            except (TypeError, ValueError):
                # 如果是 'present' / 'absent'，可以在这里做映射
                continue

            att_sum[cid] += val
            att_cnt[cid] += 1

        items: List[Dict[str, Any]] = []
        for cid in sorted(att_sum.keys()):
            rate = att_sum[cid] / att_cnt[cid] if att_cnt[cid] > 0 else 0.0
            items.append(
                {
                    "moduleCode": cid,
                    "moduleName": cid,  # 如需真实名字，可再查 courses 表
                    "attendanceRate": round(rate, 2),
                }
            )

        return {"items": items}
