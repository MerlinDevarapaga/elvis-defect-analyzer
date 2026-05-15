---
name: bug-zero-dashboard
description: "Send a Bug Zero Morning Status email for MSIL DA2.8. Use when: sending morning Bug Zero status, generating Bug Zero HTML dashboard, checking open/inflow/outflow by domain, emailing Bug Zero progress report, morning status email."
argument-hint: "No input needed — just invoke. Optionally specify recipient email."
---

# DA2.8 Bug Zero Morning Status

## What It Does
Queries the Elvis Report DB for Bug Zero filtered tickets, generates a styled HTML morning status dashboard with:
- **KPI Cards**: Total Open, Working Days Left (until May 31), Fix Rate/Day, Yesterday Net (▲ good / ▼ bad)
- **Yesterday Inflow / Outflow / Net boxes** with ticket counts
- **Burn Rate + Priority**: Projected zero date (On Track / At Risk) + TOP/A/B/C breakdown
- **Domain Table**: Per-domain open count with Platform/Project/TOP+A/Repro columns + last 5 days In/Out side by side (latest day first)
- **Yesterday Inflow Heatmap** by Domain + Component
- **Expected Outflow Today**: Tickets with FPD = today (Ticket ID, IC Platform ID, Domain, Type, Title)
- **Expected Outflow Tomorrow**: Same format for FPD = tomorrow
- **Crossed FPD (Overdue)**: Pre-integrating tickets past their planned fix date (Ticket ID, IC Platform ID, Domain, Type, Title, FPD, Overdue days)
- **FPD Not Available**: Open tickets without planned fix date (Ticket ID, IC Platform ID, Domain, Type, Title, Step)
- **Platform Rejected**: Open TYP_2 tickets whose IC Platform clone was rejected (should be treated as Project)
- **Closing Trend**: Daily trend from May 8, 2026 showing Open count, Inflow, Outflow, Net (latest date on top)

Then sends it via Outlook email.

## Platform/Project Classification
- **Platform**: `SlaveType = 'TYP_2'` AND IC Platform clone is NOT rejected
- **Project**: `SlaveType != 'TYP_2'` OR IC Platform clone IS rejected (`Rejected = 'Y'`)
- IC Platform link: IC Platform ticket's `IntRefNo` field holds the DA2.8 TYP_2 `TicketID`
- Domain table counts are adjusted after IC rejection check so Platform/Project numbers are accurate everywhere

## When to Use
- Morning Bug Zero status email
- Management wants a Bug Zero progress dashboard
- You need to check domain-wise open, inflow, and outflow counts
- You want an at-a-glance view of Bug Zero progress toward May 31 target
- Checking FPD compliance (overdue, not available)
- Reviewing Platform vs Project ticket split per domain

## Prerequisites
- Python 3 with `mysql-connector-python`, `python-dotenv`, `openpyxl` installed
- `.env` file in `elvis-defect-analyzer` root with Elvis DB credentials
- Microsoft Outlook running (win32com for email)
- Harman VPN connected (for DB access)

## Procedure

### Step 1 — Run the Script
```
cd elvis-defect-analyzer
python scripts/bug_zero_dashboard_email.py
```

### Step 2 — Verify Output
- Script prints: Total Open, Days Left, email sent confirmation
- HTML saved to `C:\My Workspace\Projects\MSIL\BugZero_Reports\DA28_BugZero_Dashboard_YYYYMMDD.html`
- Email sent to configured recipient with HTML body + Excel attachment (if available)

### Step 3 — Interpret Results
- **Total Open**: Pre-Integrating Bug Zero tickets (Categorizing + Reproduction + Processing)
- **Working Days Left**: Weekdays until May 31, 2026
- **Fix Rate/Day**: Open ÷ Working Days Left = required daily closures
- **Yesterday Net**: Outflow − Inflow (▲ = positive/reducing backlog, ▼ = negative/growing)
- **Domain Table**: Per-domain open count with Platform/Project split, TOP+A count, Repro count, + last 5 days In/Out
- **Heatmap**: Domain + Component breakdown of yesterday's inflow
- **Expected Outflow Today/Tomorrow**: Tickets with PlannedFixedDate = today/tomorrow, with IC Platform ticket ID
- **Crossed FPD**: Pre-integrating tickets past their FPD (with days overdue), with IC Platform ticket ID
- **FPD Not Available**: Tickets without FPD (NULL or 0000-00-00), with IC Platform ticket ID
- **Platform Rejected**: TYP_2 tickets whose IC Platform clone is rejected — these are effectively Project tickets
- **Closing Trend**: Daily Open/Inflow/Outflow/Net from May 8 (latest on top, color-coded net)

### Step 4 — Change Recipient
Edit `to = "..."` in the `main()` function of `scripts/bug_zero_dashboard_email.py`

## Script Location
`scripts/bug_zero_dashboard_email.py`

## Filter Details
See `BUG_ZERO_WHERE` in the script for the exact SQL filter matching Elvis UI "DA2.8 May End_Bug_Zero".
