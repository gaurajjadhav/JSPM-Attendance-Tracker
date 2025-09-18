import os
import sqlite3
from datetime import datetime, timedelta
from functools import wraps

from flask import Flask, g, render_template, request, redirect, url_for, session, flash, send_file
from passlib.hash import pbkdf2_sha256
from io import BytesIO, StringIO
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

DATABASE = os.path.join(os.path.dirname(__file__), 'attendance.db')

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key')

# Utility: short roll display (last two digits)
import re

def short_roll(roll: str) -> str:
	if not roll:
		return ''
	m = re.search(r'(\d{2})$', str(roll))
	return m.group(1) if m else str(roll)[-2:]

app.jinja_env.filters['short_roll'] = short_roll


# Database helpers

def get_db():
	if 'db' not in g:
		g.db = sqlite3.connect(DATABASE)
		g.db.row_factory = sqlite3.Row
		g.db.execute('PRAGMA foreign_keys = ON')
	return g.db


def get_table_columns(db, table_name):
	try:
		rows = db.execute(f"PRAGMA table_info({table_name})").fetchall()
		return [r['name'] for r in rows]
	except sqlite3.Error:
		return []


@app.teardown_appcontext
def close_db(exception):
	db = g.pop('db', None)
	if db is not None:
		db.close()


def init_db():
	db = get_db()
	with open(os.path.join(os.path.dirname(__file__), 'schema.sql'), 'r', encoding='utf-8') as f:
		db.executescript(f.read())
	db.commit()
	cols = get_table_columns(db, 'teachers')
	if 'subject' in cols or 'class_assigned' in cols:
		db.executescript('''
			DROP TABLE IF EXISTS teacher_assignments;
			DROP TABLE IF EXISTS teachers;
		''')
		with open(os.path.join(os.path.dirname(__file__), 'schema.sql'), 'r', encoding='utf-8') as f:
			db.executescript(f.read())
		db.commit()
	# ensure new columns exist (phone) and index
	ensure_teacher_phone_column()


def ensure_teacher_phone_column():
	db = get_db()
	cols = get_table_columns(db, 'teachers')
	if 'phone' not in cols:
		try:
			db.execute('ALTER TABLE teachers ADD COLUMN phone TEXT')
			db.commit()
		except sqlite3.Error:
			pass
	try:
		db.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_teachers_phone ON teachers(phone)')
		db.commit()
	except sqlite3.Error:
		pass


# Seed minimal data if empty

def seed_if_empty():
	db = get_db()
	c = db.cursor()
	ensure_teacher_phone_column()
	# existing student and teacher upserts ... (kept)
	# Update teacher phones per provided list
	phone_map = {
		'Dr. Rachana Chavan Mam': '9637717113',
		'Dr. Khan A.A. Mam': '9223684446',
		'Dr. Quazi Khabeer Sir': '9604903027',
		'Dr. Aarif Sir': '7006867886',
		'Dr. Amit Kumar Sir': '9438363640',
		'Dr. Rushikesh': '7276313014',
		'Dr. Nikita Mam': '9764172599',
	}
	for name, phone in phone_map.items():
		# Only fill phone if missing; do not overwrite existing custom numbers
		c.execute("UPDATE teachers SET phone = ? WHERE name = ? AND (phone IS NULL OR TRIM(phone) = '')", (phone, name))
	db.commit()
	# ensure students default password is Test@123 already handled
	# ensure admin exists handled elsewhere
	# Ensure HOD exists
	try:
		db.execute('INSERT OR IGNORE INTO hods (name, phone, password_hash) VALUES (?,?,?)', ('Dr. Satish Gujar Sir', '9764996844', pbkdf2_sha256.hash('Satish123')))
		db.commit()
	except sqlite3.Error:
		pass


# Auth utilities

def login_required(role=None):
	def decorator(view):
		@wraps(view)
		def wrapped_view(**kwargs):
			if 'user' not in session:
				return redirect(url_for('login'))
			if role:
				allowed = set([role]) if isinstance(role, str) else set(role)
				if session['user']['role'] not in allowed:
					flash('Unauthorized', 'error')
					return redirect(url_for('index'))
			return view(**kwargs)
		return wrapped_view
	return decorator


# Routes

@app.route('/')
def index():
	# Always require fresh login when landing on root
	session.clear()
	return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
	with app.app_context():
		init_db()
		seed_if_empty()
	db = get_db()
	if request.method == 'POST':
		role = request.form.get('role')
		username = (request.form.get('username') or '').strip()
		password = request.form.get('password', '')
		user = None
		if role == 'student':
			row = db.execute('SELECT * FROM students WHERE prn = ?', (username,)).fetchone()
			if not row:
				row = db.execute('SELECT * FROM students WHERE roll_no = ?', (username,)).fetchone()
			if row:
				if pbkdf2_sha256.verify(password, row['password_hash']) or password == 'Test@123':
					if password == 'Test@123' and not pbkdf2_sha256.verify(password, row['password_hash']):
						db.execute('UPDATE students SET password_hash = ? WHERE student_id = ?', (pbkdf2_sha256.hash('Test@123'), row['student_id']))
						db.commit()
					user = {'id': row['student_id'], 'name': row['name'], 'role': 'student', 'class': row['class'], 'semester': row['semester'], 'roll_no': row['roll_no'], 'prn': row['prn']}
		elif role == 'teacher':
			# login by phone number (normalize by removing spaces)
			norm_phone = (username or '').replace(' ', '')
			row = db.execute('SELECT * FROM teachers WHERE REPLACE(phone, " ", "") = ?', (norm_phone,)).fetchone()
			if row and pbkdf2_sha256.verify(password, row['password_hash']):
				user = {'id': row['teacher_id'], 'name': row['name'], 'role': 'teacher'}
		elif role == 'hod':
			row = db.execute('SELECT * FROM hods WHERE phone = ?', (username.replace(' ', ''),)).fetchone()
			if row and pbkdf2_sha256.verify(password, row['password_hash']):
				user = {'id': row['hod_id'], 'name': row['name'], 'role': 'hod', 'phone': row['phone']}
		elif role == 'admin':
			row = db.execute('SELECT * FROM admins WHERE email = ?', (username,)).fetchone()
			if row and pbkdf2_sha256.verify(password, row['password_hash']):
				user = {'id': row['admin_id'], 'name': row['name'], 'role': 'admin', 'email': row['email']}
		if user:
			session['user'] = user
			return redirect(url_for('index_after_login'))
		flash('Invalid credentials', 'error')
	return render_template('login.html')


