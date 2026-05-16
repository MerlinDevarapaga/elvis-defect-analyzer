"""
Cutoff Status Report — Shows ticket distribution split by a cutoff date.

For each period (before cutoff, after cutoff till today):
  - Total tickets
  - Concluded and Closed
  - Integrating and Verification
  - Open (Categorizing, Processing, Reproduction)

Filter: ProjectID = MSIL_DA2.8, ExtRef (ReferenceNumber) = empty/0/1/2 only.

Usage:
    python scripts/cutoff_status_report.py
"""
import os
import sys
import io
from datetime import datetime, date, timedelta

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from dotenv import load_dotenv
import mysql.connector

# Load .env
_script_dir = os.path.dirname(os.path.abspath(__file__))
for _env in [os.path.join(_script_dir, "..", ".env"), os.path.join(_script_dir, ".env")]:
    if os.path.exists(_env):
        load_dotenv(_env)
        break

PROJECT_ID = "MSIL_DA2.8"
CUTOFF_DATE = date(2026, 3, 17)  # March 17, 2026

P8_PATTERNS = ("p8", "p8_ytb_na", "p8_ytb")

def is_p8(fg_swrev):
    if not fg_swrev:
        return False
    return fg_swrev.strip().lower().startswith("p8") or fg_swrev.strip().lower() in P8_PATTERNS

# Step categories
CONCLUDED_CLOSED = ("Concluding", "Closed")
INTEGRATING_VERIFICATION = ("Integrating", "Verification")
OPEN_STEPS = ("Categorizing", "Processing", "Reproduction")


def get_connection():
    return mysql.connector.connect(
        host=os.getenv("ELVIS_DB_HOST"),
        user=os.getenv("ELVIS_DB_USER"),
        password=os.getenv("ELVIS_DB_PASSWORD"),
        database=os.getenv("ELVIS_DB_NAME"),
        port=int(os.getenv("ELVIS_DB_PORT", 3306)),
    )


