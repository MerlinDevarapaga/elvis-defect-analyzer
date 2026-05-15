---
name: top-a-daily-status
description: "TOP + A(1) Daily Status agent for MSIL DA2.8. Use when: generating daily open/inflow/outflow table for TOP and A priority tickets, checking TOP+A outflow details with ticket IDs, getting daily status update for Bug Zero TOP+A priorities."
argument-hint: "No input needed — just invoke. Optionally specify start date (default: last 9 days) or 'outflow from <date>' for outflow details."
---

# TOP + A(1) Daily Status

## What It Does
Queries the Elvis Report DB and generates a daily status table for TOP (S) and A(1) priority Bug Zero tickets, showing Open/Inflow/Outflow split by priority. Can also list outflow ticket details (ID, title, domain, step, integration date).

## When to Use
- You need the "DA2.8 : Open Bugs : TOP (S) + A : Daily Status Update" table
- You want to see daily open/inflow/outflow counts for TOP and A(1) priorities
- You need outflow ticket details (which tickets moved to Integrating/Verifying)
- Management standup status update for critical priorities

## Prerequisites
- Python 3 with `mysql-connector-python`, `python-dotenv` installed
- `.env` file in `elvis-defect-analyzer` root with Elvis DB credentials

## Procedure

### For Daily Status Table (Open/Inflow/Outflow counts):
```
cd elvis-defect-analyzer
python scripts/top_a_daily_status.py
```
Output: Table with Date, Open (TOP/A split), Inflow (TOP/A), Outflow (TOP/A), Remarks

### For Outflow Ticket Details (from a specific date):
```
cd elvis-defect-analyzer
python scripts/_top_a_outflow_since.py
```
Output: List of TOP + A(1) tickets that moved to Integrating/Verifying, with Ticket ID, Title, Step, Domain, Integration Date.

To change the start date, edit the `'2026-05-08'` in the script's SQL query.

## Filter Details
- **Bug Zero filter** applied (same as dashboard)
- **Outflow** = tickets moved to Integrating (by `FirstIntegrDateTime`) on that day
- **Open** = pre-Integrating steps (Categorizing, Reproduction, Processing)
- Open counts reconstructed backward from current open using daily inflow/outflow

## Script Locations
- `scripts/top_a_daily_status.py` — daily status table
- `scripts/_top_a_outflow_since.py` — outflow ticket details from a date
