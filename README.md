# Student-Wellbeing-Monitor

A prototype system designed to support the Student Wellbeing Office and Course Directors by collecting, analysing, and visualising student wellbeing and engagement data (attendance, submissions, survey responses, etc.).

[TOC]

## **Overview**

Student-Wellbeing-Monitor is a small prototype system built in Python 3 with a relational database backend (SQLite).
It aims to demonstrate how a university can:

- Collect and store data such as attendance, coursework submissions, and weekly wellbeing surveys.
- Provide simple analytics (averages, trends, comparisons).
- Support basic CRUD operations for authorised users.
- Visualise key indicators for programmes and modules (courses).

The system is intentionally lightweight and designed for teaching and experimentation, not for production use.

## **Screenshots**

![](https://github.com/lw384/picx-images-hosting/raw/master/Screenshot-2025-12-05-at-17.15.49.8l0jahy89s.webp)

![](https://github.com/lw384/picx-images-hosting/raw/master/Screenshot-2025-12-05-at-17.18.38.464qum773.webp)

## **Features**

- **Data collection & storage**
  - Students, modules, and relationships.
  - Weekly attendance, wellbeing surveys, and submissions.
- **Analytics**
  - Attendance trends by module or programme.
  - Submission summaries (submitted / not submitted).
  - Low-attendance student lists.
  - Cross-feature analytics (attendance vs grades, wellbeing vs engagement).
- **Visualisation**
  - Charts such as bar charts, line charts, scatter plots.
  - Programme-level wellbeing and engagement overview.
- **Mock data generation**
  - Fully configurable CSV generator matching the final DB schema.
  - Easy setup of local demo data for experimentation.
- **Clean architecture**
  - Separation between UI, services, database access, and models.
- **Testing**
  - Pytest-based unit tests.

## **Tech Stack**

**Language:** Python 3

- **Package / Environment Management:** Poetry
- **Database:** SQLite (local file)
- **Web UI:** Flask, Chart.js
- **CLI:** Python CLI entrypoint via Poetry scripts
- **Testing:** pytest

## **Project Structure**

```bash
├── API.md                               # Draft API
├── README.md                            # Project documentation and usage guide
│
├── archive/                             # Exported analytics (CSV summaries)
│   ├── attendance_summary.csv
│   ├── submission_summary.csv
│   └── wellbeing_summary.csv
│
├── database/
│   └── student.db                       # SQLite database used by the application
│
├── mock_data/
│   ├── mock/                            # Generated mock CSV files (students, modules, etc.)
│   └── scripts/                         # Mock data generation utilities
│       ├── generate_all.py              # Generate full dataset (entities + behaviour)
│       ├── generate_behaviour.py        # Create wellbeing, attendance, submission data
│       ├── generate_entities.py         # Create students, programmes, modules
│       └── mock_core/                   # Core logic for mock data generation
│           ├── attendance.py
│           ├── base.py
│           ├── entities.py
│           ├── submission.py
│           └── wellbeing.py
│
├── poetry.lock                          # Poetry lockfile (dependency versions)
├── pyproject.toml                       # Poetry configuration (deps, scripts, metadata)
│
└── src/
    ├── student_wellbeing_monitor/
    │   ├── database/                    # Data access layer (CRUD + schema)
    │   │   ├── create.py
    │   │   ├── db_core.py
    │   │   ├── delete.py
    │   │   ├── read.py
    │   │   ├── schema.py
    │   │   └── update.py
    │   │
    │   ├── services/                    # Business logic and analytics layer
    │   │   ├── archive_service.py
    │   │   ├── attendance_service.py
    │   │   ├── course_service.py
    │   │   ├── upload_service.py
    │   │   └── wellbeing_service.py
    │   │
    │   ├── tools/                       # CLI tools and setup utilities
    │   │   ├── archive.py               # Export summaries to CSV
    │   │   ├── reset_db.py              # Reset database
    │   │   ├── setup_demo.py            # Load demo/mock data into DB
    │   │   └── start.py                 # Start system with demo data
    │   │
    │   └── ui/                          # Web UI
    │       ├── app.py                   # Flask entry point
    │       └── templates/               # HTML templates for the UI
    │
    └── tests/                           # Automated tests (pytest)
        ├── conftest.py                  # Shared fixtures
        ├── test_app.py                  # UI / API tests
        ├── test_database.py             # Database-layer tests
        └── test_services.py             # Service-layer tests
```

## **Getting Started**

### **Prerequisites**

- Python 3.x installed

- [Poetry](https://python-poetry.org/) installed

Install Poetry if you don’t have it:

```
pip install poetry
```

### **Installation**

From the project root:

```
# Install dependencies
poetry install
```

## **Core Commands (Poetry Scripts)**

> All commands below are intended to be run **from the project root** and use Poetry.

### **Generate Mock Data (CSV only)**

Generate data into mock_data/mock/ without inserting into the local database:

```
# Generate only student, programme, and module data (CSV)
poetry run python mock_data/scripts/generate_entities.py

# Based on existing student/programme/module CSVs, generate wellbeing/attendance/submission data
poetry run python mock_data/scripts/generate_behaviour.py

# Generate all mock CSV data (students, modules, attendance, wellbeing, submissions)
poetry run python mock_data/scripts/generate_all.py
```

### **Generate Mock Data and Insert into Local DB**

```
# Generate only student/programme/module data and insert into the local DB
poetry run setup-demo

# Generate full mock dataset (entities + behaviour) and insert everything into the local DB
poetry run setup-demo --with-mock
```

### **Generate Mock Data, Insert into DB, and Start Web UI**

```
poetry run start
```

This script will:

1. Prepare mock data and insert it into the local database.

2. Start the web frontend (Flask app).


### **Start Web UI Only**

```
poetry run wellbeing-web
```

The web UI entry file is located at:

```
src/wellbeing_system/ui/app.py
```

Then open your browser at: http://127.0.0.1:5000

### **Run Tests**

```
# Run the full test suite
poetry run pytest
poetry run pytest --cov #test coverage summary
```

### **Archive For Data Privacy**

Export summaries only (no deletion):

``````
poetry run archive-data
``````

Archive & **delete** data from database (requires explicit confirmation):

``````
poetry run archive-data --confirm
``````

## **Mock Data Generator**

To support development and testing, this project includes a flexible mock data generator.

All mock data (students, modules, attendance, submissions, wellbeing) can be produced using a single script, driven via Poetry.

Mock data is generated into:

```
mock_data/mock/
```

and follows the final database schema and data model used in the application.

### **1. Basic Usage — Generate All Mock Data**

```
poetry run python mock_data/scripts/generate_all.py
```

This command generates:

- programme.csv
- students.csv
- modules.csv
- student_modules.csv
- Weekly attendance files: attendance_week1.csv, attendance_week2.csv, …
- Weekly wellbeing files: wellbeing_week1.csv, wellbeing_week2.csv, …
- Per-module submission files:

    - submissions-<module_code>.csv (e.g. submissions-WG1F6.csv)



All files are placed under mock_data/mock/.

### **2. Clean Existing Mock Data Before Generating**

```
poetry run python mock_data/scripts/generate_all.py --clean
```

--clean will:

- Delete **only** .csv files in mock_data/mock/

- Preserve the directory itself and any non-CSV files

- Ensure a clean environment for new mock data generation


### **3. Customisation Options**

**Change the number of students**

```
poetry run python mock_data/scripts/generate_all.py --students 50
```

**Change the number of modules**

```
poetry run python mock_data/scripts/generate_all.py --modules 8
```

**Change the number of weeks (for attendance & wellbeing)**

```
poetry run python mock_data/scripts/generate_all.py --weeks 12
```

**Change the output directory**

```
poetry run python mock_data/scripts/generate_all.py --out my_output_dir/
```

**Generate a full dataset with custom sizes**

```
poetry run python mock_data/scripts/generate_all.py --students 40 --modules 6 --weeks 10
```

**Clean and then regenerate**

```
poetry run python mock_data/scripts/generate_all.py --clean --students 20 --weeks 6
```

### **4. Generated Data Overview**

The generated mock data includes:

#### **Programme**

7 programmes

File:

``````
programme.csv
``````

#### **Students**

File:

```
students.csv
```

Columns:

- student_id (7-digit, starting with 5)
- name
- email (e.g. @warwick.ac.uk)
- programme id

#### **Modules**

File:

```
modules.csv
```

#### **Student–Module Relationships**

File:

```
student_modules.csv
```

#### **Weekly Attendance**

Files:

```
attendance_week1.csv
attendance_week2.csv
...
```

Binary attendance:

- 0 = absent

- 1 = present

#### **Weekly Wellbeing**

Files:

```
wellbeing_week1.csv
wellbeing_week2.csv
...
```

Includes:

- Stress levels

- Sleep hours

- Simulated behavioural patterns


#### **Coursework Submissions (Per Module)**

Files:

```
submissions-<module_code>.csv
```

Binary submission:

- 1 = submitted

- 0 = not submitted


with realistic grade distributions where applicable.

## **API Design**

This section contains **Service-layer Python function** designs used internally by the application.

You can treat this section as living documentation of the backend capabilities.

- **For more details, see the** **API Document.md** **file in the root folder.**

## **Git Commit Guidelines**

### **1. Commit Message Structure**

Each commit message has two parts:

```
<type>: <short summary>
(optional detailed description...)
```

### **2. Allowed Types**

Use only the following 6 types:

| **type** | **Use case**                                        |
| -------- | --------------------------------------------------- |
| feat     | New feature (new modules, endpoints, scripts, etc.) |
| fix      | Bug fix, logic fix                                  |
| data     | Mock data related (generation scripts, CSV, schema) |
| refactor | Refactor code without changing behaviour            |
| docs     | Documentation (README, design docs, comments)       |
| test     | Add or modify tests (pytest/unittest)               |

### **3. Good vs Bad Examples**

**Good examples:**

- feat: add attendance generator by week

- fix: correct module_code mapping in submissions

- refactor: split mock_core into 4 modules

- docs: add guide for using generate_all script

- data: regenerate wellbeing mock data for week 1-8

- test: add tests for write_csv helper


**Bad examples (avoid):**

- update code

- fix something

- changes

- final version


### **4. One Commit = One Logical Change**

Avoid mixing multiple unrelated changes in one commit. For example, do **not** combine:

- Mock data changes

- UI changes

- Database schema updates

- Test changes


into a single commit.

### **5. Commit Frequency**

- Aim for **2–4 commits per day** (per feature / milestone).

- Commit small, incremental changes frequently rather than one huge commit.


### **6. Branching Strategy (Minimal)**

- main: stable branch

- dev: development branch

- feature/...: feature branches

- fix/...: bug-fix branches


## **Out-of-scope / Not Implemented Yet**

The following ideas are **not included** in the current prototype:

* **Implementation of real user authentication and role-based access control** : The system does not include production-level login, session management, or permission policies.

* **Integration of advanced analytical models or predictive algorithms** : Current analytics focus on descriptive summaries rather than statistical modelling, forecasting, or machine-learning-based risk prediction.

* **Full simulation of real-world academic schedules, programme structures, and teaching patterns**: In reality, different modules may run for varying numbers of weeks, have multiple assessment points, or follow programme-specific timetables.
* **The prototype uses simplified assumptions**: e.g., uniform 12-week teaching blocks, fixed weekly attendance slots, and standardised submission frequencies—which do not capture the full complexity of actual university courses operations.
* **Exploring how Large Language Models can be integrated into business workflows**: Enabling non-technical users to generate insights effortlessly while ensuring the accuracy and reliability of analytical outputs—remains a valuable direction for future development.

These can be considered for future iterations.
