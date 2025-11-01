# JSPM Classroom Attendance Tracker

A comprehensive Flask-based web application for managing student attendance with role-based access for teachers, students, administrators, and HODs.

## 🚀 Tech Stack

- **Frontend:** HTML, CSS, JavaScript (Vanilla)
- **Backend:** Python Flask
- **Database:** SQLite (`attendance.db`)
- **PDF Generation:** ReportLab

## 🛠️ Setup Instructions

1. **Install Python 3.10 or higher**

2. **Create a virtual environment and install dependencies:**
   ```bash
   python -m venv venv
   .\venv\Scripts\activate      # Windows PowerShell
   # or: venv\Scripts\activate.bat      # Windows CMD
   pip install -r requirements.txt
   ```

3. **Run the application:**
   ```bash
   python app.py
   ```
   The app will run on http://127.0.0.1:5000 by default

4. **The app automatically initializes the database and seeds demo users on first run.**

## 👤 Demo Credentials

- **Student:** roll `01` / password `student123`
- **Teacher:** name `Prof. Sharma` / password `teacher123`
- **Admin:** email `admin@example.com` / password `admin123`

## ✨ Key Features

### Role-Based Access Control
- Separate dashboards and permissions for Students, Teachers, Admins, and HODs
- Secure session management with password hashing

### Teacher Portal
- **Class & Subject Selection:** Choose from assigned classes and subjects
- **Lecture Time Selection (NEW!)** 🆕
  - **Quick Select:** Pre-defined time slots from 7:00 AM to 8:00 PM (30-minute intervals)
  - **Custom Time:** Enter any specific time format (e.g., 08:45 AM - 09:45 AM)
  - **Fully Optional:** Teachers can skip time selection if not needed
- **Attendance Marking:** Mark individual or all students as present
- **View Reports:** Generate attendance reports with percentage calculations

### Enhanced Reporting (NEW! 🆕)
- **Lecture Time in Reports:** All PDF and CSV exports now include lecture time information
- **Complete Transparency:** Track exactly when lectures were conducted
- **Multiple Export Formats:** CSV and PDF with comprehensive attendance data

### Student Portal
- View personal attendance records
- Subject-wise attendance percentages
- Daily, weekly, and monthly views
- Low attendance alerts (<75%)

### Admin Portal
- Manage classes, teachers, and students
- Bulk import functionality for students and teachers
- Advanced reporting and filtering
- Export reports to CSV/PDF with lecture times

### Modern UI/UX (NEW! 🆕)
- Clean, responsive interface
- Properly aligned form elements
- Improved time selection interface
- Professional design with better spacing

## 🆕 Recent Updates

### Lecture Time Feature
- **Optional Time Selection:** Teachers can specify lecture times when marking attendance
- **Flexible Options:** 
  - Quick select from common time slots
  - Custom time input for any specific period
  - Fully optional - can be skipped
- **Time Tracking:** Lecture times are stored with attendance records
- **Report Integration:** Times appear in all PDF and CSV exports

### UI Improvements
- Better form layout and alignment
- Enhanced time selection interface
- Improved visual hierarchy
- Better responsive design

## 📊 Database Schema

The database schema includes:
- `students` - Student information
- `teachers` - Teacher accounts
- `admins` - Administrator accounts
- `hods` - Head of Department accounts
- `teacher_assignments` - Class and subject assignments
- `attendance` - Attendance records (includes `time` field for lecture timing)

See `schema.sql` for complete schema definition.

## 📝 Notes

- Attendance percentage = (attended / total conducted) × 100, per selected period
- Lecture time is optional and can be skipped by teachers
- All times are stored in 12-hour format with AM/PM
- Database is automatically initialized on first run

## 🔒 Security

- Passwords are hashed using pbkdf2_sha256
- Session-based authentication
- Role-based access control
- SQL injection protection through parameterized queries

## 📄 License

This project is developed for JSPM educational institution.

---

Made with ❤️ for educators and students
