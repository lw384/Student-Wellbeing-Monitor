## API

### upload csv

Description: read csv file and add into database

| URL                         | request | version | status |
| :-------------------------- | :------ | :------ | :----- |
| /services/upload_service.py | POST    | 1.0     |        |

#### Parameters

| Parameters | Type   | Required | Description | Example |
| :--------- | :----- | :------- | :---------- | :------ |
| username   | String | true     | 登录用户名  | carozhu |
| password   | String | true     | 登录密码    | 123456  |

#### Return

| Return       | Type    | Description |
| :----------- | :------ | :---------- |
| responseCode | Integer | 200：成功   |
| accessToken  | String  | 用户token   |
| ...          | ...     | ...         |

### 获取wellbeing总体均值

#### Parameters

| Parameters | Type   | Required | Description | Example |
| :--------- | :----- | :------- | :---------- | :------ |
| start week | String | true     | 登录用户名  | carozhu |
| End week   | String | true     | 登录密码    | 123456  |
| Module     |        |          |             |         |

#### Return

| Return           | Type    | Description |
| :--------------- | :------ | :---------- |
| Average sleep    | Integer | 5           |
| Average stress   | String  | 3           |
| Average response | ...     | 89%         |

### 获取wellbeing折线图

#### Parameters

| Parameters | Type   | Required | Description | Example |
| :--------- | :----- | :------- | :---------- | :------ |
| start week | String | true     | 登录用户名  | carozhu |
| End week   | String | true     | 登录密码    | 123456  |
| Module     |        |          |             |         |

#### Return

| Return | Type  | Description |
| :----- | :---- | :---------- |
| x      | Array | 5           |
| y      | Array |             |
|        |       |             |



---

# 📘 接口文档

## 1️⃣ 按周查看课程出勤趋势

### 方法

`get_attendance_trends(course_id, programme_id=None, week_start=None, week_end=None)`

### 输入参数

| 参数名          | 类型     | 必填 | 说明             |
| ------------ | ------ | -- | -------------- |
| course_id    | string | 是  | 课程 ID          |
| programme_id | string | 是  | 专业 / cohort ID |
| week_start   | int    | 是  | 起始周（含）         |
| week_end     | int    | 是  | 结束周（含）         |

### 使用到的数据表

| 表名         | 关键字段                                | 用途       |
| ---------- | ----------------------------------- | -------- |
| attendance | student_id, module_id, week, status | 统计出勤/总记录 |
| student    | student_id, programme_id            | 按专业过滤学生  |
| module     | module_id, module_name              | 获取课程名称   |

### 输出示例

```json
{
  "courseId": "WM9AA0",
  "courseName": "Project and Analytics in Industry",
  "points": [
    {
      "week": 1,
      "attendanceRate": 0.8,
      "presentCount": 120,
      "totalCount": 150
    },
    {
      "week": 2,
      "attendanceRate": 0.75,
      "presentCount": 113,
      "totalCount": 150
    }
  ]
}
```

### 逻辑说明

按课程（和可选专业、周区间）筛选 attendance，以 week 分组统计出勤数、总记录数，并计算 attendanceRate，附上课程名称返回。

### 数据层需要的接口

**输入：** `module_id, start_week, end_week, programme_id`
**返回：** `module_id, module_name, status`

> 参数为 None 则不筛选。
> （attendanceRate 在 service 层计算）

**Tips:**

* programme 未输入是否要在响应中返回？可根据前端需求决定
* course 建议统一替换为 module，输入推荐用 `module_code`（如 WMGQ1），避免使用纯数字的 module_id

---

好，我们在你这段接口说明的基础上，稍微“升级”一下这个方法，让它能：

* 利用 **所有 programme + course 的信息** 做聚合；
* 返回的就是 **画 bar 图需要的数据**：x 轴是名字（课程名 / 专业名 / 课程+专业），y 轴是提交情况（提交人数/未交人数/提交率）。

我会保留你原来的方法名，只是把说明改成“返回 bar 数据”。

---

## 2️⃣ 作业提交情况统计（已交 / 未交）——用于 bar 图

### 方法

`get_submission_summary(course_id=None, assignment_no=None, programme_id=None)`

> 说明：
>
> * 不填 `course_id` → 可以按 programme 聚合
> * 不填 `programme_id` → 可以按 course 聚合
> * 两个都填 → 聚合到 “某 programme 下的某门课”
>   （具体怎么用你可以在说明里选一种默认模式）

---

### 输入参数

| 参数名           | 类型     | 必填 | 说明                          |
| ------------- | ------ | -- | --------------------------- |
| course_id     | string | 否  | 课程 ID（若为空，可统计所有课程）          |
| assignment_no | int    | 否  | 作业编号（若为空，可统计该课程所有作业的总提交情况）  |
| programme_id  | string | 否  | 专业 / cohort ID（若为空，可统计所有专业） |

> 你可以在文档里补一句：
>
> * “前端画 bar 时，通常使用 `programme_name` 或 `course_name` 作为 X 轴标签”。

---

### 输出（bar 图数据）示例

假设你选择 **“按课程聚合，bar 的 x 轴为课程名”**，输出可以是这样：

```json
[
  {
    "courseId": "WM9AA0",
    "courseName": "Project and Analytics in Industry",
    "submit": 70,
    "unsubmit": 30,
    "submissionRate": 0.7
  },
  {
    "courseId": "CS2001",
    "courseName": "Machine Learning",
    "submit": 55,
    "unsubmit": 45,
    "submissionRate": 0.55
  }
]
```

如果你想 **按 programme 聚合**，则可以是：