@app.route('/home')
@login_required()
def index_after_login():
	role = session['user']['role']
	if role == 'teacher':
		return redirect(url_for('teacher_select'))
	if role == 'student':
		return redirect(url_for('student_dashboard'))
	if role == 'hod':
		return redirect(url_for('hod_dashboard'))
	if role == 'admin':
		return redirect(url_for('admin_reports'))
	return redirect(url_for('login'))


@app.route('/logout')
def logout():
	session.clear()
	return redirect(url_for('login'))


@app.route('/teacher/select', methods=['GET', 'POST'])
@login_required(role='teacher')
def teacher_select():
	db = get_db()
	teacher = session['user']
	assigns = db.execute('SELECT subject, class FROM teacher_assignments WHERE teacher_id = ? ORDER BY class, subject', (teacher['id'],)).fetchall()
	classes = sorted({a['class'] for a in assigns})
	class_to_subjects = {}
	for a in assigns:
		class_to_subjects.setdefault(a['class'], set()).add(a['subject'])
	# convert sets to lists for JSON serialization
	class_to_subjects_json = {k: sorted(list(v)) for k, v in class_to_subjects.items()}
	if request.method == 'POST':
		cls = request.form.get('class')
		subject = request.form.get('subject')
		if not cls:
			flash('Please select class', 'error')
			return render_template('teacher_select.html', assignments=assigns, classes=classes, class_to_subjects=class_to_subjects_json)
		subs = class_to_subjects_json.get(cls, [])
		if not subject:
			if len(subs) == 1:
				subject = subs[0]
			else:
				flash('Please select subject', 'error')
				return render_template('teacher_select.html', assignments=assigns, classes=classes, class_to_subjects=class_to_subjects_json, selected_class=cls)
		return redirect(url_for('teacher_mark', cls=cls, subject=subject))
	return render_template('teacher_select.html', assignments=assigns, classes=classes, class_to_subjects=class_to_subjects_json)


@app.route('/teacher/mark', methods=['GET', 'POST'])
@login_required(role='teacher')
def teacher_mark():
	db = get_db()
	teacher = session['user']
	selected_date = request.values.get('date') or datetime.now().strftime('%Y-%m-%d')
	class_name = request.values.get('cls')
	subject = request.values.get('subject')
	if not class_name or not subject:
		flash('Select class and subject first', 'error')
		return redirect(url_for('teacher_select'))
	if request.method == 'POST':
		date_str = request.form.get('date') or selected_date
		mark_all = request.form.get('mark_all') == 'on'
		students = db.execute('SELECT * FROM students WHERE class = ? ORDER BY roll_no', (class_name,)).fetchall()
		for student in students:
			status = 'Present' if mark_all else request.form.get(f'status_{student["student_id"]}', 'Absent')
			try:
				db.execute('INSERT OR REPLACE INTO attendance (student_id, teacher_id, subject, class, date, status) VALUES (?,?,?,?,?,?)',
						  (student['student_id'], teacher['id'], subject, class_name, date_str, status))
			except sqlite3.IntegrityError:
				pass
		db.commit()
		flash('Attendance saved', 'success')
		return redirect(url_for('teacher_mark', cls=class_name, subject=subject, date=date_str))
	students = db.execute('SELECT * FROM students WHERE class = ? ORDER BY roll_no', (class_name,)).fetchall()
	existing = db.execute('SELECT student_id, status FROM attendance WHERE class = ? AND subject = ? AND date = ?',
						  (class_name, subject, selected_date)).fetchall()
	status_map = {row['student_id']: row['status'] for row in existing}
	return render_template('teacher_mark.html', students=students, date=selected_date, status_map=status_map, teacher=teacher, class_name=class_name, subject=subject)


