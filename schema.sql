PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS students (
	student_id INTEGER PRIMARY KEY AUTOINCREMENT,
	roll_no TEXT NOT NULL UNIQUE,
	prn TEXT,
	name TEXT NOT NULL,
	class TEXT NOT NULL,
	semester INTEGER NOT NULL,
	password_hash TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS teachers (
	teacher_id INTEGER PRIMARY KEY AUTOINCREMENT,
	name TEXT NOT NULL UNIQUE,
	phone TEXT UNIQUE,
	password_hash TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS teacher_assignments (
	assignment_id INTEGER PRIMARY KEY AUTOINCREMENT,
	teacher_id INTEGER NOT NULL,
	subject TEXT NOT NULL,
	class TEXT NOT NULL,
	UNIQUE(teacher_id, subject, class),
	FOREIGN KEY(teacher_id) REFERENCES teachers(teacher_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS admins (
	admin_id INTEGER PRIMARY KEY AUTOINCREMENT,
	name TEXT NOT NULL,
	email TEXT NOT NULL UNIQUE,
	password_hash TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS hods (
	hod_id INTEGER PRIMARY KEY AUTOINCREMENT,
	name TEXT NOT NULL,
	phone TEXT NOT NULL UNIQUE,
	password_hash TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS attendance (
	attendance_id INTEGER PRIMARY KEY AUTOINCREMENT,
	student_id INTEGER NOT NULL,
	teacher_id INTEGER NOT NULL,
	subject TEXT NOT NULL,
	class TEXT NOT NULL,
	date TEXT NOT NULL,
	time TEXT,
	status TEXT NOT NULL CHECK(status IN ('Present','Absent')),
	UNIQUE(student_id, subject, class, date),
	FOREIGN KEY(student_id) REFERENCES students(student_id) ON DELETE CASCADE,
	FOREIGN KEY(teacher_id) REFERENCES teachers(teacher_id) ON DELETE CASCADE
);


