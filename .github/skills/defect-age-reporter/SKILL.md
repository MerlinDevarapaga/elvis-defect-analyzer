---
name: defect-age-reporter
description: "Generate a Non-HMI defect age report for MSIL DA2.8 tickets before Integrating step. Groups defects by Domain Dev Team (FGroup) and age buckets (0-59, 60-119, 120-179, 180-239 days) with counts and grand totals. Use when: reporting defect ageing, reviewing ticket age distribution, generating defect burndown by domain team."
argument-hint: "No input required — runs automatically. Optional: --excel <file.xlsx> for Excel output"
---

# Defect Age Reporter

## What It Does
Queries the Elvis Report DB for all MSIL DA2.8 defects that are in pre-integration steps (Responsible/Processing), excludes HMI project defects, and generates a pivot table showing defect counts grouped by Domain Dev Team (FGroup) across age buckets (in days).

### Output Table Format

| Domain Dev Teams | 0-59 | 60-119 | 120-179 | 180-239 | Grand Total |
|------------------|------|--------|---------|---------|-------------|
| SVS              | 100  | 11     | 3       | 1       | 115         |
| Tuner            | 81   |        |         |         | 81          |
| Grand Total      | 445  | 51     | 26      | 2       | 524         |

## When to Use
- You need to see defect age distribution across domain dev teams
- Standup/burndown reporting for Non-HMI pre-integration defects
- Identifying teams with aging high-age defects (60+ days)
- Management dashboards showing defect health by FGroup

## Prerequisites
- Python 3 with `mysql-connector-python` and `python-dotenv` installed
- (Optional) `openpyxl` for Excel output
- A `.env` file in the workspace root with Elvis DB credentials:
  ```
  ELVIS_DB_HOST=elvisreport.harman.com
  ELVIS_DB_USER=SReport
  ELVIS_DB_PASSWORD=<actual password>
  ELVIS_DB_NAME=db_output
  ELVIS_DB_PORT=3306
  ```

## Procedure

### Step 1: Run the Report Script
```bash
python scripts/defect_age_report.py
```

This queries `db_output.tbl_ElvisSR` with filters:
- `ProjectID = 'MSIL_DA2.8'`
- `TicketStepID IN ('Categorizing', 'Processing', 'Reproduction')` — before Integrating
- `FGroup NOT LIKE '%HMI%'` — Non-HMI only
- `IsDeleted = 'N'`

Age is calculated as: `(today - EnterDateTime)` in days.

### Step 2: Review the Output
The script prints a pretty-printed console table with:
- Rows: Domain Dev Teams (FGroup), sorted by Grand Total descending
- Columns: Age buckets (0-59, 60-119, 120-179, 180-239 days) + Grand Total
- Bottom row: Grand totals per column

### Optional: Excel Output
```bash
python scripts/defect_age_report.py --excel defect_age_report.xlsx
```

### Optional: Save Raw Data
```bash
python scripts/defect_age_report.py --json raw_defects.json
```

## Query Details
- **Database**: `db_output` on `elvisreport.harman.com`
- **Table**: `tbl_ElvisSR`
- **Columns used**: TicketID, FGroup, EnterDateTime, TicketStepID, PriorityID, Title
- **Age buckets**: 0-59, 60-119, 120-179, 180-239 days
- Defects exceeding 239 days are included in Grand Total only

## Files
- [defect_age_report.py](../../../scripts/defect_age_report.py) — Main report script
