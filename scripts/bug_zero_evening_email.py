"""
DA2.8 Bug Zero — Evening Review Email
End-of-day review: committed defect status (open/closed), reproduction breakdown,
today's actual inflow/outflow, and domain performance.
"""
import os, sys, io
from datetime import datetime, timedelta, date
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from dotenv import load_dotenv
import mysql.connector

_script_dir = os.path.dirname(os.path.abspath(__file__))
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
    open_steps_sql = "','".join(OPEN_STEPS)

    # Total open by FGroup (pre-integrating)
    cursor.execute(f"""
        SELECT `FGroup`, COUNT(*) as cnt FROM tbl_ElvisSR
        WHERE {BUG_ZERO_WHERE} AND `TicketStepID` IN ('{open_steps_sql}')
        GROUP BY `FGroup` ORDER BY cnt DESC
    """)
    domain_open = {r["FGroup"]: r["cnt"] for r in cursor.fetchall()}

    # Reproduction count per domain
    cursor.execute(f"""
        SELECT `FGroup`, COUNT(*) as cnt FROM tbl_ElvisSR
        WHERE {BUG_ZERO_WHERE} AND `TicketStepID` = 'Reproduction'
        GROUP BY `FGroup` ORDER BY cnt DESC
    """)
    domain_repro = {r["FGroup"]: r["cnt"] for r in cursor.fetchall()}

    # TOP + A(1) open by domain
    cursor.execute(f"""
        SELECT `FGroup`, COUNT(*) as cnt FROM tbl_ElvisSR
        WHERE {BUG_ZERO_WHERE} AND `TicketStepID` IN ('{open_steps_sql}')
          AND `PriorityID` IN ('A(1)', 'top')
        GROUP BY `FGroup` ORDER BY cnt DESC
    """)
    domain_top_a = {r["FGroup"]: r["cnt"] for r in cursor.fetchall()}

    # Platform (SlaveType = 'TYP_2') open by domain
    cursor.execute(f"""
        SELECT `FGroup`, COUNT(*) as cnt FROM tbl_ElvisSR
        WHERE {BUG_ZERO_WHERE} AND `TicketStepID` IN ('{open_steps_sql}')
          AND `SlaveType` = 'TYP_2'
        GROUP BY `FGroup` ORDER BY cnt DESC
    """)
    domain_platform = {r["FGroup"]: r["cnt"] for r in cursor.fetchall()}

    # Project (SlaveType != 'TYP_2') open by domain
    cursor.execute(f"""
        SELECT `FGroup`, COUNT(*) as cnt FROM tbl_ElvisSR
        WHERE {BUG_ZERO_WHERE} AND `TicketStepID` IN ('{open_steps_sql}')
          AND (`SlaveType` IS NULL OR `SlaveType` != 'TYP_2')
        GROUP BY `FGroup` ORDER BY cnt DESC
    """)
    domain_project = {r["FGroup"]: r["cnt"] for r in cursor.fetchall()}

    # Open by step
    cursor.execute(f"""
        SELECT `TicketStepID`, COUNT(*) as cnt FROM tbl_ElvisSR
        WHERE {BUG_ZERO_WHERE} AND `TicketStepID` IN ('{open_steps_sql}')
        GROUP BY `TicketStepID` ORDER BY cnt DESC
    """)
    step_open = {r["TicketStepID"]: r["cnt"] for r in cursor.fetchall()}

    # Open by priority
    cursor.execute(f"""
        SELECT `PriorityID`, COUNT(*) as cnt FROM tbl_ElvisSR
        WHERE {BUG_ZERO_WHERE} AND `TicketStepID` IN ('{open_steps_sql}')
        GROUP BY `PriorityID` ORDER BY cnt DESC
    """)
    priority_open = {r["PriorityID"]: r["cnt"] for r in cursor.fetchall()}

    # Today's inflow
    cursor.execute(f"""
        SELECT COUNT(*) as cnt FROM tbl_ElvisSR
        WHERE {BUG_ZERO_WHERE} AND DATE(`EnterDateTime`) = %s
    """, (today,))
    today_inflow = cursor.fetchone()["cnt"]

    # Today's outflow (integrated + rejected)
    cursor.execute(f"""
        SELECT COUNT(*) as cnt FROM tbl_ElvisSR
        WHERE {BUG_ZERO_WHERE} AND `Rejected` = 'N'
          AND DATE(`FirstIntegrDateTime`) = %s
    """, (today,))
    today_outflow = cursor.fetchone()["cnt"]
    cursor.execute(f"""
        SELECT COUNT(*) as cnt FROM tbl_ElvisSR
        WHERE {BUG_ZERO_WHERE} AND `Rejected` = 'Y'
          AND DATE(`FirstConclDateTime`) = %s
    """, (today,))
    today_outflow += cursor.fetchone()["cnt"]

    # Today's inflow by domain
    cursor.execute(f"""
        SELECT `FGroup`, COUNT(*) as cnt FROM tbl_ElvisSR
        WHERE {BUG_ZERO_WHERE} AND DATE(`EnterDateTime`) = %s
        GROUP BY `FGroup` ORDER BY cnt DESC
    """, (today,))
    today_inflow_by_domain = {r["FGroup"]: r["cnt"] for r in cursor.fetchall()}

    # Today's outflow by domain (integrated)
    cursor.execute(f"""
        SELECT `FGroup`, COUNT(*) as cnt FROM tbl_ElvisSR
        WHERE {BUG_ZERO_WHERE} AND `Rejected` = 'N'
          AND DATE(`FirstIntegrDateTime`) = %s
        GROUP BY `FGroup`
    """, (today,))
    today_outflow_by_domain = {r["FGroup"]: r["cnt"] for r in cursor.fetchall()}
    cursor.execute(f"""
        SELECT `FGroup`, COUNT(*) as cnt FROM tbl_ElvisSR
        WHERE {BUG_ZERO_WHERE} AND `Rejected` = 'Y'
          AND DATE(`FirstConclDateTime`) = %s
        GROUP BY `FGroup`
    """, (today,))
    for r in cursor.fetchall():
        fg = r["FGroup"]
        today_outflow_by_domain[fg] = today_outflow_by_domain.get(fg, 0) + r["cnt"]

    # Domain-wise daily inflow (last 5 days)
    last5 = [today - timedelta(days=i) for i in range(5)]
    earliest5 = last5[-1]
    cursor.execute(f"""
        SELECT `FGroup`, DATE(`EnterDateTime`) as d, COUNT(*) as cnt FROM tbl_ElvisSR
        WHERE {BUG_ZERO_WHERE} AND DATE(`EnterDateTime`) >= %s
        GROUP BY `FGroup`, DATE(`EnterDateTime`)
    """, (earliest5,))
    domain_daily_inflow = {}
    for r in cursor.fetchall():
        fg = r["FGroup"]
        d = r["d"]
        if isinstance(d, datetime): d = d.date()
        domain_daily_inflow.setdefault(fg, {})[d] = r["cnt"]

    # Domain-wise daily outflow (last 5 days) = integrated + rejected
    cursor.execute(f"""
        SELECT `FGroup`, DATE(`FirstIntegrDateTime`) as d, COUNT(*) as cnt FROM tbl_ElvisSR
        WHERE {BUG_ZERO_WHERE} AND `Rejected` = 'N'
          AND DATE(`FirstIntegrDateTime`) >= %s
        GROUP BY `FGroup`, DATE(`FirstIntegrDateTime`)
    """, (earliest5,))
    domain_daily_outflow = {}
    for r in cursor.fetchall():
        fg = r["FGroup"]
        d = r["d"]
        if isinstance(d, datetime): d = d.date()
        domain_daily_outflow.setdefault(fg, {})[d] = r["cnt"]

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
        domain_daily_outflow.setdefault(fg, {})
        domain_daily_outflow[fg][d] = domain_daily_outflow[fg].get(d, 0) + r["cnt"]

    # Committed today — only open (pre-integrating) tickets with FPD = today
    cursor.execute(f"""
        SELECT `TicketID`, `Title`, `FGroup`, `PlannedFixedDate`, `TicketStepID` FROM tbl_ElvisSR
        WHERE {BUG_ZERO_WHERE}
          AND `TicketStepID` IN ('{open_steps_sql}')
          AND DATE(`PlannedFixedDate`) = %s
        ORDER BY `FGroup`, `TicketID`
    """, (today,))
    committed_today = [(r["TicketID"], r["Title"] or "", r["FGroup"] or "Unknown",
                        r["PlannedFixedDate"], r["TicketStepID"] or "") for r in cursor.fetchall()]

    # Tomorrow committed — for preview
    tomorrow = today + timedelta(days=1)
    cursor.execute(f"""
        SELECT `TicketID`, `Title`, `FGroup`, `PlannedFixedDate` FROM tbl_ElvisSR
        WHERE {BUG_ZERO_WHERE} AND `TicketStepID` IN ('{open_steps_sql}')
          AND DATE(`PlannedFixedDate`) = %s
        ORDER BY `FGroup`, `TicketID`
    """, (tomorrow,))
    tomorrow_committed = [(r["TicketID"], r["Title"] or "", r["FGroup"] or "Unknown",
                           r["PlannedFixedDate"]) for r in cursor.fetchall()]

    # Today's outflow detail (integrated today) — ticket list
    cursor.execute(f"""
        SELECT `TicketID`, `Title`, `FGroup` FROM tbl_ElvisSR
        WHERE {BUG_ZERO_WHERE} AND `Rejected` = 'N'
          AND DATE(`FirstIntegrDateTime`) = %s
        ORDER BY `FGroup`, `TicketID`
    """, (today,))
    today_outflow_tickets = [(r["TicketID"], r["Title"] or "", r["FGroup"] or "Unknown") for r in cursor.fetchall()]

    # Today's inflow detail — ticket list
    cursor.execute(f"""
        SELECT `TicketID`, `Title`, `FGroup` FROM tbl_ElvisSR
        WHERE {BUG_ZERO_WHERE} AND DATE(`EnterDateTime`) = %s
        ORDER BY `FGroup`, `TicketID`
    """, (today,))
    today_inflow_tickets = [(r["TicketID"], r["Title"] or "", r["FGroup"] or "Unknown") for r in cursor.fetchall()]

    # 9-day daily inflow/outflow for burn rate
    dates = [today - timedelta(days=i) for i in range(9)]
    earliest = dates[-1]
    cursor.execute(f"""
        SELECT DATE(`EnterDateTime`) as d, COUNT(*) as cnt FROM tbl_ElvisSR
        WHERE {BUG_ZERO_WHERE} AND DATE(`EnterDateTime`) >= %s
        GROUP BY DATE(`EnterDateTime`) ORDER BY d
    """, (earliest,))
    daily_inflow = {}
    for r in cursor.fetchall():
        d = r["d"]
        if isinstance(d, datetime): d = d.date()
        daily_inflow[d] = r["cnt"]

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
        daily_outflow[d] = r["cnt"]

    cursor.execute(f"""
        SELECT DATE(`FirstConclDateTime`) as d, COUNT(*) as cnt FROM tbl_ElvisSR
        WHERE {BUG_ZERO_WHERE} AND `Rejected` = 'Y'
          AND DATE(`FirstConclDateTime`) >= %s
        GROUP BY DATE(`FirstConclDateTime`) ORDER BY d
    """, (earliest,))
    for r in cursor.fetchall():
        d = r["d"]
        if isinstance(d, datetime): d = d.date()
        daily_outflow[d] = daily_outflow.get(d, 0) + r["cnt"]

    # Crossed FPD — open (pre-integrating) tickets where PlannedFixedDate < today
    cursor.execute(f"""
        SELECT `TicketID`, `Title`, `FGroup`, `PlannedFixedDate` FROM tbl_ElvisSR
        WHERE {BUG_ZERO_WHERE} AND `TicketStepID` IN ('{open_steps_sql}')
          AND `PlannedFixedDate` IS NOT NULL
          AND DATE(`PlannedFixedDate`) < %s
          AND DATE(`PlannedFixedDate`) != '0000-00-00'
          AND YEAR(`PlannedFixedDate`) > 0
        ORDER BY `PlannedFixedDate`, `FGroup`
    """, (today,))
    crossed_fpd = [(r["TicketID"], r["Title"] or "", r["FGroup"] or "Unknown", r["PlannedFixedDate"]) for r in cursor.fetchall()]

    # FPD Not Available — open tickets where PlannedFixedDate is NULL or zero-date
    cursor.execute(f"""
        SELECT `FGroup`, COUNT(*) as cnt FROM tbl_ElvisSR
        WHERE {BUG_ZERO_WHERE} AND `TicketStepID` IN ('{open_steps_sql}')
          AND (`PlannedFixedDate` IS NULL OR DATE(`PlannedFixedDate`) = '0000-00-00' OR YEAR(`PlannedFixedDate`) = 0)
        GROUP BY `FGroup` ORDER BY cnt DESC
    """)
    fpd_not_available = [(r["FGroup"] or "Unknown", r["cnt"]) for r in cursor.fetchall()]

    cursor.close()
    conn.close()

    return {
        "today": today,
        "dates": dates,
        "domain_open": domain_open,
        "domain_repro": domain_repro,
        "domain_top_a": domain_top_a,
        "domain_platform": domain_platform,
        "domain_project": domain_project,
        "step_open": step_open,
        "priority_open": priority_open,
        "today_inflow": today_inflow,
        "today_outflow": today_outflow,
        "today_inflow_by_domain": today_inflow_by_domain,
        "today_outflow_by_domain": today_outflow_by_domain,
        "last5": last5,
        "domain_daily_inflow": domain_daily_inflow,
        "domain_daily_outflow": domain_daily_outflow,
        "committed_today": committed_today,
        "tomorrow_committed": tomorrow_committed,
        "today_outflow_tickets": today_outflow_tickets,
        "today_inflow_tickets": today_inflow_tickets,
        "daily_inflow": daily_inflow,
        "daily_outflow": daily_outflow,
        "crossed_fpd": crossed_fpd,
        "fpd_not_available": fpd_not_available,
        "total_open": sum(domain_open.values()),
    }