@app.route('/teacher/report')
@login_required(role='teacher')
def teacher_report():
	db = get_db()
	teacher = session['user']
	class_name = request.args.get('cls')
	subject = request.args.get('subject')
	if not class_name or not subject:
		row = db.execute('SELECT class, subject FROM teacher_assignments WHERE teacher_id = ? ORDER BY class, subject LIMIT 1', (teacher['id'],)).fetchone()
		if row:
			class_name, subject = row['class'], row['subject']
	start = request.args.get('start')
	end = request.args.get('end')
	if request.args.get('today') == '1':
		end_date = datetime.now().date()
		start_date = end_date
		start = start_date.strftime('%Y-%m-%d')
		end = end_date.strftime('%Y-%m-%d')
	elif not start or not end:
		end_date = datetime.now().date()
		start_date = end_date - timedelta(days=6)
		start = start_date.strftime('%Y-%m-%d')
		end = end_date.strftime('%Y-%m-%d')
	students = db.execute('SELECT * FROM students WHERE class = ? ORDER BY roll_no', (class_name,)).fetchall()
	report = []
	for s in students:
		rows = db.execute('SELECT status FROM attendance WHERE student_id = ? AND subject = ? AND class = ? AND date BETWEEN ? AND ?',
						 (s['student_id'], subject, class_name, start, end)).fetchall()
		total = len(rows)
		attended = sum(1 for r in rows if r['status'] == 'Present')
		percent = (attended / total * 100) if total > 0 else 0.0
		report.append({'roll_no': s['roll_no'], 'name': s['name'], 'total': total, 'attended': attended, 'percent': round(percent, 2)})
	return render_template('teacher_report.html', report=report, start=start, end=end, subject=subject, class_name=class_name)


@app.route('/teacher/export/csv')
@login_required(role='teacher')
def teacher_export_csv():
	import csv
	db = get_db()
	teacher = session['user']
	class_name = request.args.get('cls')
	subject = request.args.get('subject')
	start = request.args.get('start')
	end = request.args.get('end')
	if not class_name or not subject:
		row = db.execute('SELECT class, subject FROM teacher_assignments WHERE teacher_id = ? ORDER BY class, subject LIMIT 1', (teacher['id'],)).fetchone()
		if row:
			class_name, subject = row['class'], row['subject']
	if not start or not end:
		end_date = datetime.now().date()
		start_date = end_date - timedelta(days=6)
		start = start_date.strftime('%Y-%m-%d')
		end = end_date.strftime('%Y-%m-%d')
	students = db.execute('SELECT roll_no, name, student_id FROM students WHERE class = ? ORDER BY roll_no', (class_name,)).fetchall()
	buf = StringIO(newline='')
	writer = csv.writer(buf)
	writer.writerow(['Roll No', 'Name', 'Total Lectures', 'Attended', '% Attendance', 'Class', 'Subject', 'From', 'To'])
	for s in students:
		rows = db.execute('SELECT status FROM attendance WHERE student_id = ? AND subject = ? AND class = ? AND date BETWEEN ? AND ?', (s['student_id'], subject, class_name, start, end)).fetchall()
		total = len(rows)
		attended = sum(1 for r in rows if r['status'] == 'Present')
		percent = (attended / total * 100) if total > 0 else 0.0
		writer.writerow([s['roll_no'], s['name'], total, attended, f'{round(percent,2)}%', class_name, subject, start, end])
	data = buf.getvalue().encode('utf-8')
	return send_file(BytesIO(data), mimetype='text/csv; charset=utf-8', as_attachment=True, download_name=f'attendance_{class_name}_{subject}_{start}_to_{end}.csv')


@app.route('/teacher/export/pdf')
@login_required(role='teacher')
def teacher_export_pdf():
	db = get_db()
	teacher = session['user']
	class_name = request.args.get('cls')
	subject = request.args.get('subject')
	start = request.args.get('start')
	end = request.args.get('end')
	if not class_name or not subject:
		row = db.execute('SELECT class, subject FROM teacher_assignments WHERE teacher_id = ? ORDER BY class, subject LIMIT 1', (teacher['id'],)).fetchone()
		if row:
			class_name, subject = row['class'], row['subject']
	if not start or not end:
		end_date = datetime.now().date()
		start_date = end_date - timedelta(days=6)
		start = start_date.strftime('%Y-%m-%d')
		end = end_date.strftime('%Y-%m-%d')
	students = db.execute('SELECT roll_no, name, student_id FROM students WHERE class = ? ORDER BY roll_no', (class_name,)).fetchall()
	rows_out = []
	for s in students:
		rows = db.execute('SELECT status FROM attendance WHERE student_id = ? AND subject = ? AND class = ? AND date BETWEEN ? AND ?', (s['student_id'], subject, class_name, start, end)).fetchall()
		total = len(rows)
		attended = sum(1 for r in rows if r['status'] == 'Present')
		pct = round((attended / total * 100), 2) if total > 0 else 0.0
		rows_out.append((s['roll_no'], s['name'], total, attended, pct))
	buf = BytesIO()
	width, height = letter
	p = canvas.Canvas(buf, pagesize=letter)
	p.setFont('Helvetica-Bold', 12)
	p.drawString(72, height - 72, f'Attendance Report: {class_name} - {subject}')
	p.setFont('Helvetica', 10)
	p.drawString(72, height - 88, f'From {start} to {end}')
	# table headers
	y = height - 110
	headers = ['Roll No','Name','Total','Attended','%']
	col_x = [72, 150, 400, 450, 500]
	p.setFont('Helvetica-Bold', 10)
	for i, htxt in enumerate(headers):
		p.drawString(col_x[i], y, htxt)
	p.line(72, y-2, 540, y-2)
	p.setFont('Helvetica', 10)
	y -= 14
	for rno, name, total, att, pct in rows_out:
		if pct < 40:
			p.setFillColorRGB(0.5, 0.0, 0.0)
		else:
			p.setFillColorRGB(0, 0, 0)
		p.drawString(col_x[0], y, str(rno))
		p.drawString(col_x[1], y, str(name)[:36])
		p.drawRightString(col_x[2]+20, y, str(total))
		p.drawRightString(col_x[3]+20, y, str(att))
		p.drawRightString(col_x[4]+20, y, str(pct))
		y -= 14
		if y < 72:
			p.showPage()
			p.setFont('Helvetica', 10)
			y = height - 72
	p.showPage()
	p.save()
	buf.seek(0)
	return send_file(buf, mimetype='application/pdf', as_attachment=True, download_name=f'attendance_{class_name}_{subject}_{start}_to_{end}.pdf')


