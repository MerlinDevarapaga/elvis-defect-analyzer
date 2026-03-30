# Getting Started

Welcome to **Elvis Defect Analyzer**! This guide walks you through setting up the project for local development and making your first contribution.

## 1. Clone the Repository

```bash
git clone https://github.com/HARMAN-Auto/elvis-defect-analyzer.git
cd elvis-defect-analyzer
```

## 2. Set Up the Development Environment

### Prerequisites

- Python 3.8 or later
- Network access to `elvisreport.harman.com:3306`
- Elvis DB credentials (request via [JIRA Service Desk](https://jira.harman.com/jira/servicedesk/customer/portal/84))

### Create a Virtual Environment

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate
```

### Install Dependencies

```bash
pip install mysql-connector-python python-dotenv
```

### Configure Credentials

Create a `.env` file in the project root:

```env
ELVIS_DB_HOST=elvisreport.harman.com
ELVIS_DB_USER=SReport
ELVIS_DB_PASSWORD=<your_password>
ELVIS_DB_NAME=db_output
ELVIS_DB_PORT=3306
```

> **Important**: The `.env` file is listed in `.gitignore` and must never be committed.

## 3. Build and Run Locally

There is no build step — the project runs directly with Python.

### Verify database access

```bash
python check_access.py
```

This prints your DB grants, available databases, and tables.

### Fetch a defect

```bash
python scripts/fetch_defect.py 3702652
```

You should see a grouped markdown summary and a `defect_3702652.json` file will be created.

### Explore the schema

```bash
python explore_schema.py
```

## 4. Run Tests

Currently testing is manual. Verify the tool works by:

1. Running `check_access.py` — confirms DB connectivity and permissions.
2. Running `scripts/fetch_defect.py <TICKET_ID>` — confirms data retrieval and formatting.
3. Checking that a `defect_<TICKET_ID>.json` file is generated with valid JSON.

If you add automated tests, place them in a `tests/` directory and use `pytest`:

```bash
pip install pytest
pytest tests/
```

## 5. Submit a Pull Request

1. Create a feature branch from `main`:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. Make your changes and commit with a descriptive message:
   ```bash
   git add .
   git commit -m "feat: add support for batch ticket queries"
   ```

3. Push your branch:
   ```bash
   git push origin feature/your-feature-name
   ```

4. Open a Pull Request on GitHub against the `main` branch.

5. Fill in the PR template, link any related issues, and request a review.

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed contribution guidelines including coding standards and commit conventions.
