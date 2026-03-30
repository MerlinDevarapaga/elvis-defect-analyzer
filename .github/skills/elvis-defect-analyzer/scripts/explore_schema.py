"""Explore the Elvis Report DB schema to understand available tables and columns."""
import os
import sys
from dotenv import load_dotenv
import mysql.connector

load_dotenv()

def get_connection():
    return mysql.connector.connect(
        host=os.getenv("ELVIS_DB_HOST"),
        user=os.getenv("ELVIS_DB_USER"),
        password=os.getenv("ELVIS_DB_PASSWORD"),
        database=os.getenv("ELVIS_DB_NAME"),
        port=int(os.getenv("ELVIS_DB_PORT", 3306)),
    )

def explore_schema():
    conn = get_connection()
    cursor = conn.cursor()

    # List all tables
    cursor.execute("SHOW TABLES")
    tables = [row[0] for row in cursor.fetchall()]
    print(f"=== Tables in db_output ({len(tables)}) ===")
    for t in tables:
        print(f"  - {t}")

    # For each table, show columns
    for t in tables:
        cursor.execute(f"DESCRIBE `{t}`")
        cols = cursor.fetchall()
        print(f"\n=== Table: {t} ({len(cols)} columns) ===")
        for col in cols:
            print(f"  {col[0]:40s} {col[1]:30s} {col[2]:5s} {col[3]:5s}")

    cursor.close()
    conn.close()

if __name__ == "__main__":
    explore_schema()
