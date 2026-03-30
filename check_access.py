"""Check DB access permissions and available objects."""
import os
from dotenv import load_dotenv
import mysql.connector

load_dotenv()

conn = mysql.connector.connect(
    host=os.getenv("ELVIS_DB_HOST"),
    user=os.getenv("ELVIS_DB_USER"),
    password=os.getenv("ELVIS_DB_PASSWORD"),
    database=os.getenv("ELVIS_DB_NAME"),
    port=int(os.getenv("ELVIS_DB_PORT", 3306)),
)
cursor = conn.cursor()

# Check grants
print("=== GRANTS ===")
try:
    cursor.execute("SHOW GRANTS FOR CURRENT_USER()")
    for row in cursor.fetchall():
        print(row[0])
except Exception as e:
    print(f"Error: {e}")

# Check all databases accessible
print("\n=== DATABASES ===")
try:
    cursor.execute("SHOW DATABASES")
    for row in cursor.fetchall():
        print(f"  {row[0]}")
except Exception as e:
    print(f"Error: {e}")

# Check views in db_output
print("\n=== VIEWS in db_output ===")
try:
    cursor.execute("SELECT TABLE_NAME, TABLE_TYPE FROM information_schema.TABLES WHERE TABLE_SCHEMA = 'db_output'")
    for row in cursor.fetchall():
        print(f"  {row[0]:50s} {row[1]}")
except Exception as e:
    print(f"Error: {e}")

# Try other databases
print("\n=== Trying other databases ===")
try:
    cursor.execute("SHOW DATABASES")
    dbs = [row[0] for row in cursor.fetchall()]
    for db in dbs:
        if db in ('information_schema', 'performance_schema', 'mysql', 'sys'):
            continue
        try:
            cursor.execute(f"SHOW TABLES FROM `{db}`")
            tables = cursor.fetchall()
            if tables:
                print(f"\n  Database: {db} ({len(tables)} tables)")
                for t in tables[:10]:
                    print(f"    - {t[0]}")
                if len(tables) > 10:
                    print(f"    ... and {len(tables)-10} more")
        except Exception as e2:
            print(f"  {db}: {e2}")
except Exception as e:
    print(f"Error: {e}")

cursor.close()
conn.close()
