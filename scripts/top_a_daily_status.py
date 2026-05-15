"""
DA2.8 : Open Bugs : TOP (S) + A : Daily Status Update
Generates a daily status table with Open/Inflow/Outflow split by TOP and A(1) priority.
"""
import os, sys, io
from datetime import datetime, timedelta, date
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from dotenv import load_dotenv
import mysql.connector

_script_dir = os.path.dirname(os.path.abspath(__file__))
for _env in [os.path.join(_script_dir, ".env"), os.path.join(_script_dir, "..", ".env")]:
    if os.path.exists(_env):
        load_dotenv(_env)
        break

BUG_ZERO_WHERE = """
    `ProjectID` = 'MSIL_DA2.8'
    AND `IsDeleted` = 'N'
    AND (`ReferenceNumber` IS NULL OR `ReferenceNumber` <= 2)
    AND (`FG_SWRev` IS NULL OR `FG_SWRev` != 'P8_YTB_NA')
    AND (
        `PriorityID` IN ('A(1)', 'top')
        OR (`PriorityID` = 'B(2)' AND `Occurance` != 'Once')
        OR (`PriorityID` = 'C(3)' AND `Occurance` != 'Once')
    )
"""

OPEN_STEPS = ("Categorizing", "Reproduction", "Processing")
DAYS = 9  # last N days


def main():
    conn = mysql.connector.connect(
        host=os.getenv("ELVIS_DB_HOST"),
        user=os.getenv("ELVIS_DB_USER"),
        password=os.getenv("ELVIS_DB_PASSWORD"),
        database=os.getenv("ELVIS_DB_NAME"),
        port=int(os.getenv("ELVIS_DB_PORT", 3306)),
        connection_timeout=15,
    )
    cursor = conn.cursor(dictionary=True)
    today = date.today()
    dates = [today - timedelta(days=i) for i in range(DAYS)]
    earliest = dates[-1]
    open_steps_sql = "','".join(OPEN_STEPS)

    # --- Current open by priority ---
    cursor.execute(f"""
        SELECT `PriorityID`, COUNT(*) as cnt FROM tbl_ElvisSR
        WHERE {BUG_ZERO_WHERE} AND `TicketStepID` IN ('{open_steps_sql}')
        GROUP BY `PriorityID`
    """)
    current_open = {}
    for r in cursor.fetchall():
        current_open[r["PriorityID"]] = r["cnt"]

    top_open = current_open.get("top", 0)
    a_open = current_open.get("A(1)", 0)

    # --- Daily inflow by priority ---
    cursor.execute(f"""
        SELECT DATE(`EnterDateTime`) as d, `PriorityID`, COUNT(*) as cnt FROM tbl_ElvisSR
        WHERE {BUG_ZERO_WHERE} AND DATE(`EnterDateTime`) >= %s
        GROUP BY DATE(`EnterDateTime`), `PriorityID`
    """, (earliest,))
    daily_inflow = {}  # {date: {priority: count}}
    for r in cursor.fetchall():
        d = r["d"]
        if isinstance(d, datetime): d = d.date()
        daily_inflow.setdefault(d, {})[r["PriorityID"]] = r["cnt"]

    # --- Daily outflow (moved to Integrating/Verification) by priority ---
    cursor.execute(f"""
        SELECT DATE(`FirstIntegrDateTime`) as d, `PriorityID`, COUNT(*) as cnt FROM tbl_ElvisSR
        WHERE {BUG_ZERO_WHERE} AND `Rejected` = 'N'
          AND DATE(`FirstIntegrDateTime`) >= %s
        GROUP BY DATE(`FirstIntegrDateTime`), `PriorityID`
    """, (earliest,))
    daily_outflow = {}
    for r in cursor.fetchall():
        d = r["d"]
        if isinstance(d, datetime): d = d.date()
        daily_outflow.setdefault(d, {})[r["PriorityID"]] = r["cnt"]

    # --- TOP ticket details for remarks (today's open) ---
    cursor.execute(f"""
        SELECT `TicketID`, `Title`, `FGroup` FROM tbl_ElvisSR
        WHERE {BUG_ZERO_WHERE} AND `PriorityID` = 'top'
          AND `TicketStepID` IN ('{open_steps_sql}')
        ORDER BY `TicketID`
    """)
    top_tickets = cursor.fetchall()

    cursor.close()
    conn.close()

    # --- Build remarks for TOP tickets ---
    top_remarks = f"Top - {top_open}"
    if top_tickets:
        details = []
        for t in top_tickets[:3]:  # show up to 3
            title_short = str(t["Title"] or "")[:30]
            details.append(f"{t['TicketID']}({t['FGroup']})")
        top_remarks += ", " + ", ".join(details)

    # --- Reconstruct open counts per day (approximate backward from today) ---
    # We know today's open. For previous days, reconstruct:
    # open[d-1] = open[d] + inflow[d] - outflow[d]  (reverse: open[d-1] = open[d] - inflow[d] + outflow[d])
    # Actually going backward: open_yesterday = open_today + outflow_today - inflow_today
    top_opens = {}
    a_opens = {}
    top_opens[today] = top_open
    a_opens[today] = a_open

    for i in range(1, DAYS):
        d = today - timedelta(days=i-1)
        d_prev = today - timedelta(days=i)
        # open[prev] = open[d] + outflow[d] - inflow[d]
        top_in = daily_inflow.get(d, {}).get("top", 0)
        top_out = daily_outflow.get(d, {}).get("top", 0)
        a_in = daily_inflow.get(d, {}).get("A(1)", 0)
        a_out = daily_outflow.get(d, {}).get("A(1)", 0)
        top_opens[d_prev] = top_opens[d] + top_out - top_in
        a_opens[d_prev] = a_opens[d] + a_out - a_in

    # --- Print table ---
    print()
    print("DA2.8 : Open Bugs : TOP (S) + A : Daily Status Update")
    print("=" * 90)
    print(f"{'Date':<12} {'Open':^11} {'Inflow':^11} {'Outflow':^11} {'Remarks'}")
    print(f"{'':12} {'TOP(S)':>5} {'A(1)':>5} {'TOP(S)':>5} {'A(1)':>5} {'TOP(S)':>5} {'A(1)':>5}")
    print("-" * 90)

    for d in sorted(dates):
        t_open = top_opens.get(d, 0)
        a_op = a_opens.get(d, 0)
        t_in = daily_inflow.get(d, {}).get("top", 0)
        a_in = daily_inflow.get(d, {}).get("A(1)", 0)
        t_out = daily_outflow.get(d, {}).get("top", 0)
        a_out = daily_outflow.get(d, {}).get("A(1)", 0)
        remarks = ""
        if d == today:
            remarks = top_remarks
        print(f"{d.strftime('%d-%m-%Y'):<12} {t_open:>5} {a_op:>5} {t_in:>5} {a_in:>5} {t_out:>5} {a_out:>5}   {remarks}")

    print("-" * 90)
    print(f"\nCurrent Open: TOP = {top_open}, A(1) = {a_open}, Total TOP+A = {top_open + a_open}")
    print(f"(Bug Zero filter applied — excludes Once-B2, Once-C3, P8_YTB_NA, RefNum>2)")


if __name__ == "__main__":
    main()
