import mysql.connector, os
from dotenv import load_dotenv
load_dotenv()

conn = mysql.connector.connect(
    host=os.getenv('ELVIS_DB_HOST'), user=os.getenv('ELVIS_DB_USER'),
    password=os.getenv('ELVIS_DB_PASSWORD'), database=os.getenv('ELVIS_DB_NAME'),
    port=int(os.getenv('ELVIS_DB_PORT', 3306))
)
cur = conn.cursor(dictionary=True)
ids = [3726579,3724991,3710131,3703960,3727643,3714420,3726402,3725645,3723553,3719292,3719329,3727322]
placeholders = ','.join(['%s'] * len(ids))
cur.execute(
    f"SELECT TicketID, Title, TicketStepID, StateID, PriorityID, FGroup, "
    f"SequenceOfActivity, PlannedFixedDate "
    f"FROM tbl_ElvisSR WHERE TicketID IN ({placeholders})", ids
)
rows = cur.fetchall()
conn.close()

header = f"{'Ticket':<10} {'Step':<15} {'State':<12} {'Priority':<15} {'SOA':<22} {'FPD':<14} {'FGroup':<22} Title"
print(header)
print("-" * len(header) + "-" * 30)
for r in sorted(rows, key=lambda x: x['TicketID']):
    fpd = str(r['PlannedFixedDate'] or 'N/A')[:10]
    title = str(r['Title'] or '')[:55]
    print(f"{r['TicketID']:<10} {str(r['TicketStepID']):<15} {str(r['StateID']):<12} {str(r['PriorityID']):<15} {str(r['SequenceOfActivity']):<22} {fpd:<14} {str(r['FGroup']):<22} {title}")
