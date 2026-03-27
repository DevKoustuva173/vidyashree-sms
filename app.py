from flask import url_for
from functools import wraps
from flask import Flask, render_template, request, redirect, session, send_file
import pandas as pd
import sqlite3
from io import BytesIO
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os
from werkzeug.utils import secure_filename
import re

app = Flask(__name__)
app.secret_key = "school_secret_key_2026"


# Login protection decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "admin" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function


# Database connection helper
def get_db():
    conn = sqlite3.connect("school.db")
    conn.row_factory = sqlite3.Row
    return conn


# Login
@app.route("/", methods=["GET","POST"])
def login():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM users WHERE username=?", (username,))
        user = cursor.fetchone()

        conn.close()

        if user and check_password_hash(user["password"], password):
            session["admin"] = username
            return redirect(url_for("dashboard"))
        else:
            return render_template("login.html", error="Invalid username or password")

    return render_template("login.html")


# Logout
@app.route("/logout")
@login_required
def logout():
    
    session.pop("admin", None)
    return redirect(url_for("login"))


#forgot_password
@app.route("/forgot_password", methods=["GET","POST"])
def forgot_password():

    if request.method == "POST":

        username = request.form["username"]
        security_answer = request.form["security_answer"]
        new_password = generate_password_hash(request.form["password"])

        conn = get_db()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT * FROM users WHERE username=? AND security_answer=?",
            (username, security_answer)
        )

        user = cursor.fetchone()

        if user:
            cursor.execute(
                "UPDATE users SET password=? WHERE username=?",
                (new_password, username)
            )
            conn.commit()
            conn.close()
            return redirect(url_for("login"))

        conn.close()
        return render_template("forgot_password.html", error="Invalid username or security answer")

    return render_template("forgot_password.html")


#profile
@app.route("/profile", methods=["GET","POST"])
@login_required
def profile():

    if request.method == "POST":

        old_password = request.form["old_password"]
        new_password = request.form["new_password"]
        confirm_password = request.form["confirm_password"]

        if new_password != confirm_password:
            return render_template("profile.html", error="New passwords do not match")

        conn = get_db()
        cursor = conn.cursor()

        cursor.execute(
        "SELECT password FROM users WHERE username=?",
        (session["admin"],)
        )

        user = cursor.fetchone()

        if user and check_password_hash(user["password"], old_password):

            hashed = generate_password_hash(new_password)

            cursor.execute(
            "UPDATE users SET password=? WHERE username=?",
            (hashed, session["admin"])
            )

            conn.commit()
            conn.close()

            return redirect(url_for("dashboard"))

        conn.close()

        return render_template("profile.html", error="Wrong old password")

    return render_template("profile.html")


# Dashboard
@app.route("/dashboard")
@login_required
def dashboard():
    
    conn = get_db()
    cursor = conn.cursor()

    # Total students
    cursor.execute("SELECT COUNT(*) FROM students")
    total_students = cursor.fetchone()[0]

    # Total attendance records
    cursor.execute("SELECT COUNT(*) FROM attendance")
    total_attendance = cursor.fetchone()[0]

    # Total fees
    cursor.execute("SELECT COALESCE(SUM(amount),0) FROM fees")
    total_fees = cursor.fetchone()[0]

    # Students per class
    cursor.execute("SELECT class, COUNT(*) FROM students GROUP BY class ORDER BY class")
    class_data = cursor.fetchall()

    classes = [row[0] for row in class_data]
    class_counts = [row[1] for row in class_data]

    conn.close()

    return render_template(
        "dashboard.html",
        total_students=total_students,
        total_attendance=total_attendance,
        total_fees=total_fees,
        classes=classes,
        class_counts=class_counts
    )

# students
@app.route("/students", methods=["GET","POST"])
@login_required
def students():

    if request.method == "POST":

        name = request.form["name"]
        student_class = request.form["class"]
        section = request.form.get("section", "")
        dob = request.form["dob"]
        phone = request.form["phone"]
        address = request.form["address"]

        # Name validation
        if not re.match(r'^[A-Za-z .-]+$', name):
            return render_template("students.html", error="Invalid name", name=name, student_class=student_class, section=section, dob=dob, phone=phone, address=address)
        
        # Class validation
        if not re.match(r'^[A-Za-z0-9 ]+$', student_class):
            return render_template("students.html", error="Invalid class (only letters and numbers allowed)")

        # Address validation
        if not re.match(r'^[A-Za-z0-9 ,.-]+$', address):
            return render_template("students.html", error="Invalid address")

        photo = request.files["photo"]

        filename = None

        if photo and photo.filename != "":
            filename = secure_filename(photo.filename)
            photo.save(os.path.join("static/uploads", filename))

        conn = get_db()
        cursor = conn.cursor()

        cursor.execute(
        "INSERT INTO students(name,class,section,dob,phone,address,photo) VALUES (?,?,?,?,?,?,?)",
        (name, student_class, section, dob, phone, address, filename)
        )

        conn.commit()
        conn.close()

        return redirect("/student_list")

    return render_template("students.html")


