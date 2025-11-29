# WellbeingService API 文档

## 使用说明

所有接口都通过 `WellbeingService` 类提供。使用前需要先创建服务实例：

```python
from wellbeing_service import WellbeingService

# 创建服务实例
service = WellbeingService()

# 调用方法
result = service.get_dashboard_summary(1, 5, None)
```

---

# 1️⃣ 接口：获取仪表盘概览

**方法名称：** `get_dashboard_summary`

**类：** `WellbeingService`

## 请求参数（Query）

| 参数名        | 类型     | 必填 | 说明      |
| ---------- | ------ | -- | ------- |
| startWeek  | int    | 是  | 起始周     |
| endWeek    | int    | 是  | 结束周     |
| moduleCode | string | 否  | 模块，空=全部 |

## 返回示例

```json
{
  "avgHoursSlept": 7.1,
  "avgStressLevel": 3.2,
  "surveyResponses": {
    "studentCount": 38,
    "responseRate": 0.76
  }
}
```

## 简单逻辑说明

1. 查询符合筛选条件的学生数量（若指定 module 则过滤）。
2. 从 wellbeing 表中取出对应周的数据。
3. 计算：

   * 平均睡眠
   * 平均压力
   * 查询过问卷的学生数（distinct student_id）
   * 响应率 = “问卷学生数 / 总学生数”
4. 返回给前端三个 summary 卡片。4

### 需要接口
需要两个接口，一个查询某课程，一个查询全部课程。
接口需要输出：course_id，week，stress，sleep hours
（这里1️⃣和2️⃣可以用同样的接口，service层后面计算，也可以让database写新方法给1️⃣直接把均值给我们）
---

# 2️⃣ 接口：获取压力与睡眠趋势

**方法名称：** `get_stress_sleep_trend`

**类：** `WellbeingService`

## 请求参数（Query）

| 参数名        | 类型     | 必填 | 说明   |
| ---------- | ------ | -- | ---- |
| startWeek  | int    | 是  | 起始周  |
| endWeek    | int    | 是  | 结束周  |
| moduleCode | string | 否  | 模块筛选 |

## 返回示例

```json
{
  "items": [
    {
      "week": 1,
      "avgStress": 3.1,
      "avgSleep": 7.2
    },
    {
      "week": 2,
      "avgStress": 3.3,
      "avgSleep": 7.0
    }
  ]
}
```

## 简单逻辑说明

1. wellbeing × students 联查，按周过滤。
2. 若 module 指定则再过滤课程。
3. 按 week 分组：

   * 平均压力
   * 平均睡眠
4. 返回折线图数据。

### 需要接口
需要两个接口，一个查询某课程，一个查询全部课程。
接口需要输出：course_id，week，stress，sleep hours
---

# 3️⃣ 接口：获取模块出勤率

**方法名称：** `get_attendance_by_module`

**类：** `WellbeingService`

## 请求参数（Query）

| 参数名       | 类型  | 必填 | 说明  |
| --------- | --- | -- | --- |
| startWeek | int | 是  | 起始周 |
| endWeek   | int | 是  | 结束周 |

## 返回示例

```json
{
  "items": [
    {
      "moduleCode": "WG1F6",
      "moduleName": "WG1F6",
      "attendanceRate": 0.92
    },
    {
      "moduleCode": "CS2A4",
      "moduleName": "CS2A4",
      "attendanceRate": 0.85
    }
  ]
}
```

## 简单逻辑说明

1. attendance × students × courses 联查。
2. 基于筛选周范围过滤记录。
3. 按 module 分组统计出勤率：

   * `attendanceRate = AVG(attended)`（因为 attended 是 0/1）。
4. 返回给前端柱状图。

### 需要接口
需要一个接口，接口需要输出course_id,week,attended
---

# 4️⃣ 接口：获取风险学生或者查询学生

**方法名称：** `get_risk_students`

**类：** `WellbeingService`

## 请求参数（Query）

| 参数名           | 类型     | 必填 | 说明                    |
| ------------- | ------ | -- | --------------------- |
| startWeek     | int    | 是  | 起始周                   |
| endWeek       | int    | 是  | 结束周                   |
| moduleCode    | string | 否  | 某模块；空=全部              |
| student_id    | string | 否  | 学生ID；空=所有学生；指定则只返回该学生 |

---

# 🔥 风险判定逻辑

风险判定需要**同时满足**两个条件：
- **压力条件**：`stress >= threshold`（默认 threshold = 4.5）
- **睡眠条件**：`sleep < sleep_threshold`（默认 sleep_threshold = 6.0 小时）

---

## **Potential Risk（潜在风险）**

**只要有任意一周，同时满足 `stress >= threshold` 且 `sleep < sleep_threshold`，即视为 potential risk。**

