"""
Generate static GitHub Pages dashboard from Elvis DB and push to gh-pages branch.
Run locally after morning email: python scripts/publish_dashboard.py
"""
import os, sys, io, json, tempfile, subprocess, shutil
from datetime import datetime, timedelta, date

if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from dotenv import load_dotenv
import mysql.connector

_script_dir = os.path.dirname(os.path.abspath(__file__))
_repo_root = os.path.dirname(_script_dir)
for _env in [os.path.join(_script_dir, ".env"), os.path.join(_script_dir, "..", ".env")]:
    if os.path.exists(_env):
        load_dotenv(_env)
        break

BUG_ZERO_WHERE = """
    `ProjectID` = 'MSIL_DA2.8'
    AND `IsDeleted` = 'N'
    AND (`ReferenceNumber` IS NULL OR `ReferenceNumber` <= 2)
    AND (`FG_SWRev` IS NULL OR `FG_SWRev` != 'P8_YTB_NA')
    AND (
        `PriorityID` IN ('A(1)', 'top')
        OR (`PriorityID` = 'B(2)' AND `Occurance` != 'Once')
        OR (`PriorityID` = 'C(3)' AND `Occurance` != 'Once')
    )
"""
OPEN_STEPS = ("Categorizing", "Reproduction", "Processing")


def get_connection():
    return mysql.connector.connect(
        host=os.getenv("ELVIS_DB_HOST"),
        user=os.getenv("ELVIS_DB_USER"),
        password=os.getenv("ELVIS_DB_PASSWORD"),
        database=os.getenv("ELVIS_DB_NAME"),
        port=int(os.getenv("ELVIS_DB_PORT", 3306)),
        connection_timeout=15,
    )


