"""
Elvis Defect Analyzer - Fetches defect details from Elvis Report DB.

Usage:
    python fetch_defect.py <ticket_id>

Example:
    python fetch_defect.py 3702652

Data source: db_output.tbl_ElvisSR on elvisreport.harman.com
"""
import os
import sys
import json
from dotenv import load_dotenv
import mysql.connector

# Load .env from workspace root (two levels up from scripts/)
_script_dir = os.path.dirname(os.path.abspath(__file__))
_env_candidates = [
    os.path.join(_script_dir, ".env"),
    os.path.join(_script_dir, "..", ".env"),
    os.path.join(_script_dir, "..", "..", "..", "..", ".env"),  # .github/skills/elvis-defect-analyzer/scripts -> root
]
for _env in _env_candidates:
    if os.path.exists(_env):
        load_dotenv(_env)
        break

# ---------------------------------------------------------------------------
# Column definitions grouped by category.
# These are the columns the SReport user has SELECT access to on tbl_ElvisSR.
# ---------------------------------------------------------------------------

COLUMN_GROUPS = {
    "Identity & Tracking": [
        "TicketID",
        "ProjectID",
        "ReferenceNumber",
        "IntRefNo",
        "ExtReferenceType",
        "IntReferenceType",
        "Alias",
    ],
    "Status & Workflow": [
        "StateID",
        "TicketStepID",
        "Owner",
        "Rejected",
        "RejectReason",
        "IsDeleted",
    ],
    "Description": [
        "Title",
        "ProblemDescription",
    ],
    "Classification & Priority": [
        "ProblemType",
        "PriorityID",
        "IntPriority",
        "Category",
        "StabilityCategory",
        "Occurance",
        "RPNSeverity",
        "RPNOccurrence",
        "RPNDetection",
        "RPNTotal",
        "Milestone",
        "TestEnvironment",
        "TestStage",
    ],
    "System & Component": [
        "System",
        "Sys_SWRev",
        "Sys_HWRev",
        "Sys_MERev",
        "FGroup",
        "FG_SWRev",
        "FG_HWRev",
        "FG_MERev",
        "Component",
        "Comp_SWRev",
        "Comp_HWRev",
        "Comp_MERev",
        "SubComponent",
        "SubComp_SWRev",
        "SubComp_HWRev",
        "SubComp_MERev",
        "Product",
        "SubProject",
        "CustomerDomain",
        "SolutionDomain",
    ],
    "Detection & Responsible": [
        "DetectedBy",
        "DetectedAt",
        "ResponsibleUGrp",
        "ProcessingUGrp",
        "IntegrationUGrp",
        "VerificationUGrp",
        "ConclusionUGrp",
        "ClosedByUGrp",
    ],
    "Root Cause & Resolution": [
        "CauseID",
        "BugTaxonomy",
        "Cause",
        "Measures",
        "Avoidance",
        "DesignReview",
        "Cluster",
    ],
    "Reproduction": [
        "ReproResult",
        "ReproNote",
        "ReproFlag",
    ],
    "Processing & Analysis": [
        "RespNote",
        "Result",
        "Reason",
        "InternalStatement",
        "OfficialStatement",
    ],
    "Version Tracking": [
        "PlannedFixedVersion",
        "PlannedFixedDate",
        "FixedInVersion",
        "ProceedVersion",
        "IntegrateVersion",
        "TestedVersion",
    ],
    "Key Dates": [
        "EnterDateTime",
        "LastChangeDateTime",
        "LastActualisation",
        "FirstRespDateTime",
        "FirstProcDateTime",
        "FirstIntegrDateTime",
        "FirstVeriDateTime",
        "FirstConclDateTime",
        "FirstCloseDateTime",
        "FirstReopenDateTime",
        "LastCloseDateTime",
    ],
}

# Flatten for the SQL query
ALL_COLUMNS = []
for cols in COLUMN_GROUPS.values():
    ALL_COLUMNS.extend(cols)
# Deduplicate while preserving order
ALL_COLUMNS = list(dict.fromkeys(ALL_COLUMNS))

EMPTY_VALUES = {"", "0", "0000-00-00", "0000-00-00 00:00:00", "N", "NONE", "none", "None"}


def get_connection():
    return mysql.connector.connect(
        host=os.getenv("ELVIS_DB_HOST"),
        user=os.getenv("ELVIS_DB_USER"),
        password=os.getenv("ELVIS_DB_PASSWORD"),
        database=os.getenv("ELVIS_DB_NAME"),
        port=int(os.getenv("ELVIS_DB_PORT", 3306)),
    )


def fetch_defect(ticket_id):
    """Fetch defect from tbl_ElvisSR by TicketID."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cols_sql = ", ".join(f"`{c}`" for c in ALL_COLUMNS)
    cursor.execute(
        f"SELECT {cols_sql} FROM tbl_ElvisSR WHERE TicketID = %s",
        (str(ticket_id),),
    )
    row = cursor.fetchone()

    cursor.close()
    conn.close()
    return row


def _is_populated(value):
    """Return True if the value is non-empty/non-default."""
    if value is None:
        return False
    return str(value).strip() not in EMPTY_VALUES


def format_defect_summary(defect, ticket_id):
    """Format defect data into a grouped, readable summary."""
    if not defect:
        return f"No defect found with TicketID {ticket_id} in tbl_ElvisSR."

    lines = [f"# Elvis Defect Report — Ticket {ticket_id}", ""]

    for group_name, columns in COLUMN_GROUPS.items():
        populated = [(c, defect[c]) for c in columns if c in defect and _is_populated(defect[c])]
        if not populated:
            continue
        lines.append(f"## {group_name}")
        for col, val in populated:
            val_str = str(val).strip()
            # For long text fields, keep first 500 chars in summary
            if len(val_str) > 500:
                val_str = val_str[:500] + " [...]"
            lines.append(f"- **{col}**: {val_str}")
        lines.append("")

    return "\n".join(lines)


def main():
    if len(sys.argv) < 2:
        print("Usage: python fetch_defect.py <ticket_id>")
        print("Example: python fetch_defect.py 3702652")
        sys.exit(1)

    ticket_id = sys.argv[1]
    print(f"Fetching defect {ticket_id} from Elvis Report DB (tbl_ElvisSR)...\n")

    try:
        defect = fetch_defect(ticket_id)
    except mysql.connector.Error as e:
        print(f"Database error: {e}")
        sys.exit(1)

    summary = format_defect_summary(defect, ticket_id)
    print(summary)

    if defect:
        # Save raw JSON
        json_path = os.path.join(_script_dir, "..", f"defect_{ticket_id}.json")
        serializable = {}
        for k, v in defect.items():
            try:
                json.dumps(v)
                serializable[k] = v
            except (TypeError, ValueError):
                serializable[k] = str(v)
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(serializable, f, indent=2, ensure_ascii=False)
        print(f"Raw JSON saved to: {os.path.abspath(json_path)}")


if __name__ == "__main__":
    main()
