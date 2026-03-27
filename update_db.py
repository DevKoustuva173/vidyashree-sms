import sqlite3

conn = sqlite3.connect('school.db')
cursor = conn.cursor()

try:
    cursor.execute("ALTER TABLE students ADD COLUMN photo TEXT")
    print("Column added successfully")
except:
    print("Column already exists")

conn.commit()
conn.close()