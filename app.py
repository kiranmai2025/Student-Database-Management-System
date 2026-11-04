from flask import Flask, render_template, request, redirect, url_for, flash, session
import sqlite3

app = Flask(__name__)
app.secret_key = 'hcl_interview_secret_key'
DATABASE = 'student.db'

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row  # Access columns by name like dictionaries
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    # Admins table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS admins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL
        )
    ''')
    # Default admin credentials
    cursor.execute('''
        INSERT OR IGNORE INTO admins (username, password)
        VALUES ('admin', 'admin123')
    ''')
    # Students table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            roll_no TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            department TEXT NOT NULL,
            residence_type TEXT NOT NULL,
            phone TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

# Initialize DB and tables on start
init_db()

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM admins WHERE username = ? AND password = ?", (username, password))
        admin = cursor.fetchone()
        conn.close()

        if admin:
            session['admin_logged_in'] = True
            session['username'] = admin['username']
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid admin credentials.', 'danger')

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully.', 'info')
    return redirect(url_for('login'))

@app.route('/')
def dashboard():
    if not session.get('admin_logged_in'):
        return redirect(url_for('login'))

    search_query = request.args.get('search', '').strip()
    conn = get_db_connection()
    cursor = conn.cursor()

    # Dashboard Metrics
    cursor.execute("SELECT COUNT(*) AS total FROM students")
    total_students = cursor.fetchone()['total']

    cursor.execute("SELECT COUNT(*) AS hostelers FROM students WHERE residence_type = 'Hosteler'")
    total_hostelers = cursor.fetchone()['hostelers']

    cursor.execute("SELECT COUNT(*) AS dayscholars FROM students WHERE residence_type = 'Day Scholar'")
    total_dayscholars = cursor.fetchone()['dayscholars']

    cursor.execute("SELECT department, COUNT(*) AS count FROM students GROUP BY department")
    dept_counts = cursor.fetchall()

    # Search & Filter
    if search_query:
        cursor.execute(
            "SELECT * FROM students WHERE roll_no LIKE ? OR name LIKE ? ORDER BY id DESC",
            (f"%{search_query}%", f"%{search_query}%")
        )
    else:
        cursor.execute("SELECT * FROM students ORDER BY id DESC")
    students = cursor.fetchall()
    conn.close()

    return render_template(
        'dashboard.html',
        students=students,
        total=total_students,
        hostelers=total_hostelers,
        dayscholars=total_dayscholars,
        dept_counts=dept_counts,
        search_query=search_query
    )

@app.route('/add', methods=['GET', 'POST'])
def add_student():
    if not session.get('admin_logged_in'):
        return redirect(url_for('login'))

    if request.method == 'POST':
        roll_no = request.form.get('roll_no').strip()
        name = request.form.get('name').strip()
        email = request.form.get('email').strip()
        department = request.form.get('department')
        residence_type = request.form.get('residence_type')
        phone = request.form.get('phone').strip()

        conn = get_db_connection()
        cursor = conn.cursor()

        # Duplicate Roll Number Validation
        cursor.execute("SELECT * FROM students WHERE roll_no = ?", (roll_no,))
        existing = cursor.fetchone()

        if existing:
            flash(f'Roll number "{roll_no}" already exists! Please enter a unique roll number.', 'danger')
            conn.close()
            return render_template('add_student.html')

        cursor.execute(
            """INSERT INTO students (roll_no, name, email, department, residence_type, phone)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (roll_no, name, email, department, residence_type, phone)
        )
        conn.commit()
        conn.close()

        flash('Student added successfully!', 'success')
        return redirect(url_for('dashboard'))

    return render_template('add_student.html')

@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit_student(id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == 'POST':
        roll_no = request.form.get('roll_no').strip()
        name = request.form.get('name').strip()
        email = request.form.get('email').strip()
        department = request.form.get('department')
        residence_type = request.form.get('residence_type')
        phone = request.form.get('phone').strip()

        # Duplicate Check
        cursor.execute("SELECT * FROM students WHERE roll_no = ? AND id != ?", (roll_no, id))
        duplicate = cursor.fetchone()

        if duplicate:
            flash(f'Roll number "{roll_no}" is already assigned to another student.', 'danger')
            cursor.execute("SELECT * FROM students WHERE id = ?", (id,))
            student = cursor.fetchone()
            conn.close()
            return render_template('edit_student.html', student=student)

        cursor.execute(
            """UPDATE students 
               SET roll_no=?, name=?, email=?, department=?, residence_type=?, phone=? 
               WHERE id=?""",
            (roll_no, name, email, department, residence_type, phone, id)
        )
        conn.commit()
        conn.close()

        flash('Student details updated successfully!', 'success')
        return redirect(url_for('dashboard'))

    cursor.execute("SELECT * FROM students WHERE id = ?", (id,))
    student = cursor.fetchone()
    conn.close()

    if not student:
        flash('Student record not found.', 'warning')
        return redirect(url_for('dashboard'))

    return render_template('edit_student.html', student=student)

@app.route('/delete/<int:id>', methods=['POST'])
def delete_student(id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM students WHERE id = ?", (id,))
    conn.commit()
    conn.close()

    flash('Student record deleted successfully!', 'info')
    return redirect(url_for('dashboard'))

if __name__ == '__main__':
    app.run(debug=True)