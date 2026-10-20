
import sqlite3

connection = sqlite3.connect("expense_tracker.db")

columns = [
    row[1]
    for row in connection.execute("PRAGMA table_info(expenses)")
]

if "expense_date" not in columns:
    connection.execute(
        """
        ALTER TABLE expenses
        ADD COLUMN expense_date TEXT NOT NULL
        DEFAULT '2026-10-20'
        """
    )
    print("Added expense_date column.")
else:
    print("expense_date column already exists.")

connection.commit()
connection.close()

print("Database migration completed.")