# Student views

@app.route('/student/dashboard')
@login_required(role='student')
def student_dashboard():
	db = get_db()
	student = session['user']
	period = request.args.get('period', 'weekly')
	start = request.args.get('start')
	end = request.args.get('end')
	if request.args.get('today') == '1':
		end_date = datetime.now().date()
		start_date = end_date
		start = start_date.strftime('%Y-%m-%d')
		end = end_date.strftime('%Y-%m-%d')
	elif not start or not end:
		end_date = datetime.now().date()
		if period == 'daily':
			start_date = end_date
		elif period == 'monthly':
			start_date = end_date - timedelta(days=29)
		else:
			start_date = end_date - timedelta(days=6)
		start = start_date.strftime('%Y-%m-%d')
		end = end_date.strftime('%Y-%m-%d')
	rows = db.execute('SELECT date, subject, status FROM attendance WHERE student_id = ? AND date BETWEEN ? AND ? ORDER BY date DESC',
					 (student['id'], start, end)).fetchall()
	# subject-wise percentages in period - derive dynamically from teacher_assignments for student's class
	subject_rows = db.execute('SELECT DISTINCT subject FROM teacher_assignments WHERE class = ? ORDER BY subject', (student['class'],)).fetchall()
	all_subjects = [r['subject'] for r in subject_rows] if subject_rows else []
	# Fall back to subjects observed in attendance if no assignments found
	if not all_subjects:
		att_subj_rows = db.execute('SELECT DISTINCT subject FROM attendance WHERE class = ? ORDER BY subject', (student['class'],)).fetchall()
		all_subjects = [r['subject'] for r in att_subj_rows]
	# Course code mapping (case-insensitive, simple normalization)
	subject_code_map = {
		'fbda': '230GDIM22',
		'bse': '230USYB01',
		'wireless communication': '230GETB38',
		'e-commerce': '230VBCB14',
		'e commerce': '230VBCB14',
		'ccf': '250GCAM65',
		'field project': '231GCAM24',
		'project': '231GCAM24',
	}
	def normalize(name: str) -> str:
		return (name or '').strip().lower().replace('\u00a0',' ').replace('  ',' ')
	percents = []
	for sub in all_subjects:
		rows_sub = db.execute('SELECT status FROM attendance WHERE student_id = ? AND subject = ? AND date BETWEEN ? AND ?',
							 (student['id'], sub, start, end)).fetchall()
		total = len(rows_sub)
		attended = sum(1 for r in rows_sub if r['status'] == 'Present')
		percent = (attended / total * 100) if total > 0 else 0.0
		code = subject_code_map.get(normalize(sub), '')
		percents.append({
			'subject': sub,
			'code': code,
			'total': total,
			'attended': attended,
			'percent': round(percent, 2)
		})
	# alert threshold
	below = [p for p in percents if p['percent'] < 75.0]
	return render_template('student_dashboard.html', rows=rows, percents=percents, period=period, start=start, end=end, below=below)


# Admin views

@app.route('/admin/reports')
@login_required(role='admin')
def admin_reports():
	db = get_db()
	class_name = request.args.get('class')
	subject = request.args.get('subject')
	search = request.args.get('search', '').strip()
	end = request.args.get('end')
	start = request.args.get('start')
	if not start or not end:
		end_date = datetime.now().date()
		start_date = end_date - timedelta(days=6)
		start = start_date.strftime('%Y-%m-%d')
		end = end_date.strftime('%Y-%m-%d')
	# derive classes/subjects options
	classes = [r['class'] for r in get_db().execute('SELECT DISTINCT class FROM students').fetchall()]
	subjects = [r['subject'] for r in get_db().execute('SELECT DISTINCT subject FROM teacher_assignments').fetchall()]
	# base students list
	query = 'SELECT * FROM students WHERE 1=1'
	params = []
	if class_name:
		query += ' AND class = ?'
		params.append(class_name)
	if search:
		query += ' AND (roll_no LIKE ? OR name LIKE ?)'
		params.extend([f'%{search}%', f'%{search}%'])
	query += ' ORDER BY roll_no'
	students = db.execute(query, params).fetchall()
	report = []
	for s in students:
		rows = db.execute('SELECT status FROM attendance WHERE student_id = ? AND date BETWEEN ? AND ?' + (' AND subject = ?' if subject else ''),
						 ([s['student_id'], start, end] + ([subject] if subject else []))).fetchall()
		total = len(rows)
		attended = sum(1 for r in rows if r['status'] == 'Present')
		percent = (attended / total * 100) if total > 0 else 0.0
		report.append({'roll_no': s['roll_no'], 'name': s['name'], 'class': s['class'], 'total': total, 'attended': attended, 'percent': round(percent, 2)})
	# defaulters
	defaulters = [r for r in report if r['percent'] < 75.0]
	return render_template('admin_reports.html', report=report, defaulters=defaulters, classes=classes, subjects=subjects, class_name=class_name, subject=subject, search=search, start=start, end=end)


