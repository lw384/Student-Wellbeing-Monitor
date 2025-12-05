# Student Wellbeing Monitor – Full API Documentation

## Usage Instructions

All interfaces are provided through three service classes:

- `AttendanceService`
- `CourseService`
- `WellbeingService`

You need to create service instances before use:

```python
from attendance_service import AttendanceService
from course_service import CourseService
from wellbeing_service import WellbeingService

attendance_service = AttendanceService()
course_service = CourseService()
wellbeing_service = WellbeingService()
```

---

# 1️⃣ Interface: Get Attendance Trends by Week

**Method Name:** `get_attendance_trends`  
**Class:** `AttendanceService`

## Request Parameters (Query)

| Name         | Type   | Required | Description                                      |
|--------------|--------|----------|--------------------------------------------------|
| course_id    | string | Yes      | Course / module ID                               |
| programme_id | string | No       | Programme / cohort filter; `None` = all          |
| week_start   | int    | No       | Start week (inclusive); `None` = no lower bound  |
| week_end     | int    | No       | End week (inclusive); `None` = no upper bound    |

## Response Example

```json
{
  "courseId": "WM9AA0",
  "courseName": "Applied Artificial Intelligence",
  "points": [
    {
      "week": 1,
      "attendanceRate": 0.82,
      "presentCount": 123,
      "totalCount": 150
    },
    {
      "week": 2,
      "attendanceRate": 0.78,
      "presentCount": 117,
      "totalCount": 150
    }
  ]
}
```

## Logic Overview

1. Query attendance records filtered by `course_id`, optional `programme_id`, and optional week range.
2. For each week:
   - Count `presentCount` (`status` / `attended` = 1)
   - Count `totalCount` (all attendance records in that week)
   - Compute `attendanceRate = presentCount / totalCount`
3. Read `courseName` from the attendance rows (or course table if needed).
4. Sort by week ascending and return a list of points.

### Required Database Function(s)

**Function:** `attendance_for_course(course_id, programme_id, week_start, week_end)`  
**Expected columns per row:**

- `course_id`
- `course_name`
- `student_id`
- `student_name`
- `week`
- `attended` (0/1)

---

# 2️⃣ Interface: Get Submission Summary (Submit / Unsubmit)

**Method Name:** `get_submission_summary`  
**Class:** `CourseService`

Only two states are considered: **submitted** or **not submitted** (no “late” concept).

## Request Parameters (Query)

| Name          | Type   | Required | Description                                       |
|---------------|--------|----------|---------------------------------------------------|
| programme_id  | string | Yes      | Programme / cohort ID                             |
| course_id     | string | No       | Course / module ID; `None` = all courses          |
| assignment_no | int    | No       | Assignment number; `None` = aggregate all         |

## Response Example

```json
{
  "courseId": "WM9AA0",
  "courseName": "Applied Artificial Intelligence",
  "assignmentNo": 1,
  "totalStudents": 100,
  "submit": 80,
  "unsubmit": 20
}
```

## Logic Overview

1. Select all students in the given `programme_id` (and `course_id` if provided).
2. For the selected students and assignment(s), read `submitted` from the submissions table:
   - `1 = submitted`
   - `0 = not submitted`
3. Compute:
   - `totalStudents`: number of students who should submit
   - `submit`: number of records with `submitted = 1`
   - `unsubmit`: number of records with `submitted = 0`
4. Return counts together with course and assignment information.

### Required Database Function(s)

**Function:** `submissions_for_course(programme_id, course_id, assignment_no)`  

**Expected columns per row:**

- `course_id`
- `course_name`
- `student_id`
- `submitted` (0/1)

---

# 3️⃣ Interface: Get Low-attendance Students

**Method Name:** `get_low_attendance_students`  
**Class:** `AttendanceService`

## Request Parameters (Query)

| Name           | Type   | Required | Description                                      |
|----------------|--------|----------|--------------------------------------------------|
| course_id      | string | Yes      | Course / module ID                               |
| programme_id   | string | No       | Programme / cohort ID; `None` = all              |
| week_start     | int    | No       | Start week                                       |
| week_end       | int    | No       | End week                                         |
| threshold_rate | float  | No       | Attendance rate threshold, default `0.8`         |
| min_absences   | int    | No       | Minimum number of absences to flag, default `2`  |

## Response Example

