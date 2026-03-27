import sqlite3
from werkzeug.security import generate_password_hash

conn = sqlite3.connect('school.db')
cursor = conn.cursor()

# Create users table
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
id INTEGER PRIMARY KEY AUTOINCREMENT,
username TEXT UNIQUE,
password TEXT,
security_answer TEXT
)
""")

# Insert admin user
hashed_password = generate_password_hash("admin123")

cursor.execute("""
INSERT OR IGNORE INTO users (username,password,security_answer)
VALUES (?,?,?)
""", ('admin', hashed_password, 'jagannath'))

# Students table
cursor.execute("""
CREATE TABLE IF NOT EXISTS students(
id INTEGER PRIMARY KEY AUTOINCREMENT,
name TEXT,
class TEXT,
section TEXT,
dob TEXT,
phone TEXT,
address TEXT,
photo TEXT
)
""")


# Attendance table
cursor.execute("""
CREATE TABLE IF NOT EXISTS attendance(
id INTEGER PRIMARY KEY AUTOINCREMENT,
student_id INTEGER,
date TEXT,
status TEXT
)
""")

# Fees table
cursor.execute("""
CREATE TABLE IF NOT EXISTS fees(
id INTEGER PRIMARY KEY AUTOINCREMENT,
student_id INTEGER,
amount REAL,
date TEXT
)
""")

conn.commit()
conn.close()

print("Database tables created successfully")