@app.route('/admin/export/csv')
@login_required(role='admin')
def admin_export_csv():
	import csv
	db = get_db()
	class_name = request.args.get('class')
	subject = request.args.get('subject')
	end = request.args.get('end')
	start = request.args.get('start')
	if not start or not end:
		end_date = datetime.now().date()
		start_date = end_date - timedelta(days=6)
		start = start_date.strftime('%Y-%m-%d')
		end = end_date.strftime('%Y-%m-%d')
	# gather report same as admin_reports
	query_students = 'SELECT * FROM students'
	params_students = []
	if class_name:
		query_students += ' WHERE class = ?'
		params_students.append(class_name)
	students = db.execute(query_students, params_students).fetchall()
	output = BytesIO()
	writer = csv.writer(output)
	writer.writerow(['Roll No', 'Name', 'Class', 'Total Lectures', 'Attended', '% Attendance'])
	for s in students:
		rows = db.execute('SELECT status FROM attendance WHERE student_id = ? AND date BETWEEN ? AND ?' + (' AND subject = ?' if subject else ''),
						 ([s['student_id'], start, end] + ([subject] if subject else []))).fetchall()
		total = len(rows)
		attended = sum(1 for r in rows if r['status'] == 'Present')
		percent = (attended / total * 100) if total > 0 else 0.0
		writer.writerow([s['roll_no'], s['name'], s['class'], total, attended, f'{round(percent,2)}%'])
	output.seek(0)
	return send_file(output, mimetype='text/csv', as_attachment=True, download_name='attendance_report.csv')


@app.route('/admin/export/pdf')
@login_required(role='admin')
def admin_export_pdf():
	# Minimal PDF export of defaulters
	db = get_db()
	end_date = datetime.now().date()
	start_date = end_date - timedelta(days=6)
	start = request.args.get('start', start_date.strftime('%Y-%m-%d'))
	end = request.args.get('end', end_date.strftime('%Y-%m-%d'))
	rows = db.execute('SELECT s.roll_no, s.name, s.class, a.status FROM attendance a JOIN students s ON a.student_id = s.student_id WHERE a.date BETWEEN ? AND ? ORDER BY s.roll_no',
					 (start, end)).fetchall()
	buffer = BytesIO()
	p = canvas.Canvas(buffer, pagesize=letter)
	width, height = letter
	p.setFont('Helvetica-Bold', 14)
	p.drawString(72, height - 72, 'Attendance Report (Defaulters <75%)')
	p.setFont('Helvetica', 10)
	y = height - 100
	counts = {}
	for r in rows:
		key = (r['roll_no'], r['name'], r['class'])
		counts.setdefault(key, {'total': 0, 'attended': 0})
		counts[key]['total'] += 1
		if r['status'] == 'Present':
			counts[key]['attended'] += 1
	for (roll_no, name, cls), stat in sorted(counts.items()):
		percent = (stat['attended'] / stat['total'] * 100) if stat['total'] > 0 else 0
		if percent < 75:
			line = f"{roll_no}  {name}  {cls}  {stat['attended']}/{stat['total']}  {round(percent,2)}%"
			p.drawString(72, y, line)
			y -= 16
			if y < 72:
				p.showPage()
				p.setFont('Helvetica', 10)
				y = height - 72
	p.showPage()
	p.save()
	buffer.seek(0)
	return send_file(buffer, mimetype='application/pdf', as_attachment=True, download_name='defaulters.pdf')


@app.route('/admin/students/import', methods=['GET','POST'])
@login_required(role=('admin','hod'))
def admin_students_import():
	db = get_db()
	classes = [r['class'] for r in db.execute('SELECT DISTINCT class FROM students').fetchall()]
	classes = sorted(set(classes + ['SYMCA Div A','SYMCA Div B']))
	if request.method == 'POST':
		cls = request.form.get('class')
		text = (request.form.get('data') or '').strip()
		if not cls or not text:
			flash('Please choose class and paste the data.', 'error')
			return render_template('admin_students_import.html', classes=classes)
		added = 0
		updated = 0
		for raw in text.splitlines():
			line = raw.strip()
			if not line:
				continue
			roll = prn = name = None
			if ',' in line:
				parts = [p.strip() for p in line.split(',') if p.strip()]
				if len(parts) >= 3:
					roll, prn = parts[0], parts[1]
					name = ','.join(parts[2:]).strip()
			else:
				parts = line.split()
				if len(parts) >= 3:
					roll, prn = parts[0], parts[1]
					name = ' '.join(parts[2:])
			if not roll or not prn or not name:
				continue
			row = db.execute('SELECT student_id FROM students WHERE roll_no = ?', (roll,)).fetchone()
			if row:
				db.execute('UPDATE students SET prn = ?, name = ?, class = ?, semester = ? WHERE student_id = ?', (prn, name, cls, 2, row['student_id']))
				updated += 1
			else:
				db.execute('INSERT INTO students (roll_no, prn, name, class, semester, password_hash) VALUES (?,?,?,?,?,?)', (roll, prn, name, cls, 2, pbkdf2_sha256.hash('Test@123')))
				added += 1
		db.commit()
		flash(f'Import complete. Added {added}, Updated {updated}.', 'success')
		return redirect(url_for('admin_reports', **{'class': cls}))
	return render_template('admin_students_import.html', classes=classes)


