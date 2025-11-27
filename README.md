# Student-Wellbeing-Monitor

A prototype system designed to support the Student Wellbeing Office and Course Directors by collecting, analysing and visualising student wellbeing and engagement data.

## Project Setup – Poetry Environment

This project uses Poetry to manage dependencies, virtual environments and scripts.
Before starting, ensure Poetry is installed:

```
pip install poetry
```
Install project dependencies

From the project root:
```
poetry install
```
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

## Mock

To support development and testing, this project includes a flexible mock data generator.

All mock data (students, modules, attendance, submissions, wellbeing) can be produced using a single command-driven script powered by **Poetry + Python**

Mock data is generated into:

```
data/mock/
```

and follows the final database schema and data model used in the application

### 1.Basic Usage — Generate All Mock Data

Run the following command:

```
poetry run python data/scripts/generate_all.py
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
poetry run python data/scripts/generate_all.py --clean
```

What --clean does:

- Deletes **only** .csv files in data/mock/

- Keeps the directory and any non-CSV files safe

- Ensures a clean environment for new mock data

### 3. Customisation Options

The script supports configurable parameters.

**Change number of students**

```
poetry run python data/scripts/generate_all.py --students 50
```

**Change number of modules**

```
poetry run python data/scripts/generate_all.py --modules 8
```

**Change number of weeks (for attendance & wellbeing)**

```
poetry run python data/scripts/generate_all.py --weeks 12
```

**Change output directory**

```
poetry run python data/scripts/generate_all.py --out my_output_dir/
```

**Generate full dataset with custom size:**

```
poetry run python data/scripts/generate_all.py --students 40 --modules 6 --weeks 10
```

**Clean then regenerate:**

```
poetry run python data/scripts/generate_all.py --clean --students 20 --weeks 6
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

#### 