```json
{
  "courseId": "WM9AA0",
  "courseName": "Applied Artificial Intelligence",
  "students": [
    {
      "studentId": "S0001",
      "name": "Alice Smith",
      "email": "alice@example.com",
      "attendanceRate": 0.6,
      "absentSessions": 4
    },
    {
      "studentId": "S0005",
      "name": "Bob Johnson",
      "email": "bob@example.com",
      "attendanceRate": 0.75,
      "absentSessions": 3
    }
  ]
}
```

## Logic Overview

1. Query detailed attendance records for the given course and optional filters.
2. For each student:
   - Count `present` (attended = 1)
   - Count `absent` (attended = 0)
   - Compute `total = present + absent`
   - Compute `attendanceRate = present / total`
3. Flag students if:
   - `attendanceRate < threshold_rate` **OR**
   - `absent >= min_absences`
4. Sort or group as needed and return the flagged students with their statistics.

### Required Database Function(s)

**Function:** `attendance_detail_for_students(course_id, programme_id, week_start, week_end)`  

**Expected columns per row:**

- `course_id`
- `course_name`
- `student_id`
- `student_name`
- `email`
- `week`
- `attended` (0/1)

---

# 4️⃣ Interface: Get Students with Repeated Missing Submissions

**Method Name:** `get_repeated_missing_students`  
**Class:** `CourseService`

## Request Parameters (Query)

| Name                  | Type   | Required | Description                                                   |
|-----------------------|--------|----------|---------------------------------------------------------------|
| course_id             | string | No       | Course / module filter; `None` = all courses                  |
| programme_id          | string | No       | Programme / cohort filter                                     |
| start_week            | int    | No       | Start week (inclusive)                                       |
| end_week              | int    | No       | End week (inclusive)                                         |
| min_offending_modules | int    | No       | Minimum number of modules with missing work, default `2`      |

## Response Example

```json
{
  "students": [
    {
      "studentId": "S0001",
      "name": "Alice Smith",
      "email": "alice@example.com",
      "offendingModuleCount": 2,
      "details": [
        {
          "courseId": "WM9AA0",
          "courseName": "Applied AI",
          "assignmentNo": 1,
          "status": "unsubmit"
        },
        {
          "courseId": "WM9YJ0",
          "courseName": "Data Analytics",
          "assignmentNo": 2,
          "status": "unsubmit"
        }
      ]
    }
  ]
}
```

## Logic Overview

1. Query submissions filtered by `programme_id`, optional `course_id`, and week range.
2. Treat `submitted = 0` as `"unsubmit"`.
3. For each student, collect records where `submitted = 0`, including course and assignment info.
4. For each student:
   - Compute `offendingModuleCount` = number of **distinct** `course_id` with unsubmitted work.
5. Keep only students with `offendingModuleCount >= min_offending_modules`.
6. Return per-student summary plus per-course assignment details.

### Required Database Function(s)

**Function:** `unsubmissions_for_repeated_issues(programme_id, course_id, start_week, end_week)`  

**Expected columns per row:**

- `course_id`
- `course_name`
- `assignment_no`
- `student_id`
- `student_name`
- `email`
- `submitted` (0/1)

---

# 5️⃣ Interface: Attendance vs Grade Analysis

**Method Name:** `get_attendance_vs_grades`  
**Class:** `CourseService`

## Request Parameters (Query)

| Name         | Type   | Required | Description                          |
|--------------|--------|----------|--------------------------------------|
| programme_id | string | No       | Programme / cohort filter            |
| course_id    | string | No       | Course / module filter               |
| week_start   | int    | No       | Minimum week to include              |
| week_end     | int    | No       | Maximum week to include              |

## Response Example

```json
{
  "items": [
    {
      "studentId": "S0001",
      "name": "Alice Smith",
      "attendanceRate": 0.9,
      "avgGrade": 72.5
    },
    {
      "studentId": "S0002",
      "name": "Bob Johnson",
      "attendanceRate": 0.6,
      "avgGrade": 58.0
    }
  ],
  "correlation": 0.42
}
```

> **Note:** The implementation in the provided code returns `"points"` and per-student data; you can extend it to also compute and return a `correlation` field if needed.

## Logic Overview

1. Query joined attendance and grade data for students, filtered by programme, course, and week range.
2. For each student:
   - Count `present` and `total_sessions`
   - Compute `attendanceRate = present / total_sessions`
   - Compute `avgGrade` as the mean of all available non-null grades