# Attendance
@app.route("/attendance", methods=["GET","POST"])
@login_required
def attendance():

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT id, name FROM students")
    students = cursor.fetchall()

    if request.method == "POST":

        student_id = request.form["student_id"]
        date = request.form["date"]
        status = request.form["status"]

        cursor.execute(
        "INSERT INTO attendance(student_id,date,status) VALUES (?,?,?)",
        (student_id, date, status)
        )

        conn.commit()
        conn.close()

        return redirect("/attendance")

    conn.close()

    return render_template("attendance.html", students=students)


# Attendance List
@app.route("/attendance_list")
@login_required
def attendance_list():

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT attendance.id, students.name, attendance.date, attendance.status
        FROM attendance
        JOIN students ON attendance.student_id = students.id
    """)

    records = cursor.fetchall()

    conn.close()

    return render_template("attendance_list.html", records=records)


# Student List
@app.route('/student_list')
@login_required
def student_list():
    try:
        page = int(request.args.get('page', 1))
    except:
        page = 1
    per_page = 10
    offset = (page - 1) * per_page

    search = request.args.get('search', '')

    conn = get_db()

    if search:
        students = conn.execute(
            "SELECT * FROM students WHERE name LIKE ? LIMIT ? OFFSET ?",
            ('%' + search + '%', per_page, offset)
        ).fetchall()

        total = conn.execute(
            "SELECT COUNT(*) FROM students WHERE name LIKE ?",
            ('%' + search + '%',)
        ).fetchone()[0]
    else:
        students = conn.execute(
            "SELECT * FROM students LIMIT ? OFFSET ?",
            (per_page, offset)
        ).fetchall()

        total = conn.execute(
            "SELECT COUNT(*) FROM students"
        ).fetchone()[0]

    conn.close()

    total_pages = (total + per_page - 1) // per_page

    return render_template(
        'student_list.html',
        students=students,
        total_students=total,
        page=page,
        total_pages=total_pages
    )


# Delete Student
@app.route("/delete_student/<int:id>", methods=["POST"])
@login_required
def delete_student(id):

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM students WHERE id = ?", (id,))

    conn.commit()
    conn.close()

    return redirect("/student_list")


# Edit Student
@app.route("/edit_student/<int:id>", methods=["GET","POST"])
@login_required
def edit_student(id):

    conn = get_db()
    cursor = conn.cursor()

    if request.method == "POST":

        name = request.form["name"]
        student_class = request.form["class"]
        section = request.form["section"]
        dob = request.form["dob"]
        phone = request.form["phone"]
        address = request.form["address"]

        cursor.execute("""
        UPDATE students
        SET name=?, class=?, section=?, dob=?, phone=?, address=?
        WHERE id=?
        """, (name, student_class, section, dob, phone, address, id))

        conn.commit()
        conn.close()

        return redirect("/student_list")

    cursor.execute("SELECT * FROM students WHERE id=?", (id,))
    student = cursor.fetchone()

    conn.close()

    return render_template("edit_student.html", student=student)


# Fees Entry
@app.route("/fees", methods=["GET","POST"])
@login_required
def fees():

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT id, name FROM students")
    students = cursor.fetchall()

    if request.method == "POST":

        student_id = request.form["student_id"]
        amount = request.form["amount"]
        date = request.form["date"]

        cursor.execute(
        "INSERT INTO fees(student_id,amount,date) VALUES (?,?,?)",
        (student_id, amount, date)
        )

        conn.commit()
        conn.close()

        return redirect("/fees")

    conn.close()

    return render_template("fees.html", students=students)


# Fees List
@app.route("/fees_list")
@login_required
def fees_list():

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT fees.id, students.name, fees.amount, fees.date
        FROM fees
        JOIN students ON fees.student_id = students.id
    """)

    records = cursor.fetchall()

    conn.close()

    return render_template("fees_list.html", records=records)

# export_students
@app.route('/export_students')
@login_required
def export_students():
    conn = get_db()
    students = conn.execute("SELECT * FROM students").fetchall()
    conn.close()

    df = pd.DataFrame(students)

    output = BytesIO()
    df.to_excel(output, index=False)
    output.seek(0)

    filename = f"students_{datetime.now().date()}.xlsx"

    return send_file(
        output,
        download_name=filename,
        as_attachment=True,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


if __name__ == "__main__":
    app.run(debug=False)