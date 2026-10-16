import sqlite3
from config import DB, CATEGORIES
from database import seed_packages


con = sqlite3.connect(DB)
cur = con.cursor()

print("Updating packages...")

# Remove only existing packages.
# Users and reservations are NOT affected.
cur.execute("DELETE FROM packages")

# Reset package ID numbering
cur.execute(
    "DELETE FROM sqlite_sequence WHERE name='packages'"
)

# Create the new 600 packages
seed_packages(cur)

con.commit()

count = cur.execute(
    "SELECT COUNT(*) FROM packages"
).fetchone()[0]

print(f"Packages created: {count}")

con.close()

print("Done!")