3. Optionally discard students with fewer than a minimum number of sessions (e.g., `min_sessions`).
4. Compute a Pearson correlation between attendance rate and average grade **if enough data points are available**.
5. Return the per-student list plus the overall correlation value.

### Required Database Function(s)

**Function:** `attendance_and_grades(programme_id, course_id)`  

**Expected columns per row:**

- `student_id`
- `student_name`
- `attended` (0/1)
- `grade` (nullable)

*(In the concrete implementation, additional fields like `course_id`, `course_name`, `week` may also be present.)*

---

# 6️⃣ Interface: Programme-level Wellbeing & Engagement

**Method Name:** `get_programme_wellbeing_engagement`  
**Class:** `CourseService`

## Request Parameters (Query)

| Name         | Type   | Required | Description                                         |
|--------------|--------|----------|-----------------------------------------------------|
| programme_id | string | No       | Programme filter; `None` = all programmes          |
| week_start   | int    | No       | Start week (inclusive); `None` = no lower bound    |
| week_end     | int    | No       | End week (inclusive); `None` = no upper bound      |

## Response Example

```json
{
  "items": [
    {
      "programmeId": "WM9QF",
      "programmeName": "Applied Artificial Intelligence",
      "studentCount": 45,
      "avgAttendanceRate": 0.86,
      "avgSubmissionRate": 0.81,
      "avgStress": 3.4,
      "avgSleep": 6.9
    },
    {
      "programmeId": "WM9QE",
      "programmeName": "Data Collection & Sampling",
      "studentCount": 38,
      "avgAttendanceRate": 0.82,
      "avgSubmissionRate": 0.78,
      "avgStress": 3.1,
      "avgSleep": 7.2
    }
  ]
}
```

*(The actual implementation returns an object with `programmeId` filter value and a `programmes` array containing per-programme items.)*

## Logic Overview

1. Query attendance, submission, wellbeing, and grade data per student and programme within the week range.
2. At **student level per programme**, compute:
   - `attendanceRate`
   - `submissionRate` (ratio of submitted assignments)
   - `avgStress`
   - `avgSleep`
   - average grade (if available)
3. Aggregate by `programme_id`:
   - `studentCount` (distinct students)
   - mean `attendanceRate`
   - mean `submissionRate`
   - mean `avgStress`
   - mean `avgSleep`
   - mean grade
4. Return one record per programme.

### Required Database Function(s)

**Function:** `programme_wellbeing_engagement(programme_id, week_start, week_end)`  

**Expected columns per row (conceptual):**

- `programme_id`
- `programme_name`
- `student_id`
- `attendance_rate` or `attendance_status`
- `submission_rate` or `submission_status`
- `avg_stress` or `stress_level`
- `avg_sleep` or `hours_slept`
- `grade` (optional)

*(The actual implementation uses per-week rows and aggregates in the service layer.)*

---

# 7️⃣ Interface: High-stress & Low-sleep Engagement Analysis

**Method Name:** `get_high_stress_sleep_engagement_analysis`  
**Class:** `CourseService`

> Note: In the provided code, this method operates at **programme level** using `programme_id`, not `course_id`.

## Request Parameters (Query)

| Name            | Type   | Required | Description                                                   |
|-----------------|--------|----------|---------------------------------------------------------------|
| programme_id    | string | Yes      | Programme / cohort ID                                         |
| week_start      | int    | No       | Start week (inclusive)                                       |
| week_end        | int    | No       | End week (inclusive)                                         |
| stress_threshold| float  | No       | High-stress threshold; default `4.0`                         |
| sleep_threshold | float  | No       | Low-sleep threshold (hours); default `6.0`                   |
| min_weeks       | int    | No       | Minimum weeks satisfying condition to be “high risk”; default `1` |

## Response Example (specification style)

```json
{
  "courseId": "WM9AA0",
  "courseName": "Applied AI",
  "overall": {
    "studentCount": 40,
    "highRiskCount": 5,
    "potentialRiskCount": 8
  },
  "highRiskGroup": {
    "avgAttendanceRate": 0.7,
    "avgSubmissionRate": 0.68,
    "avgGrade": 58.2
  },
  "normalGroup": {
    "avgAttendanceRate": 0.88,
    "avgSubmissionRate": 0.84,
    "avgGrade": 69.5
  }
}
```

*(The current implementation returns grouped stats and per-student lists for “highStressLowSleep” and “others”.)*

## Logic Overview

1. Query weekly wellbeing, attendance, submission, and grade data per student in the selected programme within the week range.
2. For each student, identify weeks where:
   - `stress_level >= stress_threshold` **AND**
   - `hours_slept < sleep_threshold`
