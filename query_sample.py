"""Query defect 3702652 with only permitted columns to see actual data."""
import os
from dotenv import load_dotenv
import mysql.connector

load_dotenv()

# All columns the SReport user has SELECT permission on (key subset)
PERMITTED_COLUMNS = [
    "TicketID", "ProjectID", "LastActualisation", "EnterDateTime", "LastChangeDateTime",
    "Title", "ProblemDescription", "DetectedBy", "DetectedAt", "ProblemType", "PriorityID",
    "Owner", "StateID", "TicketStepID", "Rejected", "IsDeleted",
    "System", "Sys_SWRev", "Sys_HWRev", "Sys_MERev",
    "FGroup", "FG_SWRev", "FG_HWRev", "FG_MERev",
    "Component", "Comp_SWRev", "Comp_HWRev", "Comp_MERev",
    "SubComponent", "SubComp_SWRev", "SubComp_HWRev", "SubComp_MERev",
    "Category", "StabilityCategory", "IntPriority", "Alias",
    "CauseID", "BugTaxonomy", "Cause", "Measures", "Avoidance",
    "Product", "SubProject", "CustomerDomain", "SolutionDomain",
    "PlannedFixedDate", "PlannedFixedVersion", "FixedInVersion",
    "ProceedVersion", "IntegrateVersion", "TestedVersion",
    "RespNote", "ReproResult", "ReproNote", "ReproFlag",
    "Result", "Reason", "InternalStatement", "OfficialStatement",
    "RPNSeverity", "RPNOccurrence", "RPNDetection", "RPNTotal",
    "Occurance", "ReferenceNumber", "IntRefNo", "ExtReferenceType", "IntReferenceType",
    "SerialNumber", "Milestone", "TestEnvironment", "TestStage",
    "RejectReason", "Cluster", "DesignReview",
    "FirstRespDateTime", "FirstProcDateTime", "FirstIntegrDateTime",
    "FirstVeriDateTime", "FirstConclDateTime", "FirstCloseDateTime",
    "FirstReopenDateTime", "LastCloseDateTime",
    "ResponsibleUGrp", "ProcessingUGrp", "IntegrationUGrp",
    "VerificationUGrp", "ConclusionUGrp", "ClosedByUGrp",
    "FreeField_01", "FreeField_02", "FreeField_03", "FreeField_04", "FreeField_05",
    "FreeField_06", "FreeField_07", "FreeField_08", "FreeField_09", "FreeField_10",
    "FreeField_11", "FreeField_12", "FreeField_13", "FreeField_14",
]

conn = mysql.connector.connect(
    host=os.getenv("ELVIS_DB_HOST"),
    user=os.getenv("ELVIS_DB_USER"),
    password=os.getenv("ELVIS_DB_PASSWORD"),
    database=os.getenv("ELVIS_DB_NAME"),
    port=int(os.getenv("ELVIS_DB_PORT", 3306)),
)
cursor = conn.cursor(dictionary=True)

cols_str = ", ".join(f"`{c}`" for c in PERMITTED_COLUMNS)
cursor.execute(f"SELECT {cols_str} FROM tbl_ElvisSR WHERE TicketID = %s", ("3702652",))
row = cursor.fetchone()
cursor.close()
conn.close()

if row:
    print("=== NON-EMPTY FIELDS ===")
    for k, v in row.items():
        val_str = str(v) if v is not None else ""
        if val_str.strip() and val_str not in ("0", "0000-00-00", "0000-00-00 00:00:00", "N", "NONE", ""):
            print(f"{k:45s} = {val_str[:300]}")
else:
    print("No defect found")
