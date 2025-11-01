# JSPM Classroom Attendance Tracker

A user-friendly web application for tracking student attendance, cloud-based and easily managed by teachers, admins, and students.

---

## Live Demo
- Deployed on PythonAnywhere: [`https://gaurajjadhav.pythonanywhere.com`](https://gaurajjadhav.pythonanywhere.com)



## Tech Stack

- **Frontend:** HTML, CSS, JavaScript (Vanilla)
- **Backend:** Python Flask
- **Database:** SQLite (`attendance.db`)
- **PDF Reports:** ReportLab

---

## Setup Instructions

1. **Install Python 3.10 or newer**
2. **Clone the repository & enter the project folder**

3. **Create a virtual environment & install dependencies:**
    ```bash
    python -m venv venv
    .\venv\Scripts\activate      # Windows PowerShell
    pip install -r requirements.txt
    ```

4. **Run the application:**
    ```bash
    python app.py
    ```
    By default, the app runs on http://127.0.0.1:5000

5. **The app initializes the database and seed demo users on first run.**


---

## Main Features

- **Role-Based Login**
  - Separate dashboards and permissions for Student, Teacher, HOD

- **Teacher Portal**
  - Mark attendance (all present or individual)
  - **Select class & subject** from assignments
  - **Lecture time selection** (NEW!)
    - “Quick Select” for common time slots (7 AM – 8 PM)
    - “Custom Time” for any specific period (fully flexible, AM/PM supported)
    - Time input is _optional_ – teachers may skip it if not needed
    - All options are **cleanly aligned, simple, and visually accessible**
  - **Persist lecture time** in attendance records

- **Attendance Reporting**
  - PDFs & CSV attendance reports include lecture time(s) (NEW!)
    - Times shown in top headers/columns of reports for full transparency
    - Supports multiple, distinct lecture times

- **Student Portal**
  - View attendance, subject-wise and period-wise
  - Alerts for low attendance (<75%)

- **Admin Portal**
  - Add/manage classes, teachers, students
  - Bulk importing
  - Advanced reporting & filtering
  - Export reports to CSV/PDF (with times)

- **Modern Interface**
  - Responsive, clean UI
  - Proper alignment of all input fields
  - Error, info, and success messages for all key actions

- **Secure**
  - Passwords stored hashed
  - Session protected

---

## Notable Recent Additions

- **Optional Lecture Time Selection**
  - Teachers can quickly select or manually enter custom times.
  - Time selection is not mandatory.

- **Lecture Time in Reports**
  - Each report (CSV/PDF) exports the lecture time(s) held in the selected period for a class/subject.

- **Cleaner UI/UX**
  - Time selectors now stack vertically, never overflow or appear outside their card/frame.
  - Form components have increased clarity and are easier to fill.

---

## Notes

- See `schema.sql` for details on the database structure & the new `time` field on the `attendance` table.
- All dependencies listed in `requirements.txt`.
- Ideal for educational institutes seeking a lightweight, fast, and transparent attendance system.

---

## License

MIT – See LICENSE file.

---

Made with ❤️ for JSPM and educators everywhere.
