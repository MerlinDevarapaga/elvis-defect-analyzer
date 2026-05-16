"""Temporary script to search for speed errata related tickets."""
import os
from dotenv import load_dotenv
import mysql.connector

for p in ['.env', '.github/skills/elvis-defect-analyzer/.env']:
    if os.path.exists(p):
        load_dotenv(p)
        break

conn = mysql.connector.connect(
    host=os.getenv('ELVIS_DB_HOST'),
    user=os.getenv('ELVIS_DB_USER'),
    password=os.getenv('ELVIS_DB_PASSWORD'),
    database=os.getenv('ELVIS_DB_NAME'),
    port=int(os.getenv('ELVIS_DB_PORT', 3306)),
)
cursor = conn.cursor(dictionary=True)

PROJECT = 'MSIL_DA2.8'

# Search 1: "speed" AND "errata" in Title
print(f"=== Search: 'speed' + 'errata' in Title ({PROJECT}) ===")
cursor.execute(f"SELECT TicketID, Title, TicketStepID, PriorityID, FGroup, Component, EnterDateTime FROM tbl_ElvisSR WHERE ProjectID = %s AND Title LIKE %s AND Title LIKE %s ORDER BY EnterDateTime DESC LIMIT 20", (PROJECT, '%speed%', '%errata%'))
rows = cursor.fetchall()
print(f"Found {len(rows)}\n")
for r in rows:
    print(f"  {r['TicketID']}  |  {str(r['Title'] or '')[:140]}")
    print(f"         Step={r['TicketStepID']}  Pri={r['PriorityID']}  FGroup={r['FGroup']}  Comp={r['Component']}  Date={r['EnterDateTime']}\n")

# Search 2: "speed errata" as phrase
print(f"\n=== Search: 'speed errata' phrase in Title ({PROJECT}) ===")
cursor.execute(f"SELECT TicketID, Title, TicketStepID, PriorityID, FGroup, EnterDateTime FROM tbl_ElvisSR WHERE ProjectID = %s AND Title LIKE %s ORDER BY EnterDateTime DESC LIMIT 20", (PROJECT, '%speed errata%'))
rows2 = cursor.fetchall()
print(f"Found {len(rows2)}\n")
for r in rows2:
    print(f"  {r['TicketID']}  |  {str(r['Title'] or '')[:140]}  ({r['EnterDateTime']})")

# Search 3: just "errata" in Title
print(f"\n=== Search: 'errata' in Title ({PROJECT}) ===")
cursor.execute(f"SELECT TicketID, Title, TicketStepID, PriorityID, FGroup, EnterDateTime FROM tbl_ElvisSR WHERE ProjectID = %s AND Title LIKE %s ORDER BY EnterDateTime DESC LIMIT 20", (PROJECT, '%errata%'))
rows3 = cursor.fetchall()
print(f"Found {len(rows3)}\n")
for r in rows3:
    print(f"  {r['TicketID']}  |  {str(r['Title'] or '')[:140]}  ({r['EnterDateTime']})")

# Search 4: "speed" in Title  
print(f"\n=== Search: 'speed' in Title ({PROJECT}) ===")
cursor.execute(f"SELECT TicketID, Title, TicketStepID, PriorityID, FGroup, EnterDateTime FROM tbl_ElvisSR WHERE ProjectID = %s AND Title LIKE %s ORDER BY EnterDateTime DESC LIMIT 20", (PROJECT, '%speed%'))
rows4 = cursor.fetchall()
print(f"Found {len(rows4)}\n")
for r in rows4:
    print(f"  {r['TicketID']}  |  {str(r['Title'] or '')[:140]}  ({r['EnterDateTime']})")

cursor.close()
conn.close()