def fetch_data():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    today = date.today()
    trend_start = date(2026, 5, 8)
    trend_days = (today - trend_start).days + 1
    dates = [today - timedelta(days=i) for i in range(trend_days)]
    earliest = dates[-1]
    open_steps_sql = "','".join(OPEN_STEPS)

    # Total open by FGroup
    cursor.execute(f"""
        SELECT `FGroup`, COUNT(*) as cnt FROM tbl_ElvisSR
        WHERE {BUG_ZERO_WHERE} AND `TicketStepID` IN ('{open_steps_sql}')
        GROUP BY `FGroup` ORDER BY cnt DESC
    """)
    domain_open = {r["FGroup"]: r["cnt"] for r in cursor.fetchall()}

    # Open in Reproduction
    cursor.execute(f"""
        SELECT `FGroup`, COUNT(*) as cnt FROM tbl_ElvisSR
        WHERE {BUG_ZERO_WHERE} AND `TicketStepID` = 'Reproduction'
        GROUP BY `FGroup`
    """)
    domain_repro = {r["FGroup"]: r["cnt"] for r in cursor.fetchall()}

    # TOP+A open
    cursor.execute(f"""
        SELECT `FGroup`, COUNT(*) as cnt FROM tbl_ElvisSR
        WHERE {BUG_ZERO_WHERE} AND `TicketStepID` IN ('{open_steps_sql}')
          AND `PriorityID` IN ('A(1)', 'top')
        GROUP BY `FGroup`
    """)
    domain_top_a = {r["FGroup"]: r["cnt"] for r in cursor.fetchall()}

    # Platform (TYP_2) open
    cursor.execute(f"""
        SELECT `FGroup`, COUNT(*) as cnt FROM tbl_ElvisSR
        WHERE {BUG_ZERO_WHERE} AND `TicketStepID` IN ('{open_steps_sql}')
          AND `SlaveType` = 'TYP_2'
        GROUP BY `FGroup`
    """)
    domain_platform = {r["FGroup"]: r["cnt"] for r in cursor.fetchall()}

    # Project (non-TYP_2) open
    cursor.execute(f"""
        SELECT `FGroup`, COUNT(*) as cnt FROM tbl_ElvisSR
        WHERE {BUG_ZERO_WHERE} AND `TicketStepID` IN ('{open_steps_sql}')
          AND (`SlaveType` IS NULL OR `SlaveType` != 'TYP_2')
        GROUP BY `FGroup`
    """)
    domain_project = {r["FGroup"]: r["cnt"] for r in cursor.fetchall()}

    # Priority breakdown
    cursor.execute(f"""
        SELECT `PriorityID`, COUNT(*) as cnt FROM tbl_ElvisSR
        WHERE {BUG_ZERO_WHERE} AND `TicketStepID` IN ('{open_steps_sql}')
        GROUP BY `PriorityID`
    """)
    priority_open = {r["PriorityID"]: r["cnt"] for r in cursor.fetchall()}

    # Daily inflow
    cursor.execute(f"""
        SELECT DATE(`EnterDateTime`) as d, COUNT(*) as cnt FROM tbl_ElvisSR
        WHERE {BUG_ZERO_WHERE} AND DATE(`EnterDateTime`) >= %s
        GROUP BY DATE(`EnterDateTime`) ORDER BY d
    """, (earliest,))
    daily_inflow = {}
    for r in cursor.fetchall():
        d = r["d"]
        if isinstance(d, datetime): d = d.date()
        daily_inflow[str(d)] = r["cnt"]

    # Daily outflow (integrated + rejected)
    cursor.execute(f"""
        SELECT DATE(`FirstIntegrDateTime`) as d, COUNT(*) as cnt FROM tbl_ElvisSR
        WHERE {BUG_ZERO_WHERE} AND `Rejected` = 'N'
          AND DATE(`FirstIntegrDateTime`) >= %s
        GROUP BY DATE(`FirstIntegrDateTime`) ORDER BY d
    """, (earliest,))
    daily_outflow = {}
    for r in cursor.fetchall():
        d = r["d"]
        if isinstance(d, datetime): d = d.date()
        daily_outflow[str(d)] = r["cnt"]

    cursor.execute(f"""
        SELECT DATE(`FirstConclDateTime`) as d, COUNT(*) as cnt FROM tbl_ElvisSR
        WHERE {BUG_ZERO_WHERE} AND `Rejected` = 'Y'
          AND DATE(`FirstConclDateTime`) >= %s
        GROUP BY DATE(`FirstConclDateTime`) ORDER BY d
    """, (earliest,))
    for r in cursor.fetchall():
        d = r["d"]
        if isinstance(d, datetime): d = d.date()
        key = str(d)
        daily_outflow[key] = daily_outflow.get(key, 0) + r["cnt"]

    # Domain daily inflow/outflow (last 5 days)
    last5 = [today - timedelta(days=i) for i in range(5)]
    earliest5 = last5[-1]
    cursor.execute(f"""
        SELECT `FGroup`, DATE(`EnterDateTime`) as d, COUNT(*) as cnt FROM tbl_ElvisSR
        WHERE {BUG_ZERO_WHERE} AND DATE(`EnterDateTime`) >= %s
        GROUP BY `FGroup`, DATE(`EnterDateTime`)
    """, (earliest5,))
    domain_daily_in = {}
    for r in cursor.fetchall():
        fg = r["FGroup"]
        d = r["d"]
        if isinstance(d, datetime): d = d.date()
        domain_daily_in.setdefault(fg, {})[str(d)] = r["cnt"]

    cursor.execute(f"""
        SELECT `FGroup`, DATE(`FirstIntegrDateTime`) as d, COUNT(*) as cnt FROM tbl_ElvisSR
        WHERE {BUG_ZERO_WHERE} AND `Rejected` = 'N'
          AND DATE(`FirstIntegrDateTime`) >= %s
        GROUP BY `FGroup`, DATE(`FirstIntegrDateTime`)
    """, (earliest5,))
    domain_daily_out = {}
    for r in cursor.fetchall():
        fg = r["FGroup"]
        d = r["d"]
        if isinstance(d, datetime): d = d.date()
        domain_daily_out.setdefault(fg, {})[str(d)] = r["cnt"]

    cursor.execute(f"""
        SELECT `FGroup`, DATE(`FirstConclDateTime`) as d, COUNT(*) as cnt FROM tbl_ElvisSR
        WHERE {BUG_ZERO_WHERE} AND `Rejected` = 'Y'
          AND DATE(`FirstConclDateTime`) >= %s
        GROUP BY `FGroup`, DATE(`FirstConclDateTime`)
    """, (earliest5,))
    for r in cursor.fetchall():
        fg = r["FGroup"]
        d = r["d"]
        if isinstance(d, datetime): d = d.date()
        key = str(d)
        domain_daily_out.setdefault(fg, {})
        domain_daily_out[fg][key] = domain_daily_out[fg].get(key, 0) + r["cnt"]

    # Expected outflow today
    cursor.execute(f"""
        SELECT `TicketID`, `Title`, `FGroup`, `SlaveType` FROM tbl_ElvisSR
        WHERE {BUG_ZERO_WHERE} AND `TicketStepID` IN ('{open_steps_sql}')
          AND DATE(`PlannedFixedDate`) = %s
        ORDER BY `FGroup`, `TicketID`
    """, (today,))
    expected_today = [{"tid": r["TicketID"], "title": r["Title"] or "", "domain": r["FGroup"] or "", "slave": r["SlaveType"] or ""} for r in cursor.fetchall()]

    # Closed today with FPD today
    cursor.execute(f"""
        SELECT `TicketID`, `Title`, `FGroup`, `SlaveType` FROM tbl_ElvisSR
        WHERE {BUG_ZERO_WHERE} AND `Rejected` = 'N'
          AND DATE(`FirstIntegrDateTime`) = %s AND DATE(`PlannedFixedDate`) = %s
    """, (today, today))
    closed_today = {r["TicketID"]: {"tid": r["TicketID"], "title": r["Title"] or "", "domain": r["FGroup"] or "", "slave": r["SlaveType"] or ""} for r in cursor.fetchall()}
    cursor.execute(f"""
        SELECT `TicketID`, `Title`, `FGroup`, `SlaveType` FROM tbl_ElvisSR
        WHERE {BUG_ZERO_WHERE} AND `Rejected` = 'Y'
          AND DATE(`FirstConclDateTime`) = %s AND DATE(`PlannedFixedDate`) = %s
    """, (today, today))
    for r in cursor.fetchall():
        closed_today[r["TicketID"]] = {"tid": r["TicketID"], "title": r["Title"] or "", "domain": r["FGroup"] or "", "slave": r["SlaveType"] or ""}

    # Expected outflow tomorrow
    tomorrow = today + timedelta(days=1)
    cursor.execute(f"""
        SELECT `TicketID`, `Title`, `FGroup`, `SlaveType` FROM tbl_ElvisSR
        WHERE {BUG_ZERO_WHERE} AND `TicketStepID` IN ('{open_steps_sql}')
          AND DATE(`PlannedFixedDate`) = %s
        ORDER BY `FGroup`, `TicketID`
    """, (tomorrow,))
    expected_tomorrow = [{"tid": r["TicketID"], "title": r["Title"] or "", "domain": r["FGroup"] or "", "slave": r["SlaveType"] or ""} for r in cursor.fetchall()]

    # Crossed FPD
    cursor.execute(f"""
        SELECT `TicketID`, `Title`, `FGroup`, `PlannedFixedDate`, `SlaveType` FROM tbl_ElvisSR
        WHERE {BUG_ZERO_WHERE} AND `TicketStepID` IN ('{open_steps_sql}')
          AND `PlannedFixedDate` IS NOT NULL
          AND DATE(`PlannedFixedDate`) < %s
          AND DATE(`PlannedFixedDate`) != '0000-00-00'
          AND YEAR(`PlannedFixedDate`) > 0
        ORDER BY `FGroup`, `TicketID`
    """, (today,))
    crossed_fpd = []
    for r in cursor.fetchall():
        fpd = r["PlannedFixedDate"]
        if isinstance(fpd, datetime): fpd = fpd.date()
        crossed_fpd.append({"tid": r["TicketID"], "title": r["Title"] or "", "domain": r["FGroup"] or "",
                            "fpd": str(fpd), "slave": r["SlaveType"] or "",
                            "overdue": (today - fpd).days if fpd else 0})

    # FPD NA
    cursor.execute(f"""
        SELECT `TicketID`, `Title`, `FGroup`, `TicketStepID`, `SlaveType` FROM tbl_ElvisSR
        WHERE {BUG_ZERO_WHERE} AND `TicketStepID` IN ('{open_steps_sql}')
          AND (`PlannedFixedDate` IS NULL OR DATE(`PlannedFixedDate`) = '0000-00-00' OR YEAR(`PlannedFixedDate`) = 0)
        ORDER BY `FGroup`, `TicketID`
    """)
    fpd_na = [{"tid": r["TicketID"], "title": r["Title"] or "", "domain": r["FGroup"] or "",
               "step": r["TicketStepID"] or "", "slave": r["SlaveType"] or ""} for r in cursor.fetchall()]

    # IC Platform rejection check
    all_open_typ2_ids = set()
    cursor.execute(f"""
        SELECT `TicketID` FROM tbl_ElvisSR
        WHERE {BUG_ZERO_WHERE} AND `TicketStepID` IN ('{open_steps_sql}')
          AND `SlaveType` = 'TYP_2'
    """)
    for r in cursor.fetchall():
        all_open_typ2_ids.add(r["TicketID"])

    # Collect all TYP_2 ids from ticket lists too
    for lst in [expected_today, expected_tomorrow]:
        for t in lst:
            if t["slave"] == "TYP_2":
                all_open_typ2_ids.add(t["tid"])
    for t in crossed_fpd:
        if t["slave"] == "TYP_2":
            all_open_typ2_ids.add(t["tid"])
    for t in fpd_na:
        if t["slave"] == "TYP_2":
            all_open_typ2_ids.add(t["tid"])

    ic_rejected = set()
    ic_ticket_map = {}
    if all_open_typ2_ids:
        ph = ",".join(["%s"] * len(all_open_typ2_ids))
        cursor.execute(f"""
            SELECT `TicketID`, `IntRefNo`, `Rejected` FROM tbl_ElvisSR
            WHERE `ProjectID` = 'Intelligent Cockpit Platform'
              AND `IntRefNo` IN ({ph})
        """, [str(tid) for tid in all_open_typ2_ids])
        for r in cursor.fetchall():
            try:
                da28_tid = int(r["IntRefNo"])
                ic_ticket_map[da28_tid] = r["TicketID"]
                if r["Rejected"] == "Y":
                    ic_rejected.add(da28_tid)
            except (ValueError, TypeError):
                pass

    # Adjust platform/project for IC rejection
    for tid in ic_rejected:
        if tid in all_open_typ2_ids:
            # Find which domain this ticket belongs to — lookup from any list
            for lst in [expected_today, expected_tomorrow]:
                for t in lst:
                    if t["tid"] == tid:
                        dom = t["domain"]
                        domain_platform[dom] = domain_platform.get(dom, 0) - 1
                        domain_project[dom] = domain_project.get(dom, 0) + 1
                        if domain_platform.get(dom, 0) <= 0:
                            domain_platform.pop(dom, None)

    cursor.close()
    conn.close()

    # Compute type for each ticket
    def ttype(slave, tid):
        if slave == "TYP_2" and tid not in ic_rejected:
            return "Platform"
        return "Project"

    for t in expected_today:
        t["type"] = ttype(t["slave"], t["tid"])
        t["ic"] = ic_ticket_map.get(t["tid"], "")
    for tid, t in closed_today.items():
        t["type"] = ttype(t["slave"], t["tid"])
        t["ic"] = ic_ticket_map.get(t["tid"], "")
    for t in expected_tomorrow:
        t["type"] = ttype(t["slave"], t["tid"])
        t["ic"] = ic_ticket_map.get(t["tid"], "")
    for t in crossed_fpd:
        t["type"] = ttype(t["slave"], t["tid"])
        t["ic"] = ic_ticket_map.get(t["tid"], "")
    for t in fpd_na:
        t["type"] = ttype(t["slave"], t["tid"])
        t["ic"] = ic_ticket_map.get(t["tid"], "")

    # Platform rejected list
    plat_rejected = []
    cursor2 = get_connection()
    c2 = cursor2.cursor(dictionary=True)
    c2.execute(f"""
        SELECT `TicketID`, `Title`, `FGroup`, `TicketStepID`, `PlannedFixedDate` FROM tbl_ElvisSR
        WHERE {BUG_ZERO_WHERE} AND `TicketStepID` IN ('{open_steps_sql}')
          AND `SlaveType` = 'TYP_2'
        ORDER BY `FGroup`, `TicketID`
    """)
    for r in c2.fetchall():
        if r["TicketID"] in ic_rejected:
            fpd_val = r["PlannedFixedDate"]
            if isinstance(fpd_val, datetime): fpd_val = fpd_val.date()
            plat_rejected.append({
                "tid": r["TicketID"], "title": r["Title"] or "", "domain": r["FGroup"] or "",
                "step": r["TicketStepID"] or "", "fpd": str(fpd_val) if fpd_val else "",
                "ic": ic_ticket_map.get(r["TicketID"], ""),
            })
    c2.close()
    cursor2.close()

    # Build trend data
    total_open = sum(domain_open.values())
    trend = []
    for d in dates:
        ds = str(d)
        inf = daily_inflow.get(ds, 0)
        out = daily_outflow.get(ds, 0)
        net = out - inf
        if d == today:
            day_open = total_open
        else:
            day_open = total_open
            for dd in dates:
                if dd > d and dd <= today:
                    day_open -= daily_inflow.get(str(dd), 0) - daily_outflow.get(str(dd), 0)
        trend.append({"date": ds, "day": d.strftime("%d-%b (%a)"), "open": day_open, "inflow": inf, "outflow": out, "net": net})

    # Yesterday stats
    yesterday = today - timedelta(days=1)
    yest_in = daily_inflow.get(str(yesterday), 0)
    yest_out = daily_outflow.get(str(yesterday), 0)

    # Working days left
    may_end = date(2026, 5, 31)
    days_left = (may_end - today).days
    working_days_left = sum(1 for i in range(1, days_left + 1) if (today + timedelta(days=i)).weekday() < 5)

    # Avg daily inflow (last 7 weekdays)
    last7_wd = []
    d_iter = today - timedelta(days=1)
    while len(last7_wd) < 7:
        if d_iter.weekday() < 5:
            last7_wd.append(d_iter)
        d_iter -= timedelta(days=1)
    avg_inflow = sum(daily_inflow.get(str(d), 0) for d in last7_wd) / 7
    avg_outflow = sum(daily_outflow.get(str(d), 0) for d in last7_wd) / 7
    avg_net = avg_outflow - avg_inflow
    fix_rate = (total_open + avg_inflow * working_days_left) / max(working_days_left, 1)

    if avg_net > 0:
        proj_wd = int(total_open / avg_net) + 1
        cal = 0
        wd = 0
        while wd < proj_wd:
            cal += 1
            if (today + timedelta(days=cal)).weekday() < 5:
                wd += 1
        projected_zero = str(today + timedelta(days=cal))
    else:
        projected_zero = None

    now = datetime.now()
    return {
        "generated": now.strftime("%Y-%m-%d %H:%M"),
        "generated_display": now.strftime("%A, %d %B %Y — %I:%M %p"),
        "total_open": total_open,
        "days_left": days_left,
        "working_days_left": working_days_left,
        "fix_rate": round(fix_rate, 1),
        "avg_inflow": round(avg_inflow, 1),
        "avg_outflow": round(avg_outflow, 1),
        "avg_net": round(avg_net, 1),
        "projected_zero": projected_zero,
        "yest_in": yest_in,
        "yest_out": yest_out,
        "yest_net": yest_out - yest_in,
        "priority_open": priority_open,
        "domain_open": domain_open,
        "domain_platform": domain_platform,
        "domain_project": domain_project,
        "domain_top_a": domain_top_a,
        "domain_repro": domain_repro,
        "last5": [str(d) for d in last5],
        "domain_daily_in": {k: v for k, v in domain_daily_in.items()},
        "domain_daily_out": {k: v for k, v in domain_daily_out.items()},
        "trend": trend,
        "expected_today": expected_today,
        "closed_today": list(closed_today.values()),
        "expected_tomorrow": expected_tomorrow,
        "crossed_fpd": crossed_fpd,
        "fpd_na": fpd_na,
        "plat_rejected": plat_rejected,
    }