3. Classify students:
   - **High Risk**: number of such weeks `>= min_weeks`
   - **Others**: all remaining students
4. For each group separately compute:
   - average `attendanceRate`
   - average `submissionRate`
   - average grade
5. Return overall counts plus group-level engagement statistics and optional per-student records.

### Required Database Function(s)

**Function:** `programme_wellbeing_engagement(programme_id, week_start, week_end)`  

**Expected columns per row:**

- `student_id`
- `programme_id`
- `programme_name`
- `week`
- `stress_level`
- `hours_slept`
- `attendance_status`
- `submission_status`
- `grade` (nullable)

---

# 8️⃣ Interface: AI-based Narrative Insight

**Method Name:** `analyze_high_stress_sleep_with_ai`  
**Class:** `CourseService`

## Request Parameters (Query)

| Name            | Type   | Required | Description                              |
|-----------------|--------|----------|------------------------------------------|
| programme_id    | string | Yes      | Programme / cohort ID                    |
| week_start      | int    | No       | Start week                               |
| week_end        | int    | No       | End week                                 |
| stress_threshold| float  | No       | High-stress threshold; default `4.0`     |
| sleep_threshold | float  | No       | Low-sleep threshold (hours); default `6.0` |
| min_weeks       | int    | No       | Minimum weeks for high-risk, default `1` |

## Response Example

```json
{
  "courseId": "WM9AA0",
  "summary": "About 12% of students in WM9AA0 show sustained high stress and low sleep...",
  "recommendations": [
    "Share mental health and wellbeing resources with the cohort.",
    "Discuss workload and assessment timing with the teaching team.",
    "Encourage students to reach out to their personal tutors."
  ]
}
```

*(In the current implementation, the response is wrapped as `{ "baseStats": ..., "aiAnalysis": { "status": ..., "text": ... } }`.)*

## Logic Overview

1. Internally call `get_high_stress_sleep_engagement_analysis(...)` to obtain:
   - parameters
   - group-level statistics
   - sample per-student records
2. Construct an LLM prompt summarising:
   - size of each group
   - differences in attendance, submissions, and grades
3. Call an external LLM (e.g. Gemini) with the prompt and data to generate:
   - `summary`: high-level narrative about stress, sleep, attendance, and grades
   - `recommendations`: 3–5 actionable suggestions
4. Return both the underlying statistics and the AI-generated analysis.

### Required Database / External Dependencies

- Reuse the database function from Interface 7:
  - `programme_wellbeing_engagement(programme_id, week_start, week_end)`
- External LLM client (e.g. Google Gemini) configured via:
  - environment variable `GEMINI_API_KEY`

---

# 9️⃣ Interface: Dashboard Summary (Wellbeing)

**Method Name:** `get_dashboard_summary`  
**Class:** `WellbeingService`

## Request Parameters (Query)

| Name         | Type   | Required | Description                               |
|--------------|--------|----------|-------------------------------------------|
| start_week   | int    | Yes      | Start week (inclusive)                    |
| end_week     | int    | Yes      | End week (inclusive)                      |
| programme_id | string | No       | Programme filter; `None` = all programmes |

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

1. Validate that `end_week >= start_week`.
2. Query wellbeing records for the given week range and optional programme filter.
3. Compute:
   - `avgStressLevel`: average `stress_level` over all valid records
   - `avgHoursSlept`: average `hours_slept` over all valid records
4. Count distinct students with at least one wellbeing record in the period as `studentCount`.
5. Compute response rate:
   - `total_students` = number of students in the selected programme(s)
   - `responseRate = studentCount / total_students`
6. Return the summary metrics.

### Required Database Function(s)

- `get_wellbeing_records(start_week, end_week, programme_id=None)`  
  Returns: `student_id, week, stress_level, hours_slept, programme_id`
- `get_all_students()` **or** `get_students_by_programme(programme_id)`  
  Returns: basic student information to count total students.

---

# 🔟 Interface: Stress & Sleep Trend

**Method Name:** `get_stress_sleep_trend`  
**Class:** `WellbeingService`

## Request Parameters (Query)

| Name         | Type   | Required | Description                               |
|--------------|--------|----------|-------------------------------------------|
| start_week   | int    | Yes      | Start week                                |
| end_week     | int    | Yes      | End week                                  |
| programme_id | string | No       | Programme / cohort filter; `None` = all   |

