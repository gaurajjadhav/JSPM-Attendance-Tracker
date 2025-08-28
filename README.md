# Classroom Attendance Tracker

A simple Flask web app to mark attendance, auto-calculate percentages, and show reports for students, teachers, and admins.

## Tech
- Frontend: HTML, CSS, JavaScript (vanilla)
- Backend: Python Flask
- Database: SQLite (file `attendance.db`)

## Setup
1. Install Python 3.10+
2. Create a virtual environment and install deps:

```bash
python -m venv .venv
. .venv/Scripts/activate  # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

3. Run the app:
```bash
set FLASK_APP=app.py
python app.py
```

The app initializes the database and seeds demo users on first run.

## Demo Credentials
- Student: roll `01` / password `student123`
- Teacher: name `Prof. Sharma` / password `teacher123`
- Admin: email `admin@example.com` / password `admin123`

## Features Implemented
- Role-based login and sessions
- Teacher: mark attendance with Mark All Present, view class report with %
- Student: daily/weekly/monthly views, subject-wise % and alerts <75%
- Admin: class reports, search, defaulters, CSV and PDF export

## Notes
- Attendance % = (attended / total conducted) * 100, per selected period.
- Schema defined in `schema.sql`.


