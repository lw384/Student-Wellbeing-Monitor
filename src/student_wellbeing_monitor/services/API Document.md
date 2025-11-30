# WellbeingService API Documentation

## Usage Instructions

All interfaces are provided through the `WellbeingService` class. You need to create a service instance before use:

```python
from wellbeing_service import WellbeingService

# Create service instance
service = WellbeingService()

# Call methods
result = service.get_dashboard_summary(1, 5, None)
```

---

# 1️⃣ Interface: Get Dashboard Summary

**Method Name:** `get_dashboard_summary`

**Class:** `WellbeingService`

## Request Parameters (Query)

| Parameter Name | Type   | Required | Description              |
| -------------- | ------ | -------- | ------------------------ |
| startWeek      | int    | Yes      | Start week               |
| endWeek        | int    | Yes      | End week                 |
| moduleCode     | string | No       | Module, empty = all      |

## Response Example

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

## Logic Overview

1. Query the number of students matching the filter conditions (filter by module if specified).
2. Retrieve data for the corresponding weeks from the wellbeing table.
3. Calculate:

   * Average sleep
   * Average stress
   * Number of students who completed the survey (distinct student_id)
   * Response rate = "Number of survey students / Total students"
4. Return three summary cards to the frontend.

### Required Interfaces
Two interfaces are needed: one to query a specific course, and one to query all courses.
The interface should output: course_id, week, stress, sleep hours
(Interfaces 1️⃣ and 2️⃣ can use the same interface, with calculations done at the service layer, or the database can provide a new method for 1️⃣ that directly returns the averages)
---

# 2️⃣ Interface: Get Stress and Sleep Trend

**Method Name:** `get_stress_sleep_trend`

**Class:** `WellbeingService`

## Request Parameters (Query)

| Parameter Name | Type   | Required | Description                              |
| -------------- | ------ | -------- | ---------------------------------------- |
| start_week     | int    | Yes      | Start week                               |
| end_week       | int    | Yes      | End week                                 |
| programme_id   | string | No       | Programme ID filter (None = all courses) |

## Response Example

```json
{
  "weeks": [1, 2, 3, 4, 5],
  "stress": [3.1, 3.3, 3.2, 3.4, 3.5],
  "sleep": [7.2, 7.0, 7.1, 6.9, 6.8]
}
```

## Logic Overview

1. Join wellbeing × students, filter by week.
2. If programme_id is specified, filter by programme.
3. Group by week:

   * Average stress
   * Average sleep
4. Return line chart data (three arrays: weeks, stress, sleep).

### Response Structure Description
- `weeks`: Array of week numbers, used as X-axis data
- `stress`: Array of average stress values, used as Y-axis data
- `sleep`: Array of average sleep hours, used as Y-axis data
---

# 3️⃣ Interface: Get Module Attendance Rate

**Method Name:** `get_attendance_by_module`

**Class:** `WellbeingService`

## Request Parameters (Query)

| Parameter Name | Type | Required | Description |
| -------------- | ---- | -------- | ----------- |
| startWeek      | int  | Yes      | Start week  |
| endWeek        | int  | Yes      | End week    |

## Response Example

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

## Logic Overview

1. Join attendance × students × courses.
2. Filter records based on the selected week range.
3. Group by module and calculate attendance rate:

   * `attendanceRate = AVG(attended)` (since attended is 0/1).
4. Return bar chart data to the frontend.

### Required Interface
One interface is needed that outputs: course_id, week, attended
---

# 4️⃣ Interface: Get Risk Students or Query Student

**Method Name:** `get_risk_students`

**Class:** `WellbeingService`

## Request Parameters (Query)

| Parameter Name | Type   | Required | Description                                      |
| -------------- | ------ | -------- | ------------------------------------------------ |
| startWeek      | int    | Yes      | Start week                                       |
| endWeek        | int    | Yes      | End week                                         |
| moduleCode     | string | No       | Specific module; empty = all                     |
| student_id     | string | No       | Student ID; empty = all students; if specified, only return that student |

---