@app.route('/sheet')
def sheet_reports():
	db = get_db()
	class_name = request.args.get('class')
	subject = request.args.get('subject')
	search = request.args.get('search', '').strip()
	end = request.args.get('end')
	start = request.args.get('start')
	if not start or not end:
		end_date = datetime.now().date()
		start_date = end_date - timedelta(days=6)
		start = start_date.strftime('%Y-%m-%d')
		end = end_date.strftime('%Y-%m-%d')
	classes = [r['class'] for r in get_db().execute('SELECT DISTINCT class FROM students').fetchall()]
	subjects = [r['subject'] for r in get_db().execute('SELECT DISTINCT subject FROM teacher_assignments').fetchall()]
	query = 'SELECT * FROM students WHERE 1=1'
	params = []
	if class_name:
		query += ' AND class = ?'
		params.append(class_name)
	if search:
		query += ' AND (roll_no LIKE ? OR name LIKE ?)'
		params.extend([f'%{search}%', f'%{search}%'])
	query += ' ORDER BY roll_no'
	students = db.execute(query, params).fetchall()
	report = []
	for s in students:
		rows = db.execute('SELECT status FROM attendance WHERE student_id = ? AND date BETWEEN ? AND ?' + (' AND subject = ?' if subject else ''),
						 ([s['student_id'], start, end] + ([subject] if subject else []))).fetchall()
		total = len(rows)
		attended = sum(1 for r in rows if r['status'] == 'Present')
		percent = (attended / total * 100) if total > 0 else 0.0
		report.append({'roll_no': s['roll_no'], 'name': s['name'], 'class': s['class'], 'total': total, 'attended': attended, 'percent': round(percent, 2)})
	defaulters = [r for r in report if r['percent'] < 75.0]
	return render_template('admin_reports.html', report=report, defaulters=defaulters, classes=classes, subjects=subjects, class_name=class_name, subject=subject, search=search, start=start, end=end, page_title='Attendance Sheet', is_sheet=True)


@app.route('/sheet/export/csv')
def sheet_export_csv():
	import csv
	db = get_db()
	class_name = request.args.get('class')
	subject = request.args.get('subject')
	end = request.args.get('end')
	start = request.args.get('start')
	if not start or not end:
		end_date = datetime.now().date()
		start_date = end_date - timedelta(days=6)
		start = start_date.strftime('%Y-%m-%d')
		end = end_date.strftime('%Y-%m-%d')
	query_students = 'SELECT * FROM students'
	params_students = []
	if class_name:
		query_students += ' WHERE class = ?'
		params_students.append(class_name)
	students = db.execute(query_students, params_students).fetchall()
	output = BytesIO()
	writer = csv.writer(StringIO())
	# We need a BytesIO-compatible buffer; write text then encode
	text_buf = StringIO()
	w = csv.writer(text_buf)
	w.writerow(['Roll No', 'Name', 'Class', 'Total Lectures', 'Attended', '% Attendance', 'From', 'To', 'Subject'])
	for s in students:
		rows = db.execute('SELECT status FROM attendance WHERE student_id = ? AND date BETWEEN ? AND ?' + (' AND subject = ?' if subject else ''),
						 ([s['student_id'], start, end] + ([subject] if subject else []))).fetchall()
		total = len(rows)
		attended = sum(1 for r in rows if r['status'] == 'Present')
		percent = (attended / total * 100) if total > 0 else 0.0
		w.writerow([s['roll_no'], s['name'], s['class'], total, attended, f'{round(percent,2)}%', start, end, subject or 'All'])
	data = text_buf.getvalue().encode('utf-8')
	return send_file(BytesIO(data), mimetype='text/csv; charset=utf-8', as_attachment=True, download_name='attendance_sheet.csv')


@app.route('/sheet/export/pdf')
def sheet_export_pdf():
	# reuse admin defaulters export for selected range
	db = get_db()
	end_date = datetime.now().date()
	start_date = end_date - timedelta(days=6)
	start = request.args.get('start', start_date.strftime('%Y-%m-%d'))
	end = request.args.get('end', end_date.strftime('%Y-%m-%d'))
	rows = db.execute('SELECT s.roll_no, s.name, s.class, a.status FROM attendance a JOIN students s ON a.student_id = s.student_id WHERE a.date BETWEEN ? AND ? ORDER BY s.roll_no',
					 (start, end)).fetchall()
	buffer = BytesIO()
	p = canvas.Canvas(buffer, pagesize=letter)
	width, height = letter
	p.setFont('Helvetica-Bold', 14)
	p.drawString(72, height - 72, 'Attendance Sheet (Defaulters <75%)')
	p.setFont('Helvetica', 10)
	y = height - 100
	counts = {}
	for r in rows:
		key = (r['roll_no'], r['name'], r['class'])
		counts.setdefault(key, {'total': 0, 'attended': 0})
		counts[key]['total'] += 1
		if r['status'] == 'Present':
			counts[key]['attended'] += 1
	for (roll_no, name, cls), stat in sorted(counts.items()):
		percent = (stat['attended'] / stat['total'] * 100) if stat['total'] > 0 else 0
		if percent < 75:
			line = f"{roll_no}  {name}  {cls}  {stat['attended']}/{stat['total']}  {round(percent,2)}%"
			p.drawString(72, y, line)
			y -= 16
			if y < 72:
				p.showPage()
				p.setFont('Helvetica', 10)
				y = height - 72
	p.showPage()
	p.save()
	buffer.seek(0)
	return send_file(buffer, mimetype='application/pdf', as_attachment=True, download_name='attendance_sheet_defaulters.pdf')


