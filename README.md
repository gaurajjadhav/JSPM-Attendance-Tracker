# Classroom Attendance Tracker (JSPM)

Simple Flask app to mark class attendance, auto-calc percentages, and generate reports for Students, Teachers, HODs, and Admins.

## Live Demo
- Deployed on PythonAnywhere: [`https://gaurajjadhav.pythonanywhere.com`](https://gaurajjadhav.pythonanywhere.com)

## Tech Stack
- Frontend: HTML, Bootstrap, vanilla JS
- Backend: Python (Flask)
- Database: SQLite (`attendance.db`)
- Exports: CSV, PDF (ReportLab)

## Roles & Key Features
- Student
  - Personal dashboard (daily/weekly/monthly), subject-wise percentages, alerts for < 75%.
- Teacher
  - Select class/subject from assignments, mark attendance (with “Mark All Present”), class report with date range, CSV/PDF export.
- Any User
  - Attendance sheet with filters (class/subject/search), defaulters, CSV/PDF export.
- HOD
  - Dashboard shortcuts, remove student/teacher, bulk import Students and Teachers, Import Class (create class and add students via Paste or CSV), optional subject–teacher assignments with validation.

## Quick Start (Local)
1) Prerequisites: Python 3.10+

2) Setup environment and install dependencies
```bash
python -m venv .venv
. .venv/Scripts/activate  # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

3) Run the app
```bash
set FLASK_APP=app.py
python app.py
```
On first run, the database schema is initialized and base/seed data ensured (incl. HOD user and teacher phone mapping).

## Authentication Notes
- Student: login using PRN or Roll No; default password for new imports is `Test@123` (forced hash on first successful login if missing).
- Teacher: login using registered phone number and password (import via Admin/HOD).
- HOD: seeded with phone and password; can Import Class and manage removals.
- Admin: role supported; create via DB/seed/import as per your environment.

## Data Model (Summary)
- `students(student_id, roll_no [unique], prn, name, class, semester, password_hash)`
- `teachers(teacher_id, name [unique], phone [unique], password_hash)`
- `teacher_assignments(assignment_id, teacher_id → teachers, subject, class, unique(teacher_id,subject,class))`
- `admins(admin_id, name, email [unique], password_hash)`
- `hods(hod_id, name, phone [unique], password_hash)`
- `attendance(attendance_id, student_id → students, teacher_id → teachers, subject, class, date, status[Present|Absent], unique(student_id,subject,class,date))`

## Imports
- Students: paste or CSV (`roll, prn, name`) via Admin or HOD Import Class.
- Teachers: CSV lines (`name, phone, password, subject, class`), creates teacher users and assignments.
- HOD Import Class also accepts optional assignments lines: `subject, teacher_phone_or_name`.

## Exports
- Teacher and Admin can export CSV and PDF reports for selected date ranges.

## Notes
- Attendance % = (attended / total conducted) × 100 within the selected period.
- Schema is defined in `schema.sql`. All tables enforce foreign keys and relevant unique constraints.

## Deployment
- Verified running on PythonAnywhere: [`https://gaurajjadhav.pythonanywhere.com`](https://gaurajjadhav.pythonanywhere.com)
- For other platforms, provide environment variable `SECRET_KEY` in production.

