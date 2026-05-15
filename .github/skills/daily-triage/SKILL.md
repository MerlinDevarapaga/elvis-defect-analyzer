---
name: daily-triage
description: "Daily Triage Tool for MSIL DA2.8 tickets. Use when: triaging new inflow, checking priority misassignment against Harman Bug Taxonomy, suggesting actions (escalate/assign/reject), generating daily triage reports, identifying incorrectly prioritized defects, reviewing ticket priority correctness."
argument-hint: "No input required. Optional: --days N (default 2), --excel for Excel output"
---

# Daily Triage Tool

## What It Does
Fetches recent inflow tickets from Elvis Report DB, analyzes each ticket against the **Harman Bug Taxonomy** classification matrix, detects priority misassignments, and suggests corrective actions (escalate, assign, review).

### How Priority Validation Works

The tool uses 3 axes from the Bug Taxonomy to compute the *expected* priority:

1. **Severity Rank** — inferred from ticket Title + ProblemDescription keywords:
   - Top: safety, regulatory, HU restarts, unusable, complete loss
   - A: crash, freeze, reset, audio loss, not working, black screen
   - B: glitch, display issue, sub-feature, truncated, degradation
   - C: cosmetic, grammatical, spelling, nice-to-have, negligible

2. **Frequency** — taken directly from the `Occurance` DB field:
   - Always → Always | Sometimes → Sometimes | Once → Rare

3. **Recovery** — inferred from description keywords:
   - Difficult: ignition cycle, cold boot, reflash, does not recover
   - Easy: warm boot, S2R, reconnect, toggle, source change
   - Automatic: resolves itself, goes away, momentary, within seconds

These three values are looked up in the **taxonomy matrix** to get the expected priority, then compared against the assigned `PriorityID`.

### Output
- Console: Summary with mismatch table, escalation list, assignment list
- Excel: Color-coded spreadsheet (red=escalate, orange=review, green=OK)

## When to Use
- Daily morning triage of new inflow tickets
- Checking if priority assignments follow the bug taxonomy
- Identifying tickets that need escalation or reassignment
- Pre-workshop preparation to flag misclassified tickets
- Monitoring domain-wise inflow quality

## Prerequisites
- Python 3 with `mysql-connector-python`, `python-dotenv`, and `openpyxl` installed
- A `.env` file in the workspace root with Elvis DB credentials

## Procedure

### Step 1: Run the Triage Script
```bash
python scripts/daily_triage.py --excel
```

Options:
- `--days N` — Analyze last N days of inflow (default: 2)
- `--excel` — Export to `docs/output/daily_triage_YYYYMMDD.xlsx`
- `--excel path/to/file.xlsx` — Export to specific path

### Step 2: Review Mismatches
The report highlights:
- 🔴 **ESCALATE** — Priority assigned is LOWER than taxonomy expects
- 🟠 **REVIEW** — Priority assigned is HIGHER than taxonomy expects
- 🟢 **OK** — Priority matches taxonomy expectation

### Step 3: Take Action
For each flagged ticket:
- Escalate: Raise with domain team, request priority increase
- Review: Discuss if priority should be lowered
- Assign: Ticket needs owner or proper categorization
- SOA-Flag: High-priority ticket missing appropriate SOA level