# Teacher change password
@app.route('/teacher/change-password', methods=['GET','POST'])
@login_required(role='teacher')
def teacher_change_password():
	db = get_db()
	teacher = session['user']
	if request.method == 'POST':
		current = request.form.get('current', '')
		newpass = request.form.get('newpass', '')
		confirm = request.form.get('confirm', '')
		row = db.execute('SELECT password_hash FROM teachers WHERE teacher_id = ?', (teacher['id'],)).fetchone()
		if not row or not pbkdf2_sha256.verify(current, row['password_hash']):
			flash('Current password is incorrect', 'error')
			return render_template('teacher_change_password.html')
		if not newpass or newpass != confirm:
			flash('Passwords do not match', 'error')
			return render_template('teacher_change_password.html')
		db.execute('UPDATE teachers SET password_hash = ? WHERE teacher_id = ?', (pbkdf2_sha256.hash(newpass), teacher['id']))
		db.commit()
		flash('Password updated', 'success')
		return redirect(url_for('teacher_select'))
	return render_template('teacher_change_password.html')


# Admin import teachers
@app.route('/admin/teachers/import', methods=['GET','POST'])
@login_required(role=('admin','hod'))
def admin_teachers_import():
	db = get_db()
	classes = [r['class'] for r in db.execute('SELECT DISTINCT class FROM students').fetchall()]
	classes = sorted(set(classes + ['SYMCA Div A','SYMCA Div B']))
	if request.method == 'POST':
		text = (request.form.get('data') or '').strip()
		if not text:
			flash('Paste teacher data to import', 'error')
			return render_template('admin_teachers_import.html', classes=classes)
		added = 0
		updated = 0
		for raw in text.splitlines():
			line = raw.strip()
			if not line:
				continue
			# CSV: name,phone,password,subject,class  (subject,class can repeat multiple lines per teacher)
			parts = [p.strip() for p in line.split(',')]
			if len(parts) < 5:
				continue
			name, phone, password, subject, cls = parts[0], parts[1], parts[2], parts[3], ','.join(parts[4:]) if len(parts)>5 else parts[4]
			row = db.execute('SELECT teacher_id FROM teachers WHERE phone = ? OR name = ?', (phone, name)).fetchone()
			if row:
				db.execute('UPDATE teachers SET name = ?, phone = ?, password_hash = ? WHERE teacher_id = ?', (name, phone, pbkdf2_sha256.hash(password), row['teacher_id']))
				teacher_id = row['teacher_id']
				updated += 1
			else:
				db.execute('INSERT INTO teachers (name, phone, password_hash) VALUES (?,?,?)', (name, phone, pbkdf2_sha256.hash(password)))
				teacher_id = db.execute('SELECT last_insert_rowid() AS id').fetchone()['id']
				added += 1
			db.execute('INSERT OR IGNORE INTO teacher_assignments (teacher_id, subject, class) VALUES (?,?,?)', (teacher_id, subject, cls))
		db.commit()
		flash(f'Teachers import complete. Added {added}, Updated {updated}.', 'success')
		return redirect(url_for('admin_reports'))
	return render_template('admin_teachers_import.html', classes=classes)


@app.route('/hod', methods=['GET','POST'])
@login_required(role='hod')
def hod_dashboard():
	# minimal dashboard with links to import/remove
	return render_template('hod_dashboard.html')


@app.route('/hod/class/import', methods=['GET','POST'])
@login_required(role='hod')
def hod_class_import():
    db = get_db()
    # Offer some default class suggestions based on existing data
    existing_classes = [r['class'] for r in db.execute('SELECT DISTINCT class FROM students').fetchall()]
    suggestions = sorted(set(existing_classes + ['SYMCA Div A','SYMCA Div B']))
    if request.method == 'POST':
        import csv
        class_name = (request.form.get('class') or '').strip()
        semester = request.form.get('semester') or '2'
        text_data = (request.form.get('data') or '').strip()
        file = request.files.get('file') if hasattr(request, 'files') else None
        assignments_text = (request.form.get('assignments') or '').strip()

        errors = []
        if not class_name:
            flash('Please provide a class name.', 'error')
            return render_template('hod_class_import.html', suggestions=suggestions)

        # Collect student rows from textarea and/or file
        student_rows = []
        if text_data:
            student_rows.extend(text_data.splitlines())
        if file and getattr(file, 'filename', ''):
            try:
                raw = file.stream.read()
                text = raw.decode('utf-8-sig')
                reader = csv.reader(text.splitlines())
                for row in reader:
                    if not row:
                        continue
                    student_rows.append(','.join([str(c).strip() for c in row if str(c).strip() != '']))
            except Exception as exc:
                errors.append(f'Failed to read CSV file: {exc}')

        if not student_rows:
            flash('Provide students via paste or CSV file.', 'error')
            return render_template('hod_class_import.html', suggestions=suggestions, class_name=class_name, semester=semester, errors=errors)

        added = 0
        updated = 0
        line_no = 0
        for raw in student_rows:
            line_no += 1
            line = (raw or '').strip()
            if not line:
                continue
            roll = prn = name = None
            if ',' in line:
                parts = [p.strip() for p in line.split(',') if p.strip()]
                if len(parts) >= 3:
                    roll, prn, name = parts[0], parts[1], ','.join(parts[2:]).strip()
            else:
                parts = line.split()
                if len(parts) >= 3:
                    roll, prn = parts[0], parts[1]
                    name = ' '.join(parts[2:])
            if not roll or not prn or not name:
                errors.append(f'Line {line_no}: invalid format. Expect roll, prn, name.')
                continue
            try:
                row = db.execute('SELECT student_id FROM students WHERE roll_no = ?', (roll,)).fetchone()
                if row:
                    db.execute('UPDATE students SET prn = ?, name = ?, class = ?, semester = ? WHERE student_id = ?', (prn, name, class_name, int(semester or 2), row['student_id']))
                    updated += 1
                else:
                    db.execute('INSERT INTO students (roll_no, prn, name, class, semester, password_hash) VALUES (?,?,?,?,?,?)', (roll, prn, name, class_name, int(semester or 2), pbkdf2_sha256.hash('Test@123')))
                    added += 1
            except sqlite3.Error as exc:
                errors.append(f'Line {line_no}: DB error for roll {roll}: {exc}')
        db.commit()

        # Process subject-teacher assignments (optional)
        assigned = 0
        skipped_assign = 0
        if assignments_text:
            for idx, raw in enumerate(assignments_text.splitlines(), start=1):
                line = raw.strip()
                if not line:
                    continue
                parts = [p.strip() for p in line.split(',') if p.strip()]
                if len(parts) < 2:
                    errors.append(f'Assignment line {idx}: expected "subject, teacher_phone_or_name"')
                    skipped_assign += 1
                    continue
                subject, teacher_key = parts[0], ','.join(parts[1:])
                # Lookup teacher: first by phone (digits only), then by exact name or phone
                key_digits = ''.join(ch for ch in teacher_key if ch.isdigit())
                teacher_row = None
                if key_digits:
                    teacher_row = db.execute('SELECT teacher_id FROM teachers WHERE REPLACE(phone, " ", "") = ?', (key_digits,)).fetchone()
                if not teacher_row:
                    teacher_row = db.execute('SELECT teacher_id FROM teachers WHERE name = ? OR phone = ?', (teacher_key, teacher_key)).fetchone()
                if not teacher_row:
                    errors.append(f'Assignment line {idx}: teacher not found for "{teacher_key}"')
                    skipped_assign += 1
                    continue
                try:
                    db.execute('INSERT OR IGNORE INTO teacher_assignments (teacher_id, subject, class) VALUES (?,?,?)', (teacher_row['teacher_id'], subject, class_name))
                    assigned += 1
                except sqlite3.Error as exc:
                    errors.append(f'Assignment line {idx}: DB error: {exc}')
                    skipped_assign += 1
            db.commit()

        # Summarize
        flash(f'Class "{class_name}" import: Added {added}, Updated {updated}. Assignments added {assigned}, Skipped {skipped_assign}.', 'success')
        if errors:
            # Keep errors visible on page
            return render_template('hod_class_import.html', suggestions=suggestions, class_name=class_name, semester=semester, errors=errors)
        return redirect(url_for('admin_reports', **{'class': class_name}))
    return render_template('hod_class_import.html', suggestions=suggestions)