def publish(data):
    """Write index.html + data.json to a temp dir, commit to gh-pages, push."""
    # Read the template
    template_path = os.path.join(_repo_root, "site", "index.html")
    if not os.path.exists(template_path):
        print(f"ERROR: {template_path} not found. Create the site/index.html template first.")
        sys.exit(1)

    with open(template_path, "r", encoding="utf-8") as f:
        template = f.read()

    data_json = json.dumps(data, default=str, ensure_ascii=False)

    # Inject data into template
    html = template.replace("/*__DASHBOARD_DATA__*/", f"window.__DATA__ = {data_json};")

    tmpdir = tempfile.mkdtemp(prefix="bugzero_pages_")
    try:
        # Write files
        with open(os.path.join(tmpdir, "index.html"), "w", encoding="utf-8") as f:
            f.write(html)
        # .nojekyll to skip Jekyll processing
        with open(os.path.join(tmpdir, ".nojekyll"), "w") as f:
            f.write("")

        # Git operations
        git = lambda *args: subprocess.run(["git"] + list(args), cwd=tmpdir, capture_output=True, text=True)

        git("init", "-b", "gh-pages")
        git("config", "user.email", "bugzero-bot@harman.com")
        git("config", "user.name", "Bug Zero Dashboard Bot")
        git("add", "-A")
        git("commit", "-m", f"Dashboard update {data['generated']}")

        # Push to harman remote
        harman_url = "https://github.com/HARMAN-Auto/msil-da28-ytb-applicable-tracker.git"
        git("remote", "add", "origin", harman_url)
        result = git("push", "origin", "gh-pages", "--force")
        if result.returncode != 0:
            print(f"Push failed: {result.stderr}")
            # Try personal remote as fallback
            personal_url = "https://github.com/MerlinDevarapaga/elvis-defect-analyzer.git"
            git("remote", "set-url", "origin", personal_url)
            result = git("push", "origin", "gh-pages", "--force")
            if result.returncode != 0:
                print(f"Personal push also failed: {result.stderr}")
                return False
            print("Pushed to personal repo instead.")
        else:
            print("Pushed to HARMAN-Auto repo.")
        return True
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def main():
    print("Fetching Bug Zero data for static dashboard...")
    data = fetch_data()
    print(f"Total Open: {data['total_open']} | Working Days Left: {data['working_days_left']}")
    print("Publishing to GitHub Pages...")
    if publish(data):
        print("Done! Dashboard will be live shortly.")
    else:
        print("Failed to publish.")


if __name__ == "__main__":
    main()
