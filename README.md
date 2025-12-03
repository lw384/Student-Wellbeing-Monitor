# Student-Wellbeing-Monitor

A prototype system designed to support the Student Wellbeing Office and Course Directors by collecting, analysing and visualising student wellbeing and engagement data.

## 项目命令说明

请使用poetry

 以下所有命令都在项目根目录下运行

**生成假数据**

```
# 只在 mock-data/mock下生成 表 student programme module 的数据
poetry run python mock_data/scripts/generate_entities.py
# 只在 mock-data/mock下根据已有的 student programme module 的数据 生成wellbeing attendance submission 数据
poetry run python mock_data/scripts/generate_behaviour.py
# 在 mock-data/mock 下生成全部假数据
poetry run python mock_data/scripts/generate_all.py
```

**生成假数据 + 写入本地库中**

```
# 只生成 student programme module 的数据 并写入
poetry run setup-demo
# 生成全部假数据并全部写入
poetry run setup-demo --with-mock
```

**生成假数据 + 写入本地库 + 启动前端**

```
poetry run start
```

**只启动前端**

```
poetry run wellbeing-web
```
前端入口文件在 ui/app.py

**启动测试**

```
# 全量测试
poetry run pytest
```



## Project Setup – Poetry Environment

This project uses Poetry to manage dependencies, virtual environments and scripts.
Before starting, ensure **Poetry** is installed:

```
pip install poetry
```
Install project dependencies

From the project root:
```
poetry install
```
setup with mock data

```
poetry run start
```

Insert mock data to database

``````
poetry run setup-demo
``````

Setup project without mock 

``````
poetry run wellbeing-web
``````



## Project Structure

```
student-wellbeing-monitor/
│
├── pyproject.toml                  # Poetry config (dependencies + scripts)
├── README.md                       # Documentation (this file)
│
├── data/                           # SQLite DB, runtime data (ignored by Git)
│   └── wellbeing.db
│
├── src/
│   └── wellbeing_system/           # Main Python package
│       ├── __init__.py
│       │
│       ├── ui/                     # ui
│       │   ├── __init__.py
│       │   ├── cli_main.py         # CLI entry point
│       │   ├── menu.py             # Menu navigation
│       │   └── app.py              # Flask Web Demo 
│       │
│       ├── services/               # Business logic layer
│       │   ├── wellbeing_service.py
│       │   ├── engagement_service.py
│       │   └── analytics_service.py
│       │
│       ├── database/           # Data access layer (SQLite)
│       │   ├── db_init.py
│       │   ├── student_repository.py
│       │   ├── attendance_repository.py
│       │   └── wellbeing_repository.py
│       │
│       └── models/                 # Optional data models (dataclasses)
│
└── tests/                          # Unit tests (TDD)
```

## Running the Application
Start Flask web 

```
poetry run wellbeing
```
Then open:
http://127.0.0.1:5000

## Running Tests

 ```
 poetry run pytest
 ```

## Git Commit

1. Commit 由两部分组成

```
<type>: <short summary>
(optional detailed description...)
```

2. 使用以下 6 个固定 type

- type	用途说明
- feat	新功能（新增模块、新接口、新脚本）
- fix	修复 bug、修复逻辑错误
- data	mock 数据相关（generate scripts、CSV、数据结构等）
- refactor	代码重构，不改变功能（重命名、拆分文件）
- docs	文档更新（README、架构文档、注释）
- test	添加或修改测试（pytest/unittest）

3. commit message 要简短、具体

好例子：

- feat: add attendance generator by week

- fix: correct module_code mapping in submissions
- refactor: split mock_core into 4 modules
- docs: add guide for using generate_all script
- data: regenerate wellbeing mock data for week 1-8
- test: add tests for write_csv helper

坏例子（不要这样）：

- update code
- fix something
- changes
- final version

4. 每次 commit 做“一件事”

不要把：
	•	mock 数据
	•	UI 修改
	•	database schema
	•	test

一次 commit 全混在一起。

5. commit 频率建议
   - 一天至少 2–4 次（功能点 / 阶段点）
   - 每次小改动都要 commit，不要积压到一个大 commit
6. 分支建议（极简）

- main: 稳定版
- dev：开发版
- feature/... ： 功能开发
  fix/...: 修 bug

## Mock

To support development and testing, this project includes a flexible mock data generator.

All mock data (students, modules, attendance, submissions, wellbeing) can be produced using a single command-driven script powered by **Poetry + Python**

Mock data is generated into:

```
mock_data/mock/
```