def build_html(data):
    today = data["today"]
    total = data["total_open"]
    dates = data["dates"]
    may_end = date(2026, 5, 31)
    days_left = (may_end - today).days
    working_days_left = sum(1 for i in range(1, days_left + 1) if (today + timedelta(days=i)).weekday() < 5)

    # Avg daily inflow (last 7 weekdays)
    last7_weekdays = []
    d_iter = today - timedelta(days=1)
    while len(last7_weekdays) < 7:
        if d_iter.weekday() < 5:
            last7_weekdays.append(d_iter)
        d_iter -= timedelta(days=1)
    avg_daily_inflow = sum(data["daily_inflow"].get(d, 0) for d in last7_weekdays) / len(last7_weekdays)
    expected_total_inflow = avg_daily_inflow * working_days_left
    daily_target = (total + expected_total_inflow) / max(working_days_left, 1)

    # Burn rate
    net_vals = [data["daily_outflow"].get(d, 0) - data["daily_inflow"].get(d, 0) for d in last7_weekdays]
    avg_net = sum(net_vals) / len(net_vals) if net_vals else 0
    avg_outflow_7d = sum(data["daily_outflow"].get(d, 0) for d in last7_weekdays) / len(last7_weekdays)
    if avg_net > 0:
        projected_days_work = int(total / avg_net) + 1
        cal_days = 0
        wd_count = 0
        while wd_count < projected_days_work:
            cal_days += 1
            if (today + timedelta(days=cal_days)).weekday() < 5:
                wd_count += 1
        projected_date = today + timedelta(days=cal_days)
        on_track = projected_date <= date(2026, 5, 31)
        burn_status = f"On Track \u2014 projected zero by {projected_date.strftime('%d-%b')}" if on_track else f"At Risk \u2014 projected zero by {projected_date.strftime('%d-%b')} (need to increase pace)"
        burn_color = "#27ae60" if on_track else "#e74c3c"
        burn_icon = "&#10004;" if on_track else "&#9888;"
    else:
        burn_status = "At Risk \u2014 no net reduction in last 7 working days"
        burn_color = "#e74c3c"
        burn_icon = "&#9888;"
        avg_net = 0

    today_in = data["today_inflow"]
    today_out = data["today_outflow"]
    net = today_out - today_in
    net_color = "#27ae60" if net > 0 else "#e74c3c"
    net_arrow = "\u25bc" if net > 0 else "\u25b2"
    net_word = "GOOD" if net > 0 else "ALERT"

    tf = "font-family:'Segoe UI',Calibri,Arial,sans-serif;"
    dot = "\u00b7"

    # Priority breakdown
    priority_open = data.get("priority_open", {})
    prio_rows = ""
    for prio in ["top", "A(1)", "B(2)", "C(3)"]:
        cnt = priority_open.get(prio, 0)
        if cnt > 0:
            prio_rows += f'<span style="display:inline-block;margin-right:12px;font-size:14px;{tf}"><strong style="color:#1a5276;">{prio}</strong>: <span style="font-weight:600;color:#d35400;">{cnt}</span></span>'

    # Today's targets — open tickets with FPD = today
    committed_today = data["committed_today"]
    committed_rows = ""
    total_committed = len(committed_today)
    if committed_today:
        for i, (tid, title, dom, fpd, step) in enumerate(committed_today):
            row_bg = '#fef2f2' if i % 2 == 0 else '#fff'
            title_short = (title[:80] + '...') if len(title) > 80 else title
            committed_rows += f'<tr style="background:{row_bg};"><td style="padding:4px 8px;font-size:12px;border-bottom:1px solid #f0f0f0;white-space:nowrap;{tf}">{tid}</td><td style="padding:4px 8px;font-size:12px;border-bottom:1px solid #f0f0f0;white-space:nowrap;{tf}">{dom}</td><td style="padding:4px 8px;font-size:12px;border-bottom:1px solid #f0f0f0;color:#555;{tf}">{title_short}</td><td style="padding:4px 8px;font-size:12px;border-bottom:1px solid #f0f0f0;color:#666;{tf}">{step}</td></tr>'
    else:
        committed_rows = '<tr><td colspan="4" style="padding:12px;font-size:13px;color:#999;text-align:center;">No open tickets with FPD today</td></tr>'

    # Domain table with Open + Platform + Project + TOP+A + Repro + 5-day In/Out
    domain_open = data["domain_open"]
    domain_repro = data["domain_repro"]
    domain_top_a = data.get("domain_top_a", {})
    domain_platform = data.get("domain_platform", {})
    domain_project = data.get("domain_project", {})
    domain_daily_inflow = data["domain_daily_inflow"]
    domain_daily_outflow = data["domain_daily_outflow"]
    last5 = sorted(data["last5"], reverse=True)
    all_domains = sorted(domain_open.keys(), key=lambda x: -domain_open[x])

    total_repro = sum(domain_repro.values())
    total_top_a = sum(domain_top_a.values())
    total_platform = sum(domain_platform.values())
    total_project = sum(domain_project.values())

    # Date headers — each date has In/Out side by side
    date_header_top = ""
    date_header_sub = ""
    for d in last5:
        dl = d.strftime("%d-%b")
        date_header_top += f'<td colspan="2" style="padding:4px 3px;font-size:11px;font-weight:600;color:#fff;text-align:center;background:#1a5276;border-bottom:1px solid #2980b9;border-left:2px solid #2980b9;{tf}">{dl}</td>'
        date_header_sub += f'<td style="padding:3px 4px;font-size:10px;font-weight:600;color:#fff;text-align:center;background:#c0392b;{tf}">In</td><td style="padding:3px 4px;font-size:10px;font-weight:600;color:#fff;text-align:center;background:#1e8449;{tf}">Out</td>'

    domain_rows = ""
    for i, dom in enumerate(all_domains):
        cnt = domain_open[dom]
        repro_cnt = domain_repro.get(dom, 0)
        top_a_cnt = domain_top_a.get(dom, 0)
        platfor_cnt = domain_platform.get(dom, 0)
        project_cnt = domain_project.get(dom, 0)
        row_bg = '#f8f9fa' if i % 2 == 0 else '#fff'
        day_cells = ""
        for d in last5:
            iv = domain_daily_inflow.get(dom, {}).get(d, 0)
            ov = domain_daily_outflow.get(dom, {}).get(d, 0)
            in_color = '#c0392b' if iv > 0 else '#ccc'
            out_color = '#1e8449' if ov > 0 else '#ccc'
            in_w = 'font-weight:600;' if iv > 0 else ''
            out_w = 'font-weight:600;' if ov > 0 else ''
            in_val = str(iv) if iv else dot
            out_val = str(ov) if ov else dot
            day_cells += f'<td style="padding:4px 4px;border-bottom:1px solid #eee;font-size:12px;text-align:center;background:#fff5f5;color:{in_color};{in_w}{tf}border-left:2px solid #e0e0e0;">{in_val}</td>'
            day_cells += f'<td style="padding:4px 4px;border-bottom:1px solid #eee;font-size:12px;text-align:center;background:#f0fff0;color:{out_color};{out_w}{tf}">{out_val}</td>'
        domain_rows += f'<tr><td style="padding:4px 8px;border-bottom:1px solid #eee;font-size:12px;white-space:nowrap;background:{row_bg};{tf}">{dom}</td><td style="padding:4px 6px;border-bottom:1px solid #eee;font-size:13px;text-align:center;font-weight:600;color:#d35400;background:{row_bg};{tf}">{cnt}</td><td style="padding:4px 6px;border-bottom:1px solid #eee;font-size:12px;text-align:center;color:#2471a3;background:{row_bg};{tf}">{platfor_cnt if platfor_cnt else dot}</td><td style="padding:4px 6px;border-bottom:1px solid #eee;font-size:12px;text-align:center;color:#1e8449;background:{row_bg};{tf}">{project_cnt if project_cnt else dot}</td><td style="padding:4px 6px;border-bottom:1px solid #eee;font-size:12px;text-align:center;color:#c0392b;font-weight:600;background:{row_bg};{tf}">{top_a_cnt if top_a_cnt else dot}</td><td style="padding:4px 6px;border-bottom:1px solid #eee;font-size:12px;text-align:center;color:#8e44ad;background:{row_bg};{tf}">{repro_cnt if repro_cnt else dot}</td>{day_cells}</tr>'

    # Totals row
    total_day_cells = ""
    for d in last5:
        ti = sum(domain_daily_inflow.get(dom, {}).get(d, 0) for dom in all_domains)
        to_ = sum(domain_daily_outflow.get(dom, {}).get(d, 0) for dom in all_domains)
        total_day_cells += f'<td style="padding:4px 4px;font-size:13px;text-align:center;font-weight:600;color:#c0392b;background:#ffe0e0;border-top:2px solid #1a5276;border-left:2px solid #e0e0e0;{tf}">{ti}</td>'
        total_day_cells += f'<td style="padding:4px 4px;font-size:13px;text-align:center;font-weight:600;color:#1e8449;background:#d5f5e3;border-top:2px solid #1a5276;{tf}">{to_}</td>'

    # Today's outflow ticket list
    outflow_tickets = data["today_outflow_tickets"]
    outflow_rows = ""
    if outflow_tickets:
        for i, (tid, title, dom) in enumerate(outflow_tickets):
            row_bg = '#f0fdf4' if i % 2 == 0 else '#fff'
            title_short = (title[:90] + '...') if len(title) > 90 else title
            outflow_rows += f'<tr style="background:{row_bg};"><td style="padding:4px 8px;font-size:12px;border-bottom:1px solid #f0f0f0;white-space:nowrap;{tf}">{tid}</td><td style="padding:4px 8px;font-size:12px;border-bottom:1px solid #f0f0f0;white-space:nowrap;{tf}">{dom}</td><td style="padding:4px 8px;font-size:12px;border-bottom:1px solid #f0f0f0;color:#555;{tf}">{title_short}</td></tr>'
    else:
        outflow_rows = '<tr><td colspan="3" style="padding:12px;font-size:13px;color:#999;text-align:center;">No outflow today</td></tr>'

    # Today's inflow ticket list
    inflow_tickets = data["today_inflow_tickets"]
    inflow_rows = ""
    if inflow_tickets:
        for i, (tid, title, dom) in enumerate(inflow_tickets):
            row_bg = '#fef2f2' if i % 2 == 0 else '#fff'
            title_short = (title[:90] + '...') if len(title) > 90 else title
            inflow_rows += f'<tr style="background:{row_bg};"><td style="padding:4px 8px;font-size:12px;border-bottom:1px solid #f0f0f0;white-space:nowrap;{tf}">{tid}</td><td style="padding:4px 8px;font-size:12px;border-bottom:1px solid #f0f0f0;white-space:nowrap;{tf}">{dom}</td><td style="padding:4px 8px;font-size:12px;border-bottom:1px solid #f0f0f0;color:#555;{tf}">{title_short}</td></tr>'
    else:
        inflow_rows = '<tr><td colspan="3" style="padding:12px;font-size:13px;color:#999;text-align:center;">No inflow today</td></tr>'

    # Tomorrow preview
    tomorrow = today + timedelta(days=1)
    tomorrow_committed = data["tomorrow_committed"]
    tomorrow_rows = ""
    if tomorrow_committed:
        for i, (tid, title, dom, fpd) in enumerate(tomorrow_committed):
            row_bg = '#eaf2f8' if i % 2 == 0 else '#fff'
            title_short = (title[:90] + '...') if len(title) > 90 else title
            tomorrow_rows += f'<tr style="background:{row_bg};"><td style="padding:4px 8px;font-size:12px;border-bottom:1px solid #f0f0f0;white-space:nowrap;{tf}">{tid}</td><td style="padding:4px 8px;font-size:12px;border-bottom:1px solid #f0f0f0;white-space:nowrap;{tf}">{dom}</td><td style="padding:4px 8px;font-size:12px;border-bottom:1px solid #f0f0f0;color:#555;{tf}">{title_short}</td></tr>'
    else:
        tomorrow_rows = '<tr><td colspan="3" style="padding:12px;font-size:13px;color:#999;text-align:center;">No tickets committed for tomorrow</td></tr>'

    # Crossed FPD — overdue tickets
    crossed_fpd = data["crossed_fpd"]
    crossed_rows = ""
    if crossed_fpd:
        for i, (tid, title, dom, fpd) in enumerate(crossed_fpd):
            row_bg = '#fef2f2' if i % 2 == 0 else '#fff'
            fpd_str = fpd.strftime('%d-%b') if hasattr(fpd, 'strftime') else str(fpd)
            days_overdue = (today - (fpd.date() if isinstance(fpd, datetime) else fpd)).days if fpd else 0
            title_short = (title[:90] + '...') if len(title) > 90 else title
            crossed_rows += f'<tr style="background:{row_bg};"><td style="padding:4px 8px;font-size:12px;border-bottom:1px solid #f0f0f0;white-space:nowrap;{tf}">{tid}</td><td style="padding:4px 8px;font-size:12px;border-bottom:1px solid #f0f0f0;white-space:nowrap;{tf}">{dom}</td><td style="padding:4px 8px;font-size:12px;border-bottom:1px solid #f0f0f0;color:#555;{tf}">{title_short}</td><td style="padding:4px 8px;font-size:12px;border-bottom:1px solid #f0f0f0;white-space:nowrap;{tf}">{fpd_str}</td><td style="padding:4px 6px;font-size:12px;border-bottom:1px solid #f0f0f0;text-align:center;color:#c0392b;font-weight:600;{tf}">{days_overdue}d</td></tr>'
    else:
        crossed_rows = '<tr><td colspan="5" style="padding:12px;font-size:13px;color:#999;text-align:center;">No overdue tickets</td></tr>'

    # FPD Not Available — domain + count
    fpd_na = data["fpd_not_available"]
    fpd_na_rows = ""
    fpd_na_total = 0
    if fpd_na:
        for i, (dom, cnt) in enumerate(fpd_na):
            row_bg = '#fff8e1' if i % 2 == 0 else '#fff'
            fpd_na_total += cnt
            fpd_na_rows += f'<tr style="background:{row_bg};"><td style="padding:6px 12px;font-size:13px;border-bottom:1px solid #f0f0f0;{tf}">{dom}</td><td style="padding:6px 10px;font-size:13px;border-bottom:1px solid #f0f0f0;text-align:center;font-weight:600;color:#e67e22;{tf}">{cnt}</td></tr>'
        fpd_na_rows += f'<tr style="background:#fef9e7;font-weight:bold;"><td style="padding:7px 12px;font-size:13px;border-top:2px solid #d4ac0d;{tf}">TOTAL</td><td style="padding:7px 10px;font-size:14px;border-top:2px solid #d4ac0d;text-align:center;color:#d35400;{tf}">{fpd_na_total}</td></tr>'
    else:
        fpd_na_rows = '<tr><td colspan="2" style="padding:12px;font-size:13px;color:#999;text-align:center;">All tickets have FPD</td></tr>'

    # 9-day trend table rows
    trend_rows = ""
    for d in reversed(dates):
        inf = data["daily_inflow"].get(d, 0)
        out = data["daily_outflow"].get(d, 0)
        n = out - inf
        n_display = f'<span style="color:#27ae60;font-weight:600;">{n}</span>' if n > 0 else (f'<span style="color:#e74c3c;font-weight:600;">{n}</span>' if n < 0 else '0')
        bg = "#f0fdf4" if n > 0 else ("#fef2f2" if n < 0 else "#fff")
        if d == today:
            day_open = total
        else:
            day_open = total
            for dd in dates:
                if dd > d and dd <= today:
                    day_open -= data["daily_inflow"].get(dd, 0) - data["daily_outflow"].get(dd, 0)
        trend_rows += f'<tr style="background:{bg};"><td style="padding:7px 14px;border-bottom:1px solid #eee;font-size:14px;{tf}">{d.strftime("%d-%b (%a)")}</td><td style="padding:7px 14px;border-bottom:1px solid #eee;text-align:center;font-size:15px;font-weight:600;color:#e67e22;{tf}">{day_open}</td><td style="padding:7px 14px;border-bottom:1px solid #eee;text-align:center;font-size:15px;{tf}">{inf}</td><td style="padding:7px 14px;border-bottom:1px solid #eee;text-align:center;font-size:15px;{tf}">{out}</td><td style="padding:7px 14px;border-bottom:1px solid #eee;text-align:center;font-size:15px;{tf}">{n_display}</td></tr>'

    html = f"""
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="margin:0;padding:0;font-family:Aptos,Calibri,'Segoe UI',Arial,sans-serif;font-size:14px;background:#f0f2f5;">
<table width="900" cellpadding="0" cellspacing="0" style="margin:20px auto;background:#fff;border-radius:8px;border:1px solid #ddd;">

<!-- Header -->
<tr><td style="background:#1a5276;padding:22px 28px;border-radius:8px 8px 0 0;">
    <span style="font-size:22px;font-weight:bold;color:#fff;letter-spacing:0.5px;">DA2.8 Bug Zero — Evening Review</span><br>
    <span style="font-size:13px;color:#aed6f1;">{today.strftime('%A, %d %B %Y')}</span>
</td></tr>

<!-- Big Numbers -->
<tr><td style="padding:20px 24px;">
<table width="100%" cellpadding="0" cellspacing="8">
<tr>
    <td width="20%" style="text-align:center;background:#fef9e7;border-radius:8px;padding:14px 8px;">
        <div style="font-size:11px;color:#999;text-transform:uppercase;font-family:Aptos,Calibri,Arial,sans-serif;">Open</div>
        <div style="font-size:38px;font-weight:600;color:#e67e22;font-family:'Segoe UI','Trebuchet MS',Calibri,sans-serif;letter-spacing:-1px;">{total}</div>
    </td>
    <td width="20%" style="text-align:center;background:#fdedec;border-radius:8px;padding:14px 8px;">
        <div style="font-size:11px;color:#999;text-transform:uppercase;font-family:Aptos,Calibri,Arial,sans-serif;">Days Left</div>
        <div style="font-size:38px;font-weight:600;color:#c0392b;font-family:'Segoe UI','Trebuchet MS',Calibri,sans-serif;letter-spacing:-1px;">{working_days_left}</div>
        <div style="font-size:10px;color:#999;">({days_left} calendar)</div>
    </td>
    <td width="20%" style="text-align:center;background:#eaf2f8;border-radius:8px;padding:14px 8px;">
        <div style="font-size:11px;color:#999;text-transform:uppercase;font-family:Aptos,Calibri,Arial,sans-serif;">Fix Rate/Day</div>
        <div style="font-size:38px;font-weight:600;color:#2471a3;font-family:'Segoe UI','Trebuchet MS',Calibri,sans-serif;letter-spacing:-1px;">{daily_target:.0f}</div>
        <div style="font-size:10px;color:#999;">incl. ~{avg_daily_inflow:.0f} inflow/day</div>
    </td>
    <td width="20%" style="text-align:center;background:{'#eafaf1' if net > 0 else '#fdedec'};border-radius:8px;padding:14px 8px;">
        <div style="font-size:11px;color:#999;text-transform:uppercase;font-family:Aptos,Calibri,Arial,sans-serif;">Today Net</div>
        <div style="font-size:38px;font-weight:600;color:{net_color};font-family:'Segoe UI','Trebuchet MS',Calibri,sans-serif;letter-spacing:-1px;">{net_arrow}{abs(net)}</div>
        <div style="font-size:10px;color:{net_color};font-weight:bold;">{net_word}</div>
    </td>
    <td width="20%" style="text-align:center;background:#f5eef8;border-radius:8px;padding:14px 8px;">
        <div style="font-size:11px;color:#999;text-transform:uppercase;font-family:Aptos,Calibri,Arial,sans-serif;">Today's Target</div>
        <div style="font-size:38px;font-weight:600;color:#7d3c98;font-family:'Segoe UI','Trebuchet MS',Calibri,sans-serif;letter-spacing:-1px;">{total_committed}</div>
        <div style="font-size:10px;color:#999;">open with FPD today</div>
    </td>
</tr>
</table>
</td></tr>

<!-- Today Inflow / Outflow / Net -->
<tr><td style="padding:0 28px 18px 28px;">
<table width="100%" cellpadding="0" cellspacing="0">
<tr>
    <td width="31%" style="text-align:center;background:#fdedec;border:2px solid #f5b7b1;border-radius:8px;padding:14px 10px;">
        <span style="font-size:12px;color:#7f8c8d;font-weight:bold;letter-spacing:1px;">TODAY INFLOW</span><br>
        <span style="font-size:34px;font-weight:600;color:#c0392b;font-family:'Segoe UI','Trebuchet MS',Calibri,sans-serif;">{today_in}</span>
    </td>
    <td width="3%"></td>
    <td width="31%" style="text-align:center;background:#eafaf1;border:2px solid #abebc6;border-radius:8px;padding:14px 10px;">
        <span style="font-size:12px;color:#7f8c8d;font-weight:bold;letter-spacing:1px;">TODAY OUTFLOW</span><br>
        <span style="font-size:34px;font-weight:600;color:#1e8449;font-family:'Segoe UI','Trebuchet MS',Calibri,sans-serif;">{today_out}</span>
    </td>
    <td width="3%"></td>
    <td width="31%" style="text-align:center;background:{'#eafaf1' if net > 0 else '#fdedec'};border:2px solid {'#abebc6' if net > 0 else '#f5b7b1'};border-radius:8px;padding:14px 10px;">
        <span style="font-size:12px;color:#7f8c8d;font-weight:bold;letter-spacing:1px;">TODAY NET</span><br>
        <span style="font-size:34px;font-weight:600;color:{net_color};font-family:'Segoe UI','Trebuchet MS',Calibri,sans-serif;">{net_arrow}{abs(net)}</span>
    </td>
</tr>
</table>
</td></tr>

<!-- Burn Rate + Priority Breakdown -->
<tr><td style="padding:0 28px 18px 28px;">
<table width="100%" cellpadding="0" cellspacing="0">
<tr>
    <td style="background:#f8f9fa;border:1px solid #ddd;border-radius:8px;padding:14px 20px;">
        <div style="font-size:12px;color:#7f8c8d;font-weight:bold;letter-spacing:1px;margin-bottom:6px;">BURN RATE PROJECTION</div>
        <div style="font-size:15px;color:{burn_color};font-weight:600;">{burn_icon} {burn_status}</div>
        <div style="font-size:12px;color:#999;margin-top:4px;">Avg net reduction (7 weekdays): {avg_net:.1f}/day | Avg outflow: {avg_outflow_7d:.1f}/day | Avg inflow: {avg_daily_inflow:.1f}/day | Need fix rate: {daily_target:.0f}/day</div>
    </td>
</tr>
<tr><td style="padding-top:10px;">
    <div style="font-size:12px;color:#7f8c8d;font-weight:bold;letter-spacing:1px;margin-bottom:4px;">OPEN BY PRIORITY</div>
    <div>{prio_rows}</div>
</td></tr>
</table>
</td></tr>

<!-- Domain Breakdown -->
<tr><td style="padding:0 28px 18px 28px;">
    <div style="font-size:16px;font-weight:600;color:#2c3e50;margin-bottom:8px;font-family:'Segoe UI',Calibri,Arial,sans-serif;">Domain-wise: Open | Inflow | Outflow <span style="font-size:12px;font-weight:normal;color:#7f8c8d;">(Last 5 Days)</span></div>
    <table width="100%" cellpadding="0" cellspacing="0" style="border:2px solid #bdc3c7;border-radius:6px;border-collapse:collapse;">
        <tr style="background:#1a5276;">
            <td rowspan="2" style="padding:8px 12px;font-size:13px;font-weight:600;color:#fff;border-right:2px solid #2980b9;font-family:'Segoe UI',Calibri,Arial,sans-serif;">Domain</td>
            <td rowspan="2" style="padding:8px 10px;font-size:13px;font-weight:600;color:#fff;text-align:center;border-right:1px solid #2980b9;font-family:'Segoe UI',Calibri,Arial,sans-serif;">Open</td>
            <td rowspan="2" style="padding:8px 10px;font-size:13px;font-weight:600;color:#fff;text-align:center;border-right:1px solid #2980b9;font-family:'Segoe UI',Calibri,Arial,sans-serif;">Platform</td>
            <td rowspan="2" style="padding:8px 10px;font-size:13px;font-weight:600;color:#fff;text-align:center;border-right:1px solid #2980b9;font-family:'Segoe UI',Calibri,Arial,sans-serif;">Project</td>
            <td rowspan="2" style="padding:8px 10px;font-size:13px;font-weight:600;color:#fff;text-align:center;border-right:1px solid #2980b9;font-family:'Segoe UI',Calibri,Arial,sans-serif;">TOP+A</td>
            <td rowspan="2" style="padding:8px 10px;font-size:13px;font-weight:600;color:#fff;text-align:center;border-right:2px solid #2980b9;font-family:'Segoe UI',Calibri,Arial,sans-serif;">Repro</td>
            {date_header_top}
        </tr>
        <tr>
            {date_header_sub}
        </tr>
        {domain_rows}
        <tr style="font-weight:bold;">
            <td style="padding:7px 10px;font-size:14px;border-top:2px solid #1a5276;background:#eaf2f8;">TOTAL</td>
            <td style="padding:7px 8px;font-size:14px;text-align:center;border-top:2px solid #1a5276;color:#d35400;background:#eaf2f8;">{total}</td>
            <td style="padding:7px 8px;font-size:14px;text-align:center;border-top:2px solid #1a5276;color:#2471a3;font-weight:600;background:#eaf2f8;">{total_platform}</td>
            <td style="padding:7px 8px;font-size:14px;text-align:center;border-top:2px solid #1a5276;color:#1e8449;font-weight:600;background:#eaf2f8;">{total_project}</td>
            <td style="padding:7px 8px;font-size:14px;text-align:center;border-top:2px solid #1a5276;color:#c0392b;font-weight:600;background:#eaf2f8;">{total_top_a}</td>
            <td style="padding:7px 8px;font-size:14px;text-align:center;border-top:2px solid #1a5276;color:#8e44ad;font-weight:600;background:#eaf2f8;">{total_repro}</td>
            {total_day_cells}
        </tr>
    </table>
</td></tr>

<!-- Committed Defects Status (FPD = Today) -->
<tr><td style="padding:0 28px 18px 28px;">
    <div style="font-size:16px;font-weight:600;color:#2c3e50;margin-bottom:8px;{tf}">&#127919; Today's Target: {total_committed} <span style="font-size:12px;font-weight:normal;color:#7f8c8d;">(Open tickets with FPD = {today.strftime('%d-%b')})</span></div>
    <table width="100%" cellpadding="0" cellspacing="0" style="border:2px solid #d7bde2;border-radius:6px;border-collapse:collapse;">
        <tr style="background:#1a5276;">
            <td style="padding:7px 12px;font-size:13px;font-weight:600;color:#fff;border-right:1px solid #2980b9;">Ticket ID</td>
            <td style="padding:7px 12px;font-size:13px;font-weight:600;color:#fff;border-right:1px solid #2980b9;">Domain</td>
            <td style="padding:7px 12px;font-size:13px;font-weight:600;color:#fff;border-right:1px solid #2980b9;">Title</td>
            <td style="padding:7px 12px;font-size:13px;font-weight:600;color:#fff;">Step</td>
        </tr>
        {committed_rows}
    </table>
</td></tr>

<!-- Today's Outflow Detail -->
<tr><td style="padding:0 28px 18px 28px;">
    <div style="font-size:16px;font-weight:600;color:#1e8449;margin-bottom:8px;font-family:'Segoe UI',Calibri,Arial,sans-serif;">&#10004; Today's Outflow: {len(outflow_tickets)} <span style="font-size:12px;font-weight:normal;color:#7f8c8d;">(Integrated today)</span></div>
    <table width="100%" cellpadding="0" cellspacing="0" style="border:2px solid #abebc6;border-radius:6px;border-collapse:collapse;">
        <tr style="background:#1e8449;">
            <td style="padding:7px 12px;font-size:13px;font-weight:600;color:#fff;border-right:1px solid #27ae60;">Ticket ID</td>
            <td style="padding:7px 12px;font-size:13px;font-weight:600;color:#fff;border-right:1px solid #27ae60;">Domain</td>
            <td style="padding:7px 12px;font-size:13px;font-weight:600;color:#fff;">Title</td>
        </tr>
        {outflow_rows}
    </table>
</td></tr>

<!-- Today's Inflow Detail -->
<tr><td style="padding:0 28px 18px 28px;">
    <div style="font-size:16px;font-weight:600;color:#c0392b;margin-bottom:8px;font-family:'Segoe UI',Calibri,Arial,sans-serif;">&#9888; Today's Inflow: {len(inflow_tickets)} <span style="font-size:12px;font-weight:normal;color:#7f8c8d;">(New tickets today)</span></div>
    <table width="100%" cellpadding="0" cellspacing="0" style="border:2px solid #f5b7b1;border-radius:6px;border-collapse:collapse;">
        <tr style="background:#c0392b;">
            <td style="padding:7px 12px;font-size:13px;font-weight:600;color:#fff;border-right:1px solid #e74c3c;">Ticket ID</td>
            <td style="padding:7px 12px;font-size:13px;font-weight:600;color:#fff;border-right:1px solid #e74c3c;">Domain</td>
            <td style="padding:7px 12px;font-size:13px;font-weight:600;color:#fff;">Title</td>
        </tr>
        {inflow_rows}
    </table>
</td></tr>

<!-- Tomorrow Preview -->
<tr><td style="padding:0 28px 18px 28px;">
    <div style="font-size:16px;font-weight:600;color:#2471a3;margin-bottom:8px;font-family:'Segoe UI',Calibri,Arial,sans-serif;">&#128197; Tomorrow's Target: {len(tomorrow_committed)} <span style="font-size:12px;font-weight:normal;color:#7f8c8d;">(FPD = {tomorrow.strftime('%d-%b')})</span></div>
    <table width="100%" cellpadding="0" cellspacing="0" style="border:2px solid #aed6f1;border-radius:6px;border-collapse:collapse;">
        <tr style="background:#2471a3;">
            <td style="padding:7px 12px;font-size:13px;font-weight:600;color:#fff;border-right:1px solid #5499c7;">Ticket ID</td>
            <td style="padding:7px 12px;font-size:13px;font-weight:600;color:#fff;border-right:1px solid #5499c7;">Domain</td>
            <td style="padding:7px 12px;font-size:13px;font-weight:600;color:#fff;">Title</td>
        </tr>
        {tomorrow_rows}
    </table>
</td></tr>

<!-- Crossed FPD (Overdue) -->
<tr><td style="padding:0 28px 18px 28px;">
    <div style="font-size:16px;font-weight:600;color:#c0392b;margin-bottom:8px;font-family:'Segoe UI',Calibri,Arial,sans-serif;">&#9888; Crossed FPD (Overdue): {len(crossed_fpd)} <span style="font-size:12px;font-weight:normal;color:#7f8c8d;">(Pre-Integrating tickets past their planned fix date)</span></div>
    <table width="100%" cellpadding="0" cellspacing="0" style="border:2px solid #f5b7b1;border-radius:6px;border-collapse:collapse;">
        <tr style="background:#c0392b;">
            <td style="padding:7px 12px;font-size:13px;font-weight:600;color:#fff;border-right:1px solid #e74c3c;">Ticket ID</td>
            <td style="padding:7px 12px;font-size:13px;font-weight:600;color:#fff;border-right:1px solid #e74c3c;">Domain</td>
            <td style="padding:7px 12px;font-size:13px;font-weight:600;color:#fff;border-right:1px solid #e74c3c;">Title</td>
            <td style="padding:7px 12px;font-size:13px;font-weight:600;color:#fff;border-right:1px solid #e74c3c;">FPD</td>
            <td style="padding:7px 12px;font-size:13px;font-weight:600;color:#fff;text-align:center;">Overdue</td>
        </tr>
        {crossed_rows}
    </table>
</td></tr>

<!-- FPD Not Available -->
<tr><td style="padding:0 28px 18px 28px;">
    <div style="font-size:16px;font-weight:600;color:#e67e22;margin-bottom:8px;font-family:'Segoe UI',Calibri,Arial,sans-serif;">&#9888; FPD Not Available: {fpd_na_total} <span style="font-size:12px;font-weight:normal;color:#7f8c8d;">(Open tickets without planned fix date)</span></div>
    <table width="100%" cellpadding="0" cellspacing="0" style="border:2px solid #f9e79f;border-radius:6px;border-collapse:collapse;">
        <tr style="background:#d4ac0d;">
            <td style="padding:7px 12px;font-size:13px;font-weight:600;color:#fff;border-right:1px solid #f1c40f;">Domain</td>
            <td style="padding:7px 12px;font-size:13px;font-weight:600;color:#fff;text-align:center;">Count</td>
        </tr>
        {fpd_na_rows}
    </table>
</td></tr>

<!-- 9-Day Trend -->
<tr><td style="padding:0 28px 18px 28px;">
    <div style="font-size:16px;font-weight:bold;color:#2c3e50;margin-bottom:8px;">9-Day Trend</div>
    <table width="100%" cellpadding="0" cellspacing="0" style="border:1px solid #ddd;border-radius:6px;">
        <tr style="background:#34495e;">
            <td style="padding:6px 12px;font-size:13px;font-weight:bold;color:#fff;">Date</td>
            <td style="padding:6px 12px;font-size:13px;font-weight:bold;color:#fdebd0;text-align:center;">Open</td>
            <td style="padding:6px 12px;font-size:13px;font-weight:bold;color:#f5b7b1;text-align:center;">In</td>
            <td style="padding:6px 12px;font-size:13px;font-weight:bold;color:#abebc6;text-align:center;">Out</td>
            <td style="padding:6px 12px;font-size:13px;font-weight:bold;color:#fff;text-align:center;">Net</td>
        </tr>
        {trend_rows}
    </table>
</td></tr>

<!-- Footer -->
<tr><td style="background:#f8f9fa;padding:14px 24px;border-radius:0 0 8px 8px;border-top:1px solid #eee;">
    <span style="font-size:11px;color:#999;">Auto-generated | DA2.8 Defect Management — Evening Review | {today.strftime('%d-%b-%Y')}</span>
</td></tr>

</table>
</body>
</html>
"""
    return html


def main():
    print("Fetching Bug Zero evening data...")
    data = fetch_data()
    total = data["total_open"]
    today = data["today"]
    days_left = (date(2026, 5, 31) - today).days

    committed = data["committed_today"]
    print(f"Total Open: {total} | Days Left: {days_left} | Today's Target (FPD today): {len(committed)}")

    print("Building evening HTML...")
    html = build_html(data)

    reports_dir = r"C:\My Workspace\Projects\MSIL\BugZero_Reports"
    os.makedirs(reports_dir, exist_ok=True)
    html_path = os.path.join(reports_dir, f"DA28_BugZero_Evening_{today.strftime('%Y%m%d')}.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"HTML saved: {html_path}")

    to = "merlin.devarapaga@harman.com"

    import win32com.client
    outlook = win32com.client.Dispatch("Outlook.Application")
    mail = outlook.CreateItem(0)
    mail.To = to
    mail.Subject = f"DA2.8 Bug Zero Evening Review — {today.strftime('%d-%b-%Y')} | {total} Open | {len(committed)} Target (FPD today)"
    mail.HTMLBody = html
    mail.Send()
    print(f"Email sent to {to}")


if __name__ == "__main__":
    main()