```json
[
  {
    "programmeId": "DS2024",
    "programmeName": "Data Science",
    "submit": 120,
    "unsubmit": 30,
    "submissionRate": 0.8
  },
  {
    "programmeId": "CS2024",
    "programmeName": "Computer Science",
    "submit": 90,
    "unsubmit": 60,
    "submissionRate": 0.6
  }
]
```

### 数据层接口需求
数据层输入

module_id（可选）：课程 ID

assignment_no（可选）：作业编号

programme_id（可选）：专业 ID

这三个参数和 service 层保持一致即可。

数据层输出（从数据库读出来的“原始行数据”长这样）

只需要给 service 层返回以下字段即可：

字段名	说明
module_id，module_name, programme_id, programme_name, student_id, submitted

---

## 3️⃣ 低出勤学生列表

### 方法

`get_low_attendance_students(course_id, programme_id=None, week_start=None, week_end=None, threshold_rate=0.8, min_absences=2)`

### 输入参数

| 参数名            | 类型     | 必填 | 说明            |
| -------------- | ------ | -- | ------------- |
| course_id      | string | 是  | 课程 ID         |
| programme_id   | string | 否  | 专业            |
| week_start     | int    | 否  | 起始周           |
| week_end       | int    | 否  | 结束周           |
| threshold_rate | float  | 否  | 出勤率阈值（默认 0.8） |
| min_absences   | int    | 否  | 缺勤次数阈值（默认 2）  |

### 使用到的数据表

| 表名         | 关键字段                                  | 用途       |
| ---------- | ------------------------------------- | -------- |
| attendance | student_id, module_id, week, status   | 统计出勤与缺勤  |
| student    | student_id, name, email, programme_id | 获取学生基本信息 |
| module     | module_id, module_name                | 获取课程名称   |

### 输出示例

```json
{
  "courseId": "WM9AA0",
  "courseName": "Project and Analytics in Industry",
  "students": [
    {
      "studentId": "S0001",
      "name": "Alice",
      "email": "alice@example.com",
      "attendanceRate": 0.6,
      "absentSessions": 4
    },
    {
      "studentId": "S0003",
      "name": "Charlie",
      "email": "charlie@example.com",
      "attendanceRate": 0.75,
      "absentSessions": 2
    }
  ]
}
```

### 数据层接口需求

**输入：** `module_id, programme_id, start_week, end_week`
**返回：** `module_id, course_name, student_id, student_name, week, status`
（是否低出勤由 service 层判断）

---

## 4️⃣ 多门课作业问题学生（迟交/未交）

### 方法

`get_repeated_late_missing_students(programme_id=None, course_id=None, start_date=None, end_date=None, min_offending_modules=2)`

### 输入参数

| 参数名                   | 类型     | 必填 | 说明               |
| --------------------- | ------ | -- | ---------------- |
| programme_id          | string | 否  | 专业               |
| course_id             | string | 否  | 指定课程，不填看多门课      |
| start_date            | string | 否  | due_date 起始（ISO） |
| end_date              | string | 否  | due_date 结束      |
| min_offending_modules | int    | 否  | 至少多少门课出现问题（默认 2） |

### 输出示例

```json
[
  {
    "studentId": "S0002",
    "name": "Bob",
    "email": "bob@example.com",
    "offendingModuleCount": 2,
    "details": [
      {
        "courseId": "WM9AA0",
        "courseName": "Project and Analytics in Industry",
        "assignmentNo": 1,
        "status": "submit"
      },
      {
        "courseId": "DS201",
        "courseName": "Data Science",
        "assignmentNo": 2,
        "status": "unsubmit"
      }
    ]
  }
]
```

### 数据层接口需求

**返回：** `module_id, course_name, assignmentNo, submitted`
（迟交/未交判断在 service 层）

> 可与接口②共用底层查询逻辑

---

## 5️⃣ 出勤率 vs 成绩（散点图 / 回归）

### 方法

`get_attendance_vs_grades(course_id, programme_id=None, week_start=None, week_end=None)`

### 使用到的数据表

attendance：学生出勤
submission：平均成绩
student：过滤专业
module：课程名称

### 输出示例

```json
{
  "courseId": "WM9AA0",
  "courseName": "Project and Analytics in Industry",
  "points": [
    {
      "studentId": "S0001",
      "attendanceRate": 0.9,
      "grade": 78.5
    },
    {
      "studentId": "S0002",
      "attendanceRate": 0.6,
      "grade": 55.0
    }
  ],
  "regression": {
    "slope": 25.3,
    "intercept": 40.0,
    "rSquared": 0.58
  }
}
```

### 数据层接口

**输入：** `module_id, programme_id, week_start, week_end`
**返回：** `module_id, course_name, student_id, student_name, status(attendance), grade`

（回归由 service 层计算）

---

## 🆕 get_programme_wellbeing_engagement_bar（按 programme 聚合 4 个指标）

### 方法

`get_programme_wellbeing_engagement_bar(course_id, week_start=None, week_end=None)`

### 输出示例

```json
[
  {
    "programmeId": "DS2024",
    "programmeName": "Data Science",
    "avgStress": 3.4,
    "attendanceRate": 0.82,
    "submissionRate": 0.76,
    "avgGrade": 68.2
  },
  {
    "programmeId": "CS2024",
    "programmeName": "Computer Science",
    "avgStress": 3.9,
    "attendanceRate": 0.75,
    "submissionRate": 0.70,
    "avgGrade": 64.5
  }
]
```

### 数据层接口

**输入：** `module_id, programme_id, week_start, week_end`
**返回：**
`module_id, course_name, student_id, programme_id, week, stress, attendance_status, submission_status, grade`

---

# 📌 未纳入实现范围（暂不做）

6️⃣ 查询学生成绩并分级
7️⃣ 找到学习不认真 / 成绩不及格的学生