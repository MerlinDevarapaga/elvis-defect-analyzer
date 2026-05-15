---
name: workshop-updater
description: "Update a Defect Workshop Excel file with latest ticket status from Elvis DB. Use when: refreshing workshop sheets with new SOA 1-Urgent/2-Very High pre-integrating tickets, striking through tickets that moved >= Integrating, preparing daily workshop Excel updates. Takes input Excel file path (defaults to latest in Downloads)."
argument-hint: "No input needed — just invoke. Optionally specify input Excel path."
---

# Workshop Updater

## What It Does
Takes the current Defect Workshop Excel file, queries Elvis DB for the latest ticket status, adds new SOA 1-Urgent / 2-Very High pre-integrating tickets to their respective FGroup sheets, and strikes through any tickets that have moved >= Integrating. Keeps the Reference Sheet and metadata sheets untouched. Applies wrap text formatting.

## When to Use
- You need to refresh the daily Defect Workshop Excel with latest DB status
- New SOA 1/2 tickets appeared in Elvis and need to be added to workshop tabs
- You want to identify and mark tickets that progressed past integration
- Preparing the workshop file for the next day's meeting

## Prerequisites
- Python 3 with `mysql-connector-python`, `python-dotenv`, `openpyxl` installed
- A `.env` file in the `elvis-defect-analyzer` workspace root with Elvis DB credentials:
  ```
  ELVIS_DB_HOST=elvisreport.harman.com
  ELVIS_DB_USER=SReport
  ELVIS_DB_PASSWORD=<actual password>
  ELVIS_DB_NAME=db_output
  ELVIS_DB_PORT=3306
  ```

## Procedure

### Step 1 — Run the Workshop Updater Script

Execute the workshop updater script from the `elvis-defect-analyzer` workspace:

```
cd elvis-defect-analyzer
python scripts/filter_workshop_integrated.py
```

The script will:
1. Load the input workshop Excel (default: `14-Apr-Defect Worksjop.xlsx` from Downloads)
2. Extract all existing Ticket IDs from domain sheets
3. Query Elvis DB for current `TicketStepID` of all existing tickets
4. Query Elvis DB for all SOA 1-Urgent / 2-Very High pre-integrating tickets (`Categorizing`, `Processing`, `Reproduction`)
5. Add new tickets (not already in the file) to their respective FGroup sheet
6. Strikethrough all rows where the ticket is now >= Integrating
7. Apply wrap text formatting to all cells
8. Save to output file

### Step 2 — Present the Results

Report to the user:
- How many tickets are now >= Integrated (with list)
- How many new tickets were added per sheet
- How many rows were struck through per sheet
- Output file location

### Step 3 — Configuration

If the user wants to change the input/output file paths, edit the constants at the top of `scripts/filter_workshop_integrated.py`:
- `INPUT_FILE` — path to the source workshop Excel
- `OUTPUT_FILE` — path to save the updated file

### FGroup to Sheet Mapping

| FGroup | Sheet Name |
|--------|-----------|
| Media | Media |
| Bluetooth | BT |
| Projection | Projection |
| Audio | Audio |
| IOC | IOC |
| Camera | Camera |
| WiFi | Wifi |
| Systems - Core | Systems core |
| Systems - Infra | Sys infra |
| Systems - SWU Software Update | SWUP |
| USB | USB |
| SVS | SVS |

FGroups not in this mapping (HMI IVI, External Suppliers, RCA, etc.) are skipped.

### Sheets Skipped (No Filtering)
- Reference Sheet
- Repro
- Detail1
- Pivot
- Platfrom Dependency
- Raw data sheets