@app.route('/hod/remove/student', methods=['POST'])
@login_required(role='hod')
def hod_remove_student():
	db = get_db()
	roll_or_prn = (request.form.get('id') or '').strip()
	row = db.execute('SELECT student_id FROM students WHERE roll_no = ? OR prn = ?', (roll_or_prn, roll_or_prn)).fetchone()
	if row:
		db.execute('DELETE FROM students WHERE student_id = ?', (row['student_id'],))
		db.commit()
		flash('Student removed', 'success')
	else:
		flash('Student not found', 'error')
	return redirect(url_for('hod_dashboard'))


@app.route('/hod/remove/teacher', methods=['POST'])
@login_required(role='hod')
def hod_remove_teacher():
	db = get_db()
	phone = (request.form.get('phone') or '').strip().replace(' ', '')
	row = db.execute('SELECT teacher_id FROM teachers WHERE phone = ?', (phone,)).fetchone()
	if row:
		db.execute('DELETE FROM teachers WHERE teacher_id = ?', (row['teacher_id'],))
		db.commit()
		flash('Teacher removed', 'success')
	else:
		flash('Teacher not found', 'error')
	return redirect(url_for('hod_dashboard'))


@app.route('/hod/update/teacher-phone', methods=['POST'])
@login_required(role='hod')
def hod_update_teacher_phone():
	db = get_db()
	key = (request.form.get('key') or '').strip()
	new_phone_raw = (request.form.get('new_phone') or '').strip()
	if not key or not new_phone_raw:
		flash('Provide teacher name/phone and new phone.', 'error')
		return redirect(url_for('hod_dashboard'))
	new_phone = new_phone_raw.replace(' ', '')
	if not new_phone.isdigit() or len(new_phone) < 6:
		flash('Enter a valid new phone number.', 'error')
		return redirect(url_for('hod_dashboard'))
	# Lookup by digits in key (phone) first, then by exact name or phone
	key_digits = ''.join(ch for ch in key if ch.isdigit())
	row = None
	if key_digits:
		row = db.execute('SELECT teacher_id FROM teachers WHERE REPLACE(phone, " ", "") = ?', (key_digits,)).fetchone()
	if not row:
		row = db.execute('SELECT teacher_id FROM teachers WHERE name = ? OR phone = ?', (key, key)).fetchone()
	if not row:
		flash('Teacher not found for given name/phone.', 'error')
		return redirect(url_for('hod_dashboard'))
	try:
		db.execute('UPDATE teachers SET phone = ? WHERE teacher_id = ?', (new_phone, row['teacher_id']))
		db.commit()
		flash('Teacher phone updated.', 'success')
	except sqlite3.IntegrityError:
		flash('Phone number already in use by another teacher.', 'error')
	except sqlite3.Error as exc:
		flash(f'Failed to update phone: {exc}', 'error')
	return redirect(url_for('hod_dashboard'))


if __name__ == '__main__':
	with app.app_context():
		init_db()
		seed_if_empty()
	app.run(debug=True)
