---
name: batch-rca-excel
description: "Batch-fetch Elvis defects and generate AI-inferred Root Cause Analysis (RCA) and Countermeasures into an Excel file. Use when: generating RCA reports for multiple ticket IDs, populating defect Excel templates with RCA/countermeasure data, batch-analyzing Elvis tickets. Takes a list of Ticket IDs as input."
argument-hint: "Comma-separated Elvis Ticket IDs (e.g., 3727322, 3725174, 3710131)"
---

# Batch RCA Excel Generator

## What It Does
Takes a list of Elvis defect ticket IDs, fetches all details from the Elvis Report DB, analyzes each defect using domain-specific automotive software knowledge, generates probable/confirmed Root Cause Analysis and Countermeasures, and writes everything into a formatted Excel file matching the MSIL defect tracking template.

## When to Use
- You have multiple Elvis ticket IDs and need RCA + Countermeasures populated in Excel
- You need to prepare defect review data for standup, burndown, or management reporting
- You want AI-inferred probable RCA for tickets where Elvis Cause/Measures fields are empty
- You need to generate the "Till 17th March" style Excel template with RCA columns filled

## Prerequisites
- Python 3 with `mysql-connector-python`, `python-dotenv`, `pandas`, `openpyxl` installed
- A `.env` file in the `elvis-defect-analyzer` workspace root with Elvis DB credentials:
  ```
  ELVIS_DB_HOST=elvisreport.harman.com
  ELVIS_DB_USER=SReport
  ELVIS_DB_PASSWORD=<actual password>
  ELVIS_DB_NAME=db_output
  ELVIS_DB_PORT=3306
  ```
- The `elvis-defect-analyzer` skill must be available (fetch_defect.py script)

## Procedure

### Step 1: Collect Ticket IDs
Get the list of Elvis Ticket IDs from the user. These can be:
- Pasted as a list (one per line or comma-separated)
- Extracted from an image/screenshot
- Read from an existing Excel column

### Step 2: Batch Fetch Defect Data
For each ticket ID, run the fetch script to get full defect details:
```python
import sys, json
sys.path.insert(0, r'.github/skills/elvis-defect-analyzer/scripts')
from fetch_defect import fetch_defect

defect = fetch_defect(ticket_id)
```

Save all fetched data to a JSON file for analysis:
```python
# Save to all_defects_batch.json
with open('all_defects_batch.json', 'w', encoding='utf-8') as f:
    json.dump(all_data, f, indent=2, ensure_ascii=False)
```

### Step 3: Analyze Each Defect and Generate RCA

For each ticket, extract and analyze these key fields:
- **Title + ProblemDescription**: Understand what the defect is, symptoms, repro steps
- **FGroup / Component / SubComponent**: Identify the affected subsystem domain
- **Cause / BugTaxonomy / CauseID**: Use if already populated (confirmed RCA)
- **Measures / Avoidance**: Use if already populated (confirmed countermeasure)
- **RespNote / Result / InternalStatement**: Extract analysis clues
- **StateID / TicketStepID / Owner**: Determine current workflow state
- **PlannedFixedVersion / PlannedFixedDate / FixedInVersion**: Estimate closure

#### RCA Generation Rules:
1. **If Cause field is populated**: Use it as confirmed RCA, mark "Root cause identified = Yes"
2. **If Measures field is populated but Cause empty**: Infer RCA from measures, mark "Yes"
3. **If both empty**: Generate probable RCA based on:
   - Defect title and description symptoms
   - Functional group domain knowledge (BT, Projection, SWU, SVS, HMI, Camera, Media)
   - Component behavior patterns (DCSM, CarPlay, Android Auto, Tuner, etc.)
   - Mark "Root cause identified = No"

#### Countermeasure Generation Rules:
1. **If Measures/Avoidance populated**: Use as confirmed countermeasure
2. **If empty**: Generate actionable countermeasure steps based on:
   - The identified/probable root cause
   - Domain-specific debugging steps (log collection, config checks)
   - Suggested fix approach
   - Validation steps

#### Domain Knowledge for Automotive IVI Defects:

| Domain | Common Root Causes |
|--------|--------------------|
| **Bluetooth** | Profile reconnection race conditions, HFP/A2DP routing, SCO link issues, BT stack crashes |
| **Projection (AA/CP)** | DCSM state management, audio focus conflicts, session lifecycle, multi-device handling |
| **SWU (Software Update)** | Installation state persistence, tree.xml config, activation flow, OTA checkpointing |
| **SVS (Surround View)** | Calibration data loss, rendering pipeline order, 3D model assets, camera HAL init |
| **HMI IVI** | Localization gaps, state machine stuck, UI binding errors, popup rendering layers |
| **Camera** | HAL init failures, memory leaks, power sequencing, watchdog timeouts |
| **Media** | Audio routing, source persistence, tuner band switching, A2DP sink management |

### Step 4: Write to Excel

Generate an Excel file with the "Till 17th March" template format:

| Column | Content |
|--------|---------|
| A | Requested Priority (from PriorityID) |
| B | Occurrence (from Occurance) |
| C | Platform/Project (from SubProject) |
| D | Functional group (from FGroup) |
| E | Ticket ID |
| F | Title |
| G | Reported on (from EnterDateTime) |
| H | Root cause identified [Yes/No] |
| I | Fix in Progress [Yes/No] |
| J | What is the root cause? (AI-generated) |
| K | What is the counter measure? (AI-generated) |
| L | When this ticket can be closed? (from dates/state) |

#### Excel Formatting:
- Blue header row (#4472C4), white bold text, centered
- Wrap text enabled on all cells
- Column J and K: 70-75 width for readability
- RCA column (H): Green fill (#C6EFCE) for Yes, Red fill (#FFC7CE) for No
- Freeze panes at A2, auto-filter enabled
- Thin borders on all cells

Default output path: `C:\Users\mdevarapaga\Downloads\MSIL_DA2.8_Defect_List_<date>_RCA_Output.xlsx`

### Step 5: Verify and Report

After generating the Excel:
1. Read back the output to verify row count and data integrity
2. Print a summary table showing: Ticket ID | RCA Yes/No | FGroup | Title
3. Report counts: X confirmed RCA, Y probable RCA, Z total tickets

## Key Scripts
- [fetch_defect.py](../elvis-defect-analyzer/scripts/fetch_defect.py) — Fetches single defect from Elvis DB
- [generate_rca_combined.py](../scripts/generate_rca_combined.py) — Reference implementation for batch RCA Excel generation
- [batch_rca_to_excel.py](../scripts/batch_rca_to_excel.py) — Field-based extraction (used for initial raw data pull)

## Output Template
The Excel output matches the "Till 17th March" sheet structure from MSIL_DA2.8_Defect_List workbooks.

## Notes
- Date fields from Elvis may be `datetime.date` objects — always cast to `str()` before `.strip()`
- The original MSIL Excel may have pivot tables that break `openpyxl.load_workbook()` — create a standalone output file instead
- Use `io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')` for console output to handle Unicode
