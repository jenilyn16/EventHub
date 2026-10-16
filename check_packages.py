import sqlite3
import os

from config import DB, CATEGORIES
from database import seed_packages

db_path = os.path.abspath(DB)

print("Updating database:")
print(db_path)

con = sqlite3.connect(db_path)
cur = con.cursor()

print("Deleting old packages...")

cur.execute("DELETE FROM packages")
cur.execute("DELETE FROM sqlite_sequence WHERE name='packages'")

print("Creating 600 packages...")

seed_packages(cur)

con.commit()

rows = cur.execute("""
    SELECT event_type, category, COUNT(*)
    FROM packages
    GROUP BY event_type, category
    ORDER BY event_type, category
""").fetchall()

print("\nPACKAGE COUNTS:")

for row in rows:
    print(row)

total = cur.execute(
    "SELECT COUNT(*) FROM packages"
).fetchone()[0]

print(f"\nTOTAL PACKAGES: {total}")

con.close()

print("\nDone!")