# 🔥 Risk Assessment Logic

Risk assessment requires **both** conditions to be met simultaneously:
- **Stress condition**: `stress >= threshold` (default threshold = 4.5)
- **Sleep condition**: `sleep < sleep_threshold` (default sleep_threshold = 6.0 hours)

---

## **Potential Risk**

**If any single week simultaneously satisfies `stress >= threshold` AND `sleep < sleep_threshold`, it is considered a potential risk.**

> Condition: A sudden occurrence of a week with high stress and insufficient sleep.

---

## **High Risk**

**Three consecutive weeks, each simultaneously satisfying `stress >= threshold` AND `sleep < sleep_threshold`.**

> That is, three consecutive weeks all showing high stress and insufficient sleep simultaneously.

---

## Response Example

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

**Special Case:** When `student_id` is specified but the student does not meet any risk conditions, it will return `riskType: "normal"`:

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

**When `student_id` is specified but the student is not found:**

```json
{
  "items": [],
  "status": "not_found",
  "message": "Student 9999999 not found"
}
```

**When `student_id` is specified but the student has no wellbeing data:**

```json
{
  "items": [],
  "status": "no_data",
  "message": "Student U222200006 exists but has no wellbeing data for the specified period"
}
```

---

## Logic Overview (Backend Implementation)

1. Query `stress` and `sleep` data for selected students in selected weeks from `wellbeing × students`.
2. Group data by student and sort by week.
3. For each student:

### (1) Determine High Risk

* Check if there are three consecutive weeks, each simultaneously satisfying:
  ```
  stress[i] >= threshold AND sleep[i] < sleep_threshold
  stress[i+1] >= threshold AND sleep[i+1] < sleep_threshold
  stress[i+2] >= threshold AND sleep[i+2] < sleep_threshold
  ```
* Once met:

  * `riskType = "high_risk"`
  * `reason = "Stress ≥ {threshold} and sleep < {sleep_threshold}h for 3 consecutive weeks"`
  * `details = "Weeks {start}–{end}: stress ≥ {threshold} and sleep < {sleep_threshold}h"`

### (2) Otherwise Determine Potential Risk

* Check if any single week simultaneously satisfies:
  ```
  stress[i] >= threshold AND sleep[i] < sleep_threshold
  ```
* Once met:

  * `riskType = "potential_risk"`
  * `reason = "Stress ≥ {threshold} and sleep < {sleep_threshold}h"`
  * `details = "Week {week}: stress = {value}, sleep = {value}h"`

### (3) Normal (Only when student_id is specified)

* If `student_id` is specified but the student does not meet any risk conditions:
  * `riskType = "normal"`
  * `reason = "No risk detected"`
  * `details = "Average stress: {avg}, average sleep: {avg}h"`

4. Generate for eligible students:

   * `studentId`
   * `name`
   * `riskType`
   * `reason` (auto-generated)
   * `details` (describes the weeks with high stress and insufficient sleep)
   * `modules`

5. Return `items` list.

### Required Interface
One interface is needed to query stress values and sleep data for all students across all weeks.
The interface should output: `student_id, week, stress, sleep_hours`

---

## Python Usage Example

```python
from wellbeing_service import WellbeingService

# Create service instance
service = WellbeingService()

# 1. Get dashboard summary
dashboard = service.get_dashboard_summary(
    start_week=1,
    end_week=5,
    module_code=None  # None means all courses
)

# 2. Get stress and sleep trend
trend = service.get_stress_sleep_trend(
    start_week=1,
    end_week=5,
    module_code="WM9AA0"  # Specify course
)

# 3. Get module attendance rate
attendance = service.get_attendance_by_module(
    start_week=1,
    end_week=5
)

# 4. Get risk students
risk_students = service.get_risk_students(
    start_week=1,
    end_week=5,
    module_code=None,  # None means all courses
    threshold=4.5,     # Stress threshold, default 4.5
    sleep_threshold=6.0,  # Sleep threshold, default 6.0
    student_id=None    # None means all students, or specify student ID
)
```