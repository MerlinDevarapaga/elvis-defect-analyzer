# Elvis Defect Analyzer

![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)
![Python](https://img.shields.io/badge/python-3.8%2B-blue.svg)
![Status](https://img.shields.io/badge/status-active-green.svg)

## Overview

Elvis Defect Analyzer is a Python-based tool and GitHub Copilot skill that fetches and analyzes defect tickets from the HARMAN Elvis Report Database (MySQL). Given a Ticket ID, it queries the `tbl_ElvisSR` table and produces a structured, categorized summary of all defect attributes — enabling engineers to quickly understand bug context, severity, ownership, and resolution status.

## Features

- **Defect Lookup by Ticket ID** — Retrieve all attributes for a given Elvis defect ticket in one command.
- **Grouped Summary Output** — Results are organized into logical categories (identity, status, description, priority, system/component, root cause, dates, etc.).
- **Raw JSON Export** — Saves the full defect record as a JSON file for further processing or integration.
- **Schema Exploration** — Utility script to discover all tables and columns in the Elvis Report DB.
- **Access Verification** — Check DB permissions and available objects before querying.
- **Copilot Skill Integration** — Registered as a GitHub Copilot skill for use directly within VS Code agent conversations.

## Tech Stack

| Component | Technology |
|-----------|------------|
| Language | Python 3.8+ |
| Database | MySQL (Elvis Report DB on `elvisreport.harman.com`) |
| DB Connector | `mysql-connector-python` |
| Config Management | `python-dotenv` |
| Integration | GitHub Copilot Skills (`.github/skills/`) |

## Architecture

```
elvis-defect-analyzer/
├── scripts/
│   └── fetch_defect.py        # Main script: fetch & display defect data
├── check_access.py            # Verify DB permissions and accessible objects
├── explore_schema.py          # Explore DB schema (tables & columns)
├── query_sample.py            # Sample query for development/testing
├── SKILL.md                   # Copilot skill metadata and documentation
├── .github/
│   └── skills/
│       └── elvis-defect-analyzer/  # Copilot skill registration (mirrors root)
├── .env                       # DB credentials (not committed)
└── README.md
```

The tool connects to the Elvis Report DB (`db_output` database) via MySQL, queries `tbl_ElvisSR` by `TicketID`, and formats the ~80 accessible columns into a grouped markdown summary. The `fetch_defect.py` script is the primary entry point, while utility scripts (`check_access.py`, `explore_schema.py`) support setup and debugging.

## Prerequisites

- **Python 3.8+** installed and available on PATH
- **pip** (Python package manager)
- **Network access** to `elvisreport.harman.com:3306`
- **Elvis DB credentials** — Request the SReport password via: https://jira.harman.com/jira/servicedesk/customer/portal/84

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/HARMAN-Auto/elvis-defect-analyzer.git
   cd elvis-defect-analyzer
   ```

2. Create and activate a virtual environment (recommended):
   ```bash
   python -m venv .venv
   # Windows
   .venv\Scripts\activate
   # macOS/Linux
   source .venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install mysql-connector-python python-dotenv
   ```

4. Create a `.env` file in the project root with your credentials:
   ```env
   ELVIS_DB_HOST=elvisreport.harman.com
   ELVIS_DB_USER=SReport
   ELVIS_DB_PASSWORD=<your_password>
   ELVIS_DB_NAME=db_output
   ELVIS_DB_PORT=3306
   ```

## Usage

### Fetch a defect by Ticket ID

```bash
python scripts/fetch_defect.py <TICKET_ID>
```

**Example:**
```bash
python scripts/fetch_defect.py 3702652
```

This outputs a grouped markdown summary and saves the raw data to `defect_<TICKET_ID>.json`.

### Explore the database schema

```bash
python explore_schema.py
```

### Check database access permissions

```bash
python check_access.py
```

### Use as a Copilot Skill

When registered in a workspace, you can invoke the skill in a Copilot agent conversation by referencing a Ticket ID. The skill will automatically fetch and display defect details. See [SKILL.md](SKILL.md) for full skill documentation.

## Configuration

All configuration is managed through environment variables loaded from a `.env` file:

| Variable | Description | Default |
|----------|-------------|---------|
| `ELVIS_DB_HOST` | Elvis Report DB hostname | `elvisreport.harman.com` |
| `ELVIS_DB_USER` | Database username | `SReport` |
| `ELVIS_DB_PASSWORD` | Database password | *(required)* |
| `ELVIS_DB_NAME` | Database name | `db_output` |
| `ELVIS_DB_PORT` | MySQL port | `3306` |

## Testing

Currently, testing is manual:

1. Verify DB connectivity:
   ```bash
   python check_access.py
   ```
2. Fetch a known defect:
   ```bash
   python scripts/fetch_defect.py 3702652
   ```
3. Confirm the output contains grouped defect fields and a JSON file is created.

## InnerSource

![InnerSource](https://img.shields.io/badge/InnerSource-welcome-brightgreen.svg)

This project follows [InnerSource](https://innersourcecommons.org/) principles. Contributions from all teams within HARMAN are encouraged and welcomed. Whether it's fixing a bug, adding a feature, improving documentation, or sharing feedback — your participation makes this project better.

**Quick start for contributors**: See [GETTING_STARTED.md](GETTING_STARTED.md) to set up your environment and submit your first PR in minutes.

## Contributing

Please see [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines on how to contribute, including coding standards, branching strategy, and the PR process.

## License

This project is licensed under the Apache License 2.0 — see the [LICENSE](LICENSE) file for details.

## Contact / Maintainers

- **Team**: HARMAN Automotive Engineering
- **Questions or access requests**: Open an issue or reach out via the team's internal communication channel.