> 条件：突然出现一次高压力且睡眠不足的周。

---

## **High Risk（高风险）**

**连续三周，每周都同时满足 `stress >= threshold` 且 `sleep < sleep_threshold`。**

> 即连续三周都同时出现高压力和睡眠不足的情况。

---

## 返回示例

```json
{
  "items": [
    {
      "studentId": "5000001",
      "name": "Alice Smith",
      "riskType": "high_risk",
      "reason": "Stress ≥ 4.5 and sleep < 6.0h for 3 consecutive weeks",
      "details": "Weeks 3–5: stress ≥ 4.5 and sleep < 6.0h",
      "modules": ["WG1F6"]
    },
    {
      "studentId": "5000007",
      "name": "David Lee",
      "riskType": "potential_risk",
      "reason": "Stress ≥ 4.5 and sleep < 6.0h",
      "details": "Week 6: stress = 5.0, sleep = 5.5h",
      "modules": ["CS2A4"]
    }
  ]
}
```

**特殊情况：** 当指定 `student_id` 但该学生不满足任何风险条件时，会返回 `riskType: "normal"`：

```json
{
  "items": [
    {
      "studentId": "5000002",
      "name": "Bob Johnson",
      "riskType": "normal",
      "reason": "No risk detected",
      "details": "Average stress: 3.2, average sleep: 7.5h",
      "modules": ["WM9AA0"]
    }
  ]
}
```

**当指定 `student_id` 但找不到学生时：**

```json
{
  "items": [],
  "status": "not_found",
  "message": "Student 9999999 not found"
}
```

**当指定 `student_id` 但学生没有 wellbeing 数据时：**

```json
{
  "items": [],
  "status": "no_data",
  "message": "Student U222200006 exists but has no wellbeing data for the specified period"
}
```

---

## 简单逻辑说明（后端实现逻辑）

1. 从 `wellbeing × students` 查出选定学生在选定周的 `stress` 和 `sleep` 数据。
2. 将数据按学生分组，并按周排序。
3. 对每个学生：

### （1）判断 High Risk

* 查找是否存在连续三周，每周都同时满足：
  ```
  stress[i] >= threshold AND sleep[i] < sleep_threshold
  stress[i+1] >= threshold AND sleep[i+1] < sleep_threshold
  stress[i+2] >= threshold AND sleep[i+2] < sleep_threshold
  ```
* 一旦符合：

  * `riskType = "high_risk"`
  * `reason = "Stress ≥ {threshold} and sleep < {sleep_threshold}h for 3 consecutive weeks"`
  * `details = "Weeks {start}–{end}: stress ≥ {threshold} and sleep < {sleep_threshold}h"`

### （2）否则判断 Potential Risk

* 查找是否存在任意一周，同时满足：
  ```
  stress[i] >= threshold AND sleep[i] < sleep_threshold
  ```
* 一旦符合：

  * `riskType = "potential_risk"`
  * `reason = "Stress ≥ {threshold} and sleep < {sleep_threshold}h"`
  * `details = "Week {week}: stress = {value}, sleep = {value}h"`

### （3）Normal（仅当指定 student_id 时）

* 如果指定了 `student_id` 但该学生不满足任何风险条件：
  * `riskType = "normal"`
  * `reason = "No risk detected"`
  * `details = "Average stress: {avg}, average sleep: {avg}h"`

4. 为符合条件的学生生成：

   * `studentId`
   * `name`
   * `riskType`
   * `reason`（自动生成）
   * `details`（说明高压力和睡眠不足所在周）
   * `modules`

5. 返回 `items` 列表。

### 需要接口
需要一个接口查询所有学生在各周的压力值和睡眠数据。
接口需要输出：`student_id, week, stress, sleep_hours`

---

## Python 使用示例

```python
from wellbeing_service import WellbeingService

# 创建服务实例
service = WellbeingService()

# 1. 获取仪表盘概览
dashboard = service.get_dashboard_summary(
    start_week=1,
    end_week=5,
    module_code=None  # None 表示所有课程
)

# 2. 获取压力与睡眠趋势
trend = service.get_stress_sleep_trend(
    start_week=1,
    end_week=5,
    module_code="WM9AA0"  # 指定课程
)

# 3. 获取模块出勤率
attendance = service.get_attendance_by_module(
    start_week=1,
    end_week=5
)

# 4. 获取风险学生
risk_students = service.get_risk_students(
    start_week=1,
    end_week=5,
    module_code=None,  # None 表示所有课程
    threshold=4.5,     # 压力阈值，默认 4.5
    sleep_threshold=6.0,  # 睡眠阈值，默认 6.0
    student_id=None    # None 表示所有学生，或指定学生ID
)
```