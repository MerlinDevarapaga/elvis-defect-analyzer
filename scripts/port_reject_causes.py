`"""
Port 'Updated Reject Cause' and 'Updated Notes' from the per-FG sheets
in MSIL_DA2.8_Rejectedtickets_causes.xlsx into columns G & H of Reject tickets.csv.
"""
import pandas as pd
import sys, io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

CAUSES_XLSX = r"C:\Users\mdevarapaga\Downloads\MSIL_DA2.8_Rejectedtickets_causes.xlsx"
TARGET_CSV = r"C:\Users\mdevarapaga\Downloads\Reject tickets.csv"
OUTPUT_CSV = r"C:\Users\mdevarapaga\Downloads\Reject_tickets_updated.csv"

# Each FG sheet has slightly different column names/positions.
# Map: sheet_name -> (ticket_id_col, updated_cause_col, updated_notes_col, header_row)
SHEET_CONFIG = {
    "Projection-Imported": {
        "header_row": 3,
        "tid_col": "Ticket_ID",
        "cause_col": "Updated reject cause",
        "notes_col": "Updated notes",
    },
    "Systems Infra- Done": {
        "header_row": 3,
        "tid_col": "Ticket ID",
        "cause_col": "Updated reject cause",
        "notes_col": "Updated Notes",
    },
    "Wi-fi-Done": {
        "header_row": 3,
        "tid_col": "Ticket ID",
        "cause_col": None,  # No updated cause column
        "notes_col": "Updated rejection notes",
    },
    "Camera": {
        "header_row": 3,
        "tid_col": "Ticket ID",
        "cause_col": "Updates cause",
        "notes_col": "Updated notes",
    },
    "HMI": {
        "header_row": 3,
        "tid_col": "Ticket ID",
        # HMI has columns: Ticket ID, Title, Note, Reject cause, (blank), (blank)
        # Col E and F have data in some rows but headers are blank
        # Row 5 has: 3710586 ... '' "Rejection reason should be 'Tolerated'"
        "cause_col": None,
        "notes_col": 5,  # column index since header is blank
    },
    "IOC": {
        "header_row": 3,
        "tid_col": "Ticket ID",
        "cause_col": "Updated cause",
        "notes_col": "Updated notes",
    },
    "Bluetooth": {
        "header_row": 3,
        "tid_col": "Ticket ID",
        "cause_col": "Updated reject cause",
        "notes_col": "Updated notes",
    },
    "VR": {
        "header_row": 4,
        "tid_col": "Ticket ID",
        "cause_col": "Updated reject cause",
        "notes_col": "Updated notes",
    },
    "Systems_Core": {
        "header_row": 3,
        "tid_col": "Ticket ID",
        "cause_col": "Updated reject cause",
        "notes_col": "Updated notes",
    },
    "Security": {
        "header_row": 3,
        "tid_col": "Ticket_ID",
        "cause_col": "Updated reject cause",
        "notes_col": "Updated notes",
    },
    "Media": {
        "header_row": 3,
        "tid_col": "Ticket ID",
        "cause_col": "Updated reject cause",
        "notes_col": "Updated notes",
    },
    "Audio": {
        "header_row": 3,
        "tid_col": "Ticket ID",
        "cause_col": "Updated reject cause",
        "notes_col": "Updated notes",
    },
    "External Suppliers": {
        "header_row": 1,
        "tid_col": "Ticket ID",
        "cause_col": "Reject Cause",  # This is actually the updated one
        "notes_col": "Updated notes",
    },
    "Tuner": {
        "header_row": 3,
        "tid_col": "Ticket ID",
        "cause_col": None,
        "notes_col": None,
    },
}


def safe_str(val):
    if pd.isna(val):
        return None
    s = str(val).strip()
    if s in ("", "nan", "None", "_", "-"):
        return None
    return s


def extract_updates_from_sheet(xlsx_path, sheet_name, config):
    """Extract ticket_id -> (updated_cause, updated_notes) from a sheet."""
    updates = {}

    try:
        df = pd.read_excel(xlsx_path, sheet_name=sheet_name, header=config["header_row"])
    except Exception as e:
        print(f"  Warning: Could not read sheet '{sheet_name}': {e}")
        return updates

    # Find ticket ID column
    tid_col = config["tid_col"]
    if tid_col not in df.columns:
        # Try fuzzy match
        for c in df.columns:
            if "ticket" in str(c).lower() and "id" in str(c).lower():
                tid_col = c
                break
        else:
            print(f"  Warning: No ticket ID column found in '{sheet_name}'. Cols: {list(df.columns)}")
            return updates

    # Find cause column
    cause_col = config.get("cause_col")
    if cause_col and cause_col not in df.columns:
        # Try fuzzy match
        for c in df.columns:
            if "updated" in str(c).lower() and "cause" in str(c).lower():
                cause_col = c
                break
        else:
            cause_col = None

    # Find notes column
    notes_col = config.get("notes_col")
    if isinstance(notes_col, int):
        # Use column index
        if notes_col < len(df.columns):
            notes_col = df.columns[notes_col]
        else:
            notes_col = None
    elif notes_col and notes_col not in df.columns:
        for c in df.columns:
            if "updated" in str(c).lower() and "note" in str(c).lower():
                notes_col = c
                break
        else:
            notes_col = None

    for _, row in df.iterrows():
        tid = row.get(tid_col)
        if pd.isna(tid):
            continue
        try:
            tid = int(float(tid))
        except (ValueError, TypeError):
            continue

        updated_cause = safe_str(row.get(cause_col)) if cause_col else None
        updated_notes = safe_str(row.get(notes_col)) if notes_col else None

        if updated_cause or updated_notes:
            updates[tid] = (updated_cause, updated_notes)

    return updates


def main():
    print("Reading source Excel sheets...")
    all_updates = {}
    for sheet_name, config in SHEET_CONFIG.items():
        updates = extract_updates_from_sheet(CAUSES_XLSX, sheet_name, config)
        print(f"  {sheet_name}: {len(updates)} tickets with updates")
        # Merge — later sheets don't overwrite earlier ones
        for tid, (cause, notes) in updates.items():
            if tid not in all_updates:
                all_updates[tid] = [None, None]
            if cause:
                all_updates[tid][0] = cause
            if notes:
                all_updates[tid][1] = notes

    print(f"\nTotal unique tickets with updates: {len(all_updates)}")
    cause_count = sum(1 for v in all_updates.values() if v[0])
    notes_count = sum(1 for v in all_updates.values() if v[1])
    print(f"  With updated cause: {cause_count}")
    print(f"  With updated notes: {notes_count}")

    # Read target CSV
    print(f"\nReading target CSV: {TARGET_CSV}")
    df = pd.read_csv(TARGET_CSV, encoding='utf-8', on_bad_lines='skip')
    print(f"  Rows: {len(df)}")

    # Apply updates
    matched = 0
    for idx, row in df.iterrows():
        tid = row['Ticket ID']
        if tid in all_updates:
            cause, notes = all_updates[tid]
            if cause:
                df.at[idx, 'Updated Reject Cause'] = cause
            if notes:
                df.at[idx, 'Updated New Note'] = notes
            matched += 1

    print(f"\nMatched and updated: {matched} tickets")
    filled_g = df['Updated Reject Cause'].notna().sum()
    filled_h = df['Updated New Note'].notna().sum()
    print(f"  Col G (Updated Reject Cause) filled: {filled_g}")
    print(f"  Col H (Updated New Note) filled: {filled_h}")

    # Save
    df.to_csv(OUTPUT_CSV, index=False, encoding='utf-8-sig')
    print(f"\nSaved to: {OUTPUT_CSV}")

    # Show some samples
    updated_rows = df[df['Updated Reject Cause'].notna() | df['Updated New Note'].notna()]
    if len(updated_rows) > 0:
        print(f"\nSample updated rows:")
        for _, r in updated_rows.head(10).iterrows():
            print(f"  {r['Ticket ID']} | FG: {r['Functional group']}")
            print(f"    Old Cause: {r['Reject cause']}")
            if pd.notna(r['Updated Reject Cause']):
                print(f"    New Cause: {r['Updated Reject Cause']}")
            if pd.notna(r['Updated New Note']):
                note_preview = str(r['Updated New Note'])[:100]
                print(f"    New Note: {note_preview}")
            print()


if __name__ == "__main__":
    main()