and follows the final database schema and data model used in the application

### 1.Basic Usage — Generate All Mock Data

Run the following command:

```
poetry run python mock_data/scripts/generate_all.py
```

This will generate:

- students.csv

- modules.csv

- student_modules.csv

- Weekly attendance files: attendance_week1.csv, …

- Weekly wellbeing files: wellbeing_week1.csv, …

- Per-module submission files:

  submissions-<module_code>.csv (e.g., submissions-WG1F6.csv)

All files will be placed in data/mock/.

### 2. Clean Existing Mock Data Before Generating

If you want to clear old generated files:

```
poetry run python mock_data/scripts/generate_all.py --clean
```

What --clean does:

- Deletes **only** .csv files in data/mock/

- Keeps the directory and any non-CSV files safe

- Ensures a clean environment for new mock data

### 3. Customisation Options

The script supports configurable parameters.

**Change number of students**

```
poetry run python mock_data/scripts/generate_all.py --students 50
```

**Change number of modules**

```
poetry run python mock_data/scripts/generate_all.py --modules 8
```

**Change number of weeks (for attendance & wellbeing)**

```
poetry run python mock_data/scripts/generate_all.py --weeks 12
```

**Change output directory**

```
poetry run python mock_data/scripts/generate_all.py --out my_output_dir/
```

**Generate full dataset with custom size:**

```
poetry run python mock_data/scripts/generate_all.py --students 40 --modules 6 --weeks 10
```

**Clean then regenerate:**

```
poetry run python mock_data/scripts/generate_all.py --clean --students 20 --weeks 6
```

5. Generated Data Overview

The generated mock data includes:

**Students**

```
students.csv
```

Columns:

- student_id (7-digit, starting with 5)
- name
- email (@warwick.ac.uk)
- modules (comma-separated module codes)

**Modules**

```
modules.csv
```

**Student–Module Relationships**

```
student_modules.csv
```

**Weekly Attendance**

```
attendance_week1.csv
attendance_week2.csv
...
```

Binary attendance (0 = absent, 1 = present)
**Weekly Wellbeing**

```
wellbeing_week1.csv
wellbeing_week2.csv
...
```

Includes stress levels, sleep hours, and simulated behavioural patterns.

Coursework Submissions (Per Module)

```
submissions-<module_code>.csv
```

Binary submission (submitted=1 / not submitted=0), with realistic grade distributions.

## API

### 用户登录

Author: Luowei

| URL         | request | version | status |
| :---------- | :------ | :------ | :----- |
| /getstudent | POST    | 1.0     | true   |

#### 请求参数说明

| 请求参数 | 类型   | 必填 | 参数说明   | 示例    |
| :------- | :----- | :--- | :--------- | :------ |
| username | String | true | 登录用户名 | carozhu |
| password | String | true | 登录密码   | 123456  |

#### 返回参数说明

| 返回参数     | 参数类型 | 参数说明  |
| :----------- | :------- | :-------- |
| responseCode | Integer  | 200：成功 |
| accessToken  | String   | 用户token |
| ...          | ...      | ...       |

#### 返回示例JSON

```json
{
    "responseCode": 200,
    "data": {
        "name": "carozhu",
        "type": 4,
        "version": "1.2.4",
        "file": "http://versions.update.com/xxx.apk",
        "md5": "6ed86ad3f14db4db716c808cfc1ca392",
        "description": "update for simple to you！"
    }
}
```

#### code码说明

| code | msg     | desc |
| :--- | :------ | :--- |
| 200  | success |      |

#### 接口详细说明 

``` 
如有特别说明请描述

```

---

#### 备注

``` 
关于其它错误返回值与错误代码，参见 [Code码说明](#Link)

```

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

```
get_attendance_trends(course_id, programme_id=None, week_start=None, week_end=None)
```

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

```
get_submission_summary(course_id=None, assignment_no=None, programme_id=None)
```

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

字段名  说明
module_id，module_name, programme_id, programme_name, student_id, submitted

---

## 3️⃣ 低出勤学生列表

### 方法

```
get_low_attendance_students(course_id, programme_id=None, week_start=None, week_end=None, threshold_rate=0.8, min_absences=2)
```

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

```
get_repeated_late_missing_students(programme_id=None, course_id=None, start_date=None, end_date=None, min_offending_modules=2)
```

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

```
get_attendance_vs_grades(course_id, programme_id=None, week_start=None, week_end=None)
```

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

```
get_programme_wellbeing_engagement_bar(course_id, week_start=None, week_end=None)
```

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