def fetch_all_tickets():
    """Fetch all MSIL_DA2.8 tickets with ExtRef = empty/0/1/2."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    query = (
        "SELECT TicketID, TicketStepID, EnterDateTime, FGroup, FG_SWRev "
        "FROM tbl_ElvisSR "
        "WHERE ProjectID = %s "
        "  AND (ReferenceNumber IS NULL OR ReferenceNumber IN (0, 1, 2)) "
        "  AND IsDeleted = 'N' "
        "ORDER BY EnterDateTime"
    )
    cursor.execute(query, [PROJECT_ID])
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return rows


def classify_step(step_id):
    """Classify a TicketStepID into a category."""
    if not step_id:
        return "Open"
    s = step_id.strip()
    if s in CONCLUDED_CLOSED:
        return "Concluded and Closed"
    elif s in INTEGRATING_VERIFICATION:
        return "Integrating and Verification"
    elif s in OPEN_STEPS:
        return "Open"
    else:
        return "Other (" + s + ")"


def to_date(dt):
    if isinstance(dt, datetime):
        return dt.date()
    if isinstance(dt, date):
        return dt
    return None


def main():
    rows = fetch_all_tickets()

    # Split by cutoff date
    before_cutoff = []
    after_cutoff = []

    for row in rows:
        enter_dt = to_date(row.get("EnterDateTime"))
        if enter_dt and enter_dt <= CUTOFF_DATE:
            before_cutoff.append(row)
        else:
            after_cutoff.append(row)

    # Count by category + P8 for all categories
    def count_categories(ticket_list):
        counts = {
            "Total": 0, "Total_P8": 0,
            "Concluded and Closed": 0, "CC_P8": 0,
            "Integrating and Verification": 0, "IV_P8": 0,
            "Open": 0, "Open_P8": 0,
            "Other": 0, "Other_P8": 0,
        }
        for t in ticket_list:
            cat = classify_step(t.get("TicketStepID"))
            p8 = is_p8(t.get("FG_SWRev", ""))
            counts["Total"] += 1
            if p8:
                counts["Total_P8"] += 1
            if cat == "Concluded and Closed":
                counts["Concluded and Closed"] += 1
                if p8: counts["CC_P8"] += 1
            elif cat == "Integrating and Verification":
                counts["Integrating and Verification"] += 1
                if p8: counts["IV_P8"] += 1
            elif cat == "Open":
                counts["Open"] += 1
                if p8: counts["Open_P8"] += 1
            else:
                counts["Other"] += 1
                if p8: counts["Other_P8"] += 1
        return counts

    before_counts = count_categories(before_cutoff)
    after_counts = count_categories(after_cutoff)

    # Overall
    all_counts = {k: before_counts[k] + after_counts[k] for k in before_counts}

    def p8_str(count, p8):
        return f"{count:>8}  (P8: {p8})" if p8 else f"{count:>8}"

    # Print
    col_w = 35
    num_w = 8

    print()
    print(f"MSIL DA2.8 — Cutoff Status Report")
    print(f"Filter: ExtRef (ReferenceNumber) = empty/0, 1, 2 only")
    print(f"Cutoff Date: {CUTOFF_DATE.strftime('%B %d, %Y')}")
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    # ---- OVERALL SUMMARY ----
    print()
    sep2 = "=" * 65
    print(sep2)
    print(f"  OVERALL SUMMARY (All tickets)")
    print(sep2)
    print(f"  {'Total Defects':<{col_w}} {all_counts['Total']:>{num_w}}   (P8: {all_counts['Total_P8']})")
    print(f"  {'Concluded and Closed':<{col_w}} {all_counts['Concluded and Closed']:>{num_w}}   (P8: {all_counts['CC_P8']})")
    print(f"  {'Integrating and Verification':<{col_w}} {all_counts['Integrating and Verification']:>{num_w}}   (P8: {all_counts['IV_P8']})")
    print(f"  {'Open':<{col_w}} {all_counts['Open']:>{num_w}}   (P8: {all_counts['Open_P8']})")
    print(f"  {'  -> non-P8 Open':<{col_w}} {all_counts['Open'] - all_counts['Open_P8']:>{num_w}}")
    if all_counts["Other"]:
        print(f"  {'Other':<{col_w}} {all_counts['Other']:>{num_w}}   (P8: {all_counts['Other_P8']})")
    print(sep2)

    # ---- BEFORE / AFTER SPLIT ----
    print()
    sep = "=" * 115
    print(sep)
    lw = 48  # left column width
    print(f"{'Till Mar 17 cutoff':<{lw}}    {'After Mar 17 till today'}")
    print(f"{'-'*lw}    {'-'*lw}")
    print(f"{'Total':<30} {before_counts['Total']:>6}  (P8: {before_counts['Total_P8']:>4})    "
          f"{'Total':<30} {after_counts['Total']:>6}  (P8: {after_counts['Total_P8']:>4})")
    print(f"{'Concluded and Closed':<30} {before_counts['Concluded and Closed']:>6}  (P8: {before_counts['CC_P8']:>4})    "
          f"{'Concluded and Closed':<30} {after_counts['Concluded and Closed']:>6}  (P8: {after_counts['CC_P8']:>4})")
    print(f"{'Integrating and Verification':<30} {before_counts['Integrating and Verification']:>6}  (P8: {before_counts['IV_P8']:>4})    "
          f"{'Integrating and Verification':<30} {after_counts['Integrating and Verification']:>6}  (P8: {after_counts['IV_P8']:>4})")
    print(f"{'Open':<30} {before_counts['Open']:>6}  (P8: {before_counts['Open_P8']:>4})    "
          f"{'Open':<30} {after_counts['Open']:>6}  (P8: {after_counts['Open_P8']:>4})")
    print(f"{'  -> non-P8':<30} {before_counts['Open'] - before_counts['Open_P8']:>6}{'':>14}    "
          f"{'  -> non-P8':<30} {after_counts['Open'] - after_counts['Open_P8']:>6}")
    if before_counts["Other"] or after_counts["Other"]:
        print(f"{'Other':<30} {before_counts['Other']:>6}  (P8: {before_counts['Other_P8']:>4})    "
              f"{'Other':<30} {after_counts['Other']:>6}  (P8: {after_counts['Other_P8']:>4})")
    print(sep)

    # FGroup-wise for Open tickets with P8 split
    print(f"\n{'='*90}")
    print(f"OPEN TICKETS BREAKDOWN BY FGROUP (current step < Integrating)")
    print(f"P8 = tickets with FG_SWRev starting with P8/P8_YTB_NA")
    print(f"{'='*90}")

    # Structure: fg -> {before: count, before_p8: count, after: count, after_p8: count}
    from collections import defaultdict
    open_data = defaultdict(lambda: {"before": 0, "before_p8": 0, "after": 0, "after_p8": 0})

    for t in before_cutoff:
        cat = classify_step(t.get("TicketStepID"))
        if cat == "Open":
            fg = (t.get("FGroup") or "Unknown").strip()
            open_data[fg]["before"] += 1
            if is_p8(t.get("FG_SWRev", "")):
                open_data[fg]["before_p8"] += 1

    for t in after_cutoff:
        cat = classify_step(t.get("TicketStepID"))
        if cat == "Open":
            fg = (t.get("FGroup") or "Unknown").strip()
            open_data[fg]["after"] += 1
            if is_p8(t.get("FG_SWRev", "")):
                open_data[fg]["after_p8"] += 1

    all_fgs = sorted(open_data.keys(),
                     key=lambda fg: open_data[fg]["before"] + open_data[fg]["after"],
                     reverse=True)

    fg_w = max(len("Functional Group"), max((len(fg) for fg in all_fgs), default=15))
    print(f"\n{'Functional Group':<{fg_w}}  {'Before':>7} {'(P8)':>5}  {'After':>7} {'(P8)':>5}  {'Total':>6} {'(P8)':>5}")
    print("-" * (fg_w + 47))

    gt_before = gt_after = gt_bp8 = gt_ap8 = 0
    for fg in all_fgs:
        d = open_data[fg]
        b, bp8 = d["before"], d["before_p8"]
        a, ap8 = d["after"], d["after_p8"]
        tot = b + a
        tp8 = bp8 + ap8
        bp8_s = f"({bp8})" if bp8 else ""
        ap8_s = f"({ap8})" if ap8 else ""
        tp8_s = f"({tp8})" if tp8 else ""
        print(f"{fg:<{fg_w}}  {b:>7} {bp8_s:>5}  {a:>7} {ap8_s:>5}  {tot:>6} {tp8_s:>5}")
        gt_before += b; gt_after += a; gt_bp8 += bp8; gt_ap8 += ap8

    print("-" * (fg_w + 47))
    gt_tot = gt_before + gt_after
    gt_tp8 = gt_bp8 + gt_ap8
    print(f"{'Grand Total':<{fg_w}}  {gt_before:>7} ({gt_bp8:>2})  {gt_after:>7} ({gt_ap8:>2})  {gt_tot:>6} ({gt_tp8:>2})")
    print()
    print(f"P8/P8_YTB_NA in Open: {gt_tp8} out of {gt_tot} ({gt_tp8/gt_tot*100:.1f}%)" if gt_tot > 0 else "")


if __name__ == "__main__":
    main()