## Response Example

```json
{
  "weeks": [1, 2, 3, 4, 5],
  "stress": [3.1, 3.3, 3.2, 3.4, 3.5],
  "sleep": [7.2, 7.0, 7.1, 6.9, 6.8]
}
```

## Logic Overview

1. Validate that `end_week >= start_week`.
2. Query wellbeing records filtered by week range and optional programme.
3. Group by `week` and compute:
   - average `stress_level` per week
   - average `hours_slept` per week
4. Sort by week ascending.
5. Return three parallel arrays:
   - `weeks`: list of week numbers
   - `stress`: average stress per week
   - `sleep`: average sleep hours per week

### Required Database Function(s)

- Reuse `get_wellbeing_records(start_week, end_week, programme_id=None)`  

---

# 1️⃣1️⃣ Interface: Get Risk Students / Query Individual Risk

**Method Name:** `get_risk_students`  
**Class:** `WellbeingService`

## Request Parameters (Query)

| Name           | Type   | Required | Description                                                                 |
|----------------|--------|----------|-----------------------------------------------------------------------------|
| start_week     | int    | Yes      | Start week                                                                  |
| end_week       | int    | Yes      | End week                                                                    |
| programme_id   | string | No       | Programme filter; `None` = all programmes                                   |
| student_id     | string | No       | If set, only this student is analysed; otherwise all students              |
| threshold      | float  | No       | Stress threshold, default `4.5`                                             |
| sleep_threshold| float  | No       | Sleep threshold (hours), default `6.0`                                      |

## Risk Logic

- Build a binary sequence of weeks where both conditions hold:
  - `stress_level >= threshold`
  - `hours_slept < sleep_threshold`

**High Risk:**

- There exists a run of **3 consecutive weeks** in the range where the above conditions are both satisfied.

**Potential Risk:**

- At least one week satisfies the above conditions, but not 3 consecutive weeks.

**Normal (single student only):**

- When `student_id` is specified and the student does not meet any risk condition.

## Response Example (multiple students)

```json
{
  "items": [
    {
      "studentId": "5000001",
      "name": "Alice Smith",
      "email": "alice@example.com",
      "riskType": "high_risk",
      "reason": "Stress ≥ 4.5 and sleep < 6.0h for 3 consecutive weeks",
      "details": "Weeks 3–5: stress ≥ 4.5 and sleep < 6.0h",
      "modules": ["WM9AA0"]
    },
    {
      "studentId": "5000007",
      "name": "David Lee",
      "email": "david@example.com",
      "riskType": "potential_risk",
      "reason": "Stress ≥ 4.5 and sleep < 6.0h",
      "details": "Week 6: stress = 5.0, sleep = 5.5h",
      "modules": ["WM9YJ0"]
    }
  ]
}
```

## Response Example (single normal student)

```json
{
  "items": [
    {
      "studentId": "5000002",
      "name": "Bob Johnson",
      "email": "bob@example.com",
      "riskType": "normal",
      "reason": "No high stress + low sleep pattern detected",
      "details": "Average stress: 3.2, average sleep: 7.5h",
      "modules": ["WM9AA0"]
    }
  ]
}
```

## Logic Overview

1. Validate that `end_week >= start_week`.
2. Query wellbeing records (with programme information) for the given week range and filters.
3. Build mappings from `student_id` to names/emails using the students table.
4. Group wellbeing data by `student_id`, sort weeks.
5. For each student:
   - Create a sequence of `(week, stress, sleep, programme_id)` records.
   - Check for a run of 3 consecutive weeks where:
     - `stress >= threshold` and `sleep < sleep_threshold`  
     → mark as `high_risk`.
   - Otherwise, if any week satisfies the condition:
     → mark as `potential_risk`.
   - If `student_id` was specified and no week satisfies the condition:
     → mark as `normal` and summarise average stress/sleep.
6. Construct response items including:
   - `studentId`, `name`, `email`
   - `riskType` (`high_risk`, `potential_risk`, or `normal`)
   - `reason` (human-readable rule)
   - `details` (specific weeks or averages)
   - `modules` (distinct modules / programmes where records exist)

### Required Database Function(s)

- `get_wellbeing_records(start_week, end_week, programme_id)`  
  Returns: `student_id, week, stress_level, hours_slept, programme_id`
- `get_all_students()` and/or `get_students_by_programme(programme_id)`  
  Returns: `student_id, name, email, programme_id`

