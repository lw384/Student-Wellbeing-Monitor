# Student-Wellbeing-Monitor

A prototype system designed to support the Student Wellbeing Office and Course Directors by collecting, analysing and visualising student wellbeing and engagement data.

📦 1. Project Setup – Poetry Environment

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
2. Project Structure
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

3. Running the Application
Start Flask web 
```
poetry run wellbeing
```
Then open:
http://127.0.0.1:5000

 4. Running Tests
 ```
 poetry run pytest
 ```