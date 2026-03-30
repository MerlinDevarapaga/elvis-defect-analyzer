---
name: elvis-defect-analyzer
description: "Fetch and analyze defects from the Elvis Report DB (MySQL). Use when: analyzing a defect ticket, pulling defect details by ticket ID, summarizing Elvis defect attributes, investigating bug reports from Elvis/Standardreporting. Takes a Ticket ID as input."
argument-hint: "Ticket ID from Elvis (e.g., 3702652)"
---

# Elvis Defect Analyzer

## What It Does
Connects to the Elvis Report DB (MySQL on `elvisreport.harman.com`, database `db_output`) and retrieves all attributes for a given defect ticket ID. Outputs a structured summary of key fields grouped by category.

## When to Use
- You have an Elvis/Standardreporting defect ticket ID and need its details
- You want to analyze a bug report before investigating code
- You need defect context (severity, status, description, assignment, timeline) loaded into the conversation

## Prerequisites
- Python 3 with `mysql-connector-python` and `python-dotenv` installed
- A `.env` file in the workspace root with Elvis DB credentials:
  ```
  ELVIS_DB_HOST=elvisreport.harman.com
  ELVIS_DB_USER=SReport
  ELVIS_DB_PASSWORD=<actual password>
  ELVIS_DB_NAME=db_output
  ELVIS_DB_PORT=3306
  ```
- Request password via: https://jira.harman.com/jira/servicedesk/customer/portal/84

## Procedure

### Step 1: Fetch Defect Data
Run the fetch script with the ticket ID:
```
python .github/skills/elvis-defect-analyzer/scripts/fetch_defect.py <TICKET_ID>
```
This queries `db_output.tbl_ElvisSR` by `TicketID` and prints a structured summary grouped into these categories:

| Group | Key Columns |
|-------|-------------|
| **Identity & Tracking** | TicketID, ProjectID, ReferenceNumber, IntRefNo, Alias |
| **Status & Workflow** | StateID, TicketStepID, Owner, Rejected, RejectReason |
| **Description** | Title, ProblemDescription (includes test setup, preconditions, repro steps, observed/expected) |
| **Classification & Priority** | ProblemType, PriorityID, IntPriority, Category, Occurance, RPNSeverity/Occurrence/Detection/Total, Milestone, TestEnvironment, TestStage |
| **System & Component** | System, FGroup, Component, SubComponent (each with SW/HW/ME revisions), Product, SubProject, CustomerDomain, SolutionDomain |
| **Detection & Responsible** | DetectedBy, DetectedAt, ResponsibleUGrp, ProcessingUGrp, IntegrationUGrp, VerificationUGrp, ConclusionUGrp, ClosedByUGrp |
| **Root Cause & Resolution** | CauseID, BugTaxonomy, Cause, Measures, Avoidance, DesignReview, Cluster |
| **Reproduction** | ReproResult, ReproNote, ReproFlag |
| **Processing & Analysis** | RespNote, Result, Reason, InternalStatement, OfficialStatement |
| **Version Tracking** | PlannedFixedVersion, PlannedFixedDate, FixedInVersion, ProceedVersion, IntegrateVersion, TestedVersion |
| **Key Dates** | EnterDateTime, LastChangeDateTime, FirstRespDateTime, FirstProcDateTime, FirstIntegrDateTime, FirstVeriDateTime, FirstConclDateTime, FirstCloseDateTime, FirstReopenDateTime, LastCloseDateTime |

Only non-empty fields are shown. Raw JSON is also saved to `defect_<TICKET_ID>.json`.

### Step 2: Review the Summary
Key fields to focus on for defect analysis:
- **PriorityID / IntPriority / RPNSeverity** — determines urgency
- **StateID / TicketStepID** — current workflow state
- **Title + ProblemDescription** — what the defect is, repro steps
- **System / FGroup / Component** — where in the codebase to look
- **Cause / BugTaxonomy** — root cause analysis
- **Result** — verification pass/fail history
- **Owner / DetectedBy** — who is responsible

### Step 3: Use the Context
With the defect details loaded, you can now:
- Search the codebase for the affected component/module
- Investigate the root cause based on the description
- Check related defects or regressions (look for Elvis IDs in the Cause field)
- Propose a fix based on reproduction steps

## Schema Info
- **Database**: `db_output` on `elvisreport.harman.com`
- **Table**: `tbl_ElvisSR` (258 columns total, ~80 accessible to SReport user)
- **Primary Key**: `TicketID` (int)
- To explore the full schema, run:
```
python .github/skills/elvis-defect-analyzer/scripts/explore_schema.py
```

## Files
- [fetch_defect.py](./scripts/fetch_defect.py) — Main script to fetch and display defect data
- [explore_schema.py](./scripts/explore_schema.py) — Schema exploration utility
- `.env` (workspace root) — Credentials (not committed, in `.gitignore`)
