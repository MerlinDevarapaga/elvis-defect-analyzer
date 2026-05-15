"""
DA2.8 Bug Zero — Management Dashboard Email
Generates a visually rich HTML email with embedded charts and sends via Outlook.
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
    dates = [today - timedelta(days=i) for i in range(9)]
    earliest = dates[-1]

    # Total open by FGroup (pre-integrating)
    open_steps_sql = "','".join(OPEN_STEPS)
    cursor.execute(f"""
        SELECT `FGroup`, COUNT(*) as cnt FROM tbl_ElvisSR
        WHERE {BUG_ZERO_WHERE} AND `TicketStepID` IN ('{open_steps_sql}')
        GROUP BY `FGroup` ORDER BY cnt DESC
    """)
    domain_open = {r["FGroup"]: r["cnt"] for r in cursor.fetchall()}

    # Open in Reproduction by domain
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

    # Total open by step
    cursor.execute(f"""
        SELECT `TicketStepID`, COUNT(*) as cnt FROM tbl_ElvisSR
        WHERE {BUG_ZERO_WHERE} AND `TicketStepID` IN ('{open_steps_sql}')
        GROUP BY `TicketStepID` ORDER BY cnt DESC
    """)
    step_open = {r["TicketStepID"]: r["cnt"] for r in cursor.fetchall()}

    # Total open by priority
    cursor.execute(f"""
        SELECT `PriorityID`, COUNT(*) as cnt FROM tbl_ElvisSR
        WHERE {BUG_ZERO_WHERE} AND `TicketStepID` IN ('{open_steps_sql}')
        GROUP BY `PriorityID` ORDER BY cnt DESC
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
        daily_inflow[d] = r["cnt"]

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

    # Yesterday inflow detail by Domain + Component
    yesterday = today - timedelta(days=1)
    cursor.execute(f"""
        SELECT `FGroup`, `Component`, COUNT(*) as cnt FROM tbl_ElvisSR
        WHERE {BUG_ZERO_WHERE} AND DATE(`EnterDateTime`) = %s
        GROUP BY `FGroup`, `Component`
        ORDER BY `FGroup`, cnt DESC
    """, (yesterday,))
    yesterday_inflow_detail = []
    for r in cursor.fetchall():
        yesterday_inflow_detail.append((r["FGroup"] or "Unknown", r["Component"] or "Unknown", r["cnt"]))

    # Yesterday inflow — feature characterization from Title/Description
    cursor.execute(f"""
        SELECT `TicketID`, `Title`, `ProblemDescription`, `FGroup` FROM tbl_ElvisSR
        WHERE {BUG_ZERO_WHERE} AND DATE(`EnterDateTime`) = %s
        ORDER BY `FGroup`, `TicketID`
    """, (yesterday,))
    yesterday_tickets_raw = []
    for r in cursor.fetchall():
        yesterday_tickets_raw.append({
            "tid": r["TicketID"],
            "title": r["Title"] or "",
            "desc": r["ProblemDescription"] or "",
            "domain": r["FGroup"] or "Unknown",
        })

    # Expected outflow — open tickets with PlannedFixedDate = today
    open_steps_sql2 = "','".join(OPEN_STEPS)
    cursor.execute(f"""
        SELECT `TicketID`, `Title`, `FGroup`, `PlannedFixedDate` FROM tbl_ElvisSR
        WHERE {BUG_ZERO_WHERE} AND `TicketStepID` IN ('{open_steps_sql2}')
          AND DATE(`PlannedFixedDate`) = %s
        ORDER BY `FGroup`, `TicketID`
    """, (today,))
    expected_outflow = [(r["TicketID"], r["Title"] or "", r["FGroup"] or "Unknown", r["PlannedFixedDate"]) for r in cursor.fetchall()]

    # Expected outflow tomorrow — open tickets with PlannedFixedDate = tomorrow
    tomorrow = today + timedelta(days=1)
    cursor.execute(f"""
        SELECT `TicketID`, `Title`, `FGroup`, `PlannedFixedDate` FROM tbl_ElvisSR
        WHERE {BUG_ZERO_WHERE} AND `TicketStepID` IN ('{open_steps_sql2}')
          AND DATE(`PlannedFixedDate`) = %s
        ORDER BY `FGroup`, `TicketID`
    """, (tomorrow,))
    expected_outflow_tomorrow = [(r["TicketID"], r["Title"] or "", r["FGroup"] or "Unknown", r["PlannedFixedDate"]) for r in cursor.fetchall()]

    # Crossed FPD — open (pre-integrating) tickets where PlannedFixedDate < today and not zero-date
    cursor.execute(f"""
        SELECT `TicketID`, `Title`, `FGroup`, `PlannedFixedDate` FROM tbl_ElvisSR
        WHERE {BUG_ZERO_WHERE} AND `TicketStepID` IN ('{open_steps_sql2}')
          AND `PlannedFixedDate` IS NOT NULL
          AND DATE(`PlannedFixedDate`) < %s
          AND DATE(`PlannedFixedDate`) != '0000-00-00'
          AND YEAR(`PlannedFixedDate`) > 0
        ORDER BY `PlannedFixedDate`, `FGroup`
    """, (today,))
    crossed_fpd = [(r["TicketID"], r["Title"] or "", r["FGroup"] or "Unknown", r["PlannedFixedDate"]) for r in cursor.fetchall()]

    # FPD Not Available — open tickets where PlannedFixedDate is NULL or zero-date, grouped by domain
    cursor.execute(f"""
        SELECT `FGroup`, COUNT(*) as cnt FROM tbl_ElvisSR
        WHERE {BUG_ZERO_WHERE} AND `TicketStepID` IN ('{open_steps_sql2}')
          AND (`PlannedFixedDate` IS NULL OR DATE(`PlannedFixedDate`) = '0000-00-00' OR YEAR(`PlannedFixedDate`) = 0)
        GROUP BY `FGroup` ORDER BY cnt DESC
    """)
    fpd_not_available = [(r["FGroup"] or "Unknown", r["cnt"]) for r in cursor.fetchall()]

    cursor.close()
    conn.close()

    return {
        "today": today,
        "dates": dates,
        "last5": last5,
        "domain_open": domain_open,
        "step_open": step_open,
        "priority_open": priority_open,
        "daily_inflow": daily_inflow,
        "daily_outflow": daily_outflow,
        "domain_daily_inflow": domain_daily_inflow,
        "domain_daily_outflow": domain_daily_outflow,
        "yesterday_inflow_detail": yesterday_inflow_detail,
        "yesterday_tickets_raw": yesterday_tickets_raw,
        "expected_outflow": expected_outflow,
        "expected_outflow_tomorrow": expected_outflow_tomorrow,
        "crossed_fpd": crossed_fpd,
        "fpd_not_available": fpd_not_available,
        "total_open": sum(domain_open.values()),
        "domain_repro": domain_repro,
        "domain_top_a": domain_top_a,
    }


def build_html(data):
    today = data["today"]
    total = data["total_open"]
    may_end = date(2026, 5, 31)
    days_left = (may_end - today).days
    # Working days left (Mon-Fri only)
    working_days_left = sum(1 for i in range(1, days_left + 1) if (today + timedelta(days=i)).weekday() < 5)
    # Avg daily inflow (last 7 weekdays)
    last7_weekdays = []
    d_iter = today - timedelta(days=1)
    while len(last7_weekdays) < 7:
        if d_iter.weekday() < 5:
            last7_weekdays.append(d_iter)
        d_iter -= timedelta(days=1)
    avg_daily_inflow = sum(data["daily_inflow"].get(d, 0) for d in last7_weekdays) / len(last7_weekdays)
    # Required fix rate = (backlog + expected future inflow) / working days
    expected_total_inflow = avg_daily_inflow * working_days_left
    daily_target = (total + expected_total_inflow) / max(working_days_left, 1)
    dates = data["dates"]

    yesterday = today - timedelta(days=1)
    yest_in = data["daily_inflow"].get(yesterday, 0)
    yest_out = data["daily_outflow"].get(yesterday, 0)
    net = yest_out - yest_in
    net_color = "#27ae60" if net > 0 else "#e74c3c"
    net_arrow = "▼" if net > 0 else "▲"
    net_word = "GOOD" if net > 0 else "ALERT"

    # Top 5 domains table rows
    domain_open = data["domain_open"]
    last5 = sorted(data["last5"], reverse=True)  # latest first
    domain_daily_inflow = data["domain_daily_inflow"]
    domain_daily_outflow = data["domain_daily_outflow"]

    # All domains sorted by open count desc
    all_domains = sorted(domain_open.keys(), key=lambda x: -domain_open[x])
    domain_repro = data.get("domain_repro", {})
    total_repro = sum(domain_repro.values())
    domain_top_a = data.get("domain_top_a", {})
    total_top_a = sum(domain_top_a.values())

    # Date headers — each date has In/Out side by side
    tf = "font-family:'Segoe UI',Calibri,Arial,sans-serif;"  # table number font
    date_header_top = ""
    date_header_sub = ""
    for d in last5:
        dl = d.strftime("%d-%b")
        date_header_top += f'<td colspan="2" style="padding:4px 3px;font-size:11px;font-weight:600;color:#fff;text-align:center;background:#1a5276;border-bottom:1px solid #2980b9;border-left:2px solid #2980b9;{tf}">{dl}</td>'
        date_header_sub += f'<td style="padding:3px 4px;font-size:10px;font-weight:600;color:#fff;text-align:center;background:#c0392b;{tf}">In</td><td style="padding:3px 4px;font-size:10px;font-weight:600;color:#fff;text-align:center;background:#1e8449;{tf}">Out</td>'

    # Domain rows — per day In/Out side by side
    domain_rows = ""
    dot = "\u00b7"
    for i, dom in enumerate(all_domains):
        cnt = domain_open[dom]
        repro_cnt = domain_repro.get(dom, 0)
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
        top_a_cnt = domain_top_a.get(dom, 0)
        domain_rows += f'<tr><td style="padding:4px 8px;border-bottom:1px solid #eee;font-size:12px;white-space:nowrap;background:{row_bg};{tf}">{dom}</td><td style="padding:4px 6px;border-bottom:1px solid #eee;font-size:13px;text-align:center;font-weight:600;color:#d35400;background:{row_bg};{tf}">{cnt}</td><td style="padding:4px 6px;border-bottom:1px solid #eee;font-size:12px;text-align:center;color:#c0392b;font-weight:600;background:{row_bg};{tf}">{top_a_cnt if top_a_cnt else dot}</td><td style="padding:4px 6px;border-bottom:1px solid #eee;font-size:12px;text-align:center;color:#8e44ad;background:{row_bg};{tf}">{repro_cnt if repro_cnt else dot}</td>{day_cells}</tr>'

    # Totals row
    total_day_cells = ""
    for d in last5:
        ti = sum(domain_daily_inflow.get(dom, {}).get(d, 0) for dom in all_domains)
        to_ = sum(domain_daily_outflow.get(dom, {}).get(d, 0) for dom in all_domains)
        total_day_cells += f'<td style="padding:4px 4px;font-size:13px;text-align:center;font-weight:600;color:#c0392b;background:#ffe0e0;border-top:2px solid #1a5276;border-left:2px solid #e0e0e0;{tf}">{ti}</td>'
        total_day_cells += f'<td style="padding:4px 4px;font-size:13px;text-align:center;font-weight:600;color:#1e8449;background:#d5f5e3;border-top:2px solid #1a5276;{tf}">{to_}</td>'

    # 9-day trend table rows
    trend_rows = ""
    for d in reversed(dates):
        inf = data["daily_inflow"].get(d, 0)
        out = data["daily_outflow"].get(d, 0)
        n = out - inf
        n_display = f'<span style="color:#27ae60;font-weight:600;">{n}</span>' if n > 0 else (f'<span style="color:#e74c3c;font-weight:600;">{n}</span>' if n < 0 else '0')
        bg = "#f0fdf4" if n > 0 else ("#fef2f2" if n < 0 else "#fff")
        # Compute open count at end of each day (work backwards from today)
        if d == today:
            day_open = total
        else:
            # open(d) = total - sum of (inflow - outflow) for each day after d up to today
            # Undo future inflow (wasn't there on d) and restore future outflow (was still open on d)
            day_open = total
            for dd in dates:
                if dd > d and dd <= today:
                    day_open -= data["daily_inflow"].get(dd, 0) - data["daily_outflow"].get(dd, 0)
        trend_rows += f'<tr style="background:{bg};"><td style="padding:7px 14px;border-bottom:1px solid #eee;font-size:14px;{tf}">{d.strftime("%d-%b (%a)")}</td><td style="padding:7px 14px;border-bottom:1px solid #eee;text-align:center;font-size:15px;font-weight:600;color:#e67e22;{tf}">{day_open}</td><td style="padding:7px 14px;border-bottom:1px solid #eee;text-align:center;font-size:15px;{tf}">{inf}</td><td style="padding:7px 14px;border-bottom:1px solid #eee;text-align:center;font-size:15px;{tf}">{out}</td><td style="padding:7px 14px;border-bottom:1px solid #eee;text-align:center;font-size:15px;{tf}">{n_display}</td></tr>'

    # Burn rate indicator
    # Average net outflow over last 7 weekdays (excluding today)
    last7_wd = last7_weekdays  # already computed above
    net_vals = [data["daily_outflow"].get(d, 0) - data["daily_inflow"].get(d, 0) for d in last7_wd]
    avg_net = sum(net_vals) / len(net_vals) if net_vals else 0
    avg_outflow_7d = sum(data["daily_outflow"].get(d, 0) for d in last7_wd) / len(last7_wd)
    if avg_net > 0:
        projected_days_work = int(total / avg_net) + 1
        # Convert working days to calendar days
        cal_days = 0
        wd_count = 0
        while wd_count < projected_days_work:
            cal_days += 1
            if (today + timedelta(days=cal_days)).weekday() < 5:
                wd_count += 1
        projected_date = today + timedelta(days=cal_days)
        on_track = projected_date <= date(2026, 5, 31)
        burn_status = f"On Track — projected zero by {projected_date.strftime('%d-%b')}" if on_track else f"At Risk — projected zero by {projected_date.strftime('%d-%b')} (need to increase pace)"
        burn_color = "#27ae60" if on_track else "#e74c3c"
        burn_icon = "&#10004;" if on_track else "&#9888;"
    else:
        burn_status = "At Risk — no net reduction in last 7 working days"
        burn_color = "#e74c3c"
        burn_icon = "&#9888;"
        avg_net = 0

    # Priority breakdown
    priority_open = data["priority_open"]
    prio_rows = ""
    for prio in ["top", "A(1)", "B(2)", "C(3)"]:
        cnt = priority_open.get(prio, 0)
        if cnt > 0:
            prio_rows += f'<span style="display:inline-block;margin-right:12px;font-size:14px;{tf}"><strong style="color:#1a5276;">{prio}</strong>: <span style="font-weight:600;color:#d35400;">{cnt}</span></span>'

    # Yesterday inflow heatmap — domain + component table
    yesterday = today - timedelta(days=1)
    yesterday_detail = data["yesterday_inflow_detail"]
    yesterday_detail.sort(key=lambda x: -x[2])
    max_heat = yesterday_detail[0][2] if yesterday_detail else 1
    heatmap_rows = ""
    if yesterday_detail:
        for i, (dom, comp, cnt) in enumerate(yesterday_detail):
            intensity = int(50 + (cnt / max_heat) * 205)
            bg_color = f"rgb(255, {255 - intensity}, {255 - intensity})"
            text_color = "#fff" if intensity > 150 else "#c0392b"
            row_bg = '#f8f9fa' if i % 2 == 0 else '#fff'
            heatmap_rows += f'<tr style="background:{row_bg};"><td style="padding:6px 12px;font-size:13px;white-space:nowrap;border-bottom:1px solid #f0f0f0;{tf}">{dom}</td><td style="padding:6px 12px;font-size:13px;white-space:nowrap;border-bottom:1px solid #f0f0f0;{tf}">{comp}</td><td style="padding:6px 10px;border-bottom:1px solid #f0f0f0;text-align:center;"><div style="background:{bg_color};color:{text_color};padding:4px 10px;border-radius:4px;font-size:13px;font-weight:600;display:inline-block;min-width:30px;text-align:center;{tf}">{cnt}</div></td></tr>'
    else:
        heatmap_rows = '<tr><td colspan="3" style="padding:12px;font-size:13px;color:#999;text-align:center;">No inflow yesterday</td></tr>'

    # Tomorrow expected outflow
    tomorrow = today + timedelta(days=1)
    expected_outflow_tomorrow = data["expected_outflow_tomorrow"]
    tomorrow_rows = ""
    if expected_outflow_tomorrow:
        for i, (tid, title, dom, fpd) in enumerate(expected_outflow_tomorrow):
            row_bg = '#eaf2f8' if i % 2 == 0 else '#fff'
            title_short = (title[:90] + '...') if len(title) > 90 else title
            tomorrow_rows += f'<tr style="background:{row_bg};"><td style="padding:4px 8px;font-size:12px;border-bottom:1px solid #f0f0f0;white-space:nowrap;{tf}">{tid}</td><td style="padding:4px 8px;font-size:12px;border-bottom:1px solid #f0f0f0;white-space:nowrap;{tf}">{dom}</td><td style="padding:4px 8px;font-size:12px;border-bottom:1px solid #f0f0f0;color:#555;{tf}">{title_short}</td></tr>'
    else:
        tomorrow_rows = '<tr><td colspan="3" style="padding:12px;font-size:13px;color:#999;text-align:center;">No tickets with FPD tomorrow</td></tr>'

    # Expected outflow today (FPD = today) — ticket list
    expected_outflow = data["expected_outflow"]
    expected_rows = ""
    if expected_outflow:
        for i, (tid, title, dom, fpd) in enumerate(expected_outflow):
            row_bg = '#f0fdf4' if i % 2 == 0 else '#fff'
            title_short = (title[:90] + '...') if len(title) > 90 else title
            expected_rows += f'<tr style="background:{row_bg};"><td style="padding:4px 8px;font-size:12px;border-bottom:1px solid #f0f0f0;white-space:nowrap;{tf}">{tid}</td><td style="padding:4px 8px;font-size:12px;border-bottom:1px solid #f0f0f0;white-space:nowrap;{tf}">{dom}</td><td style="padding:4px 8px;font-size:12px;border-bottom:1px solid #f0f0f0;color:#555;{tf}">{title_short}</td></tr>'
    else:
        expected_rows = '<tr><td colspan="3" style="padding:12px;font-size:13px;color:#999;text-align:center;">No tickets with FPD today</td></tr>'

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

    html = f"""
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="margin:0;padding:0;font-family:Aptos,Calibri,'Segoe UI',Arial,sans-serif;font-size:14px;background:#f0f2f5;">
<table width="900" cellpadding="0" cellspacing="0" style="margin:20px auto;background:#fff;border-radius:8px;border:1px solid #ddd;">

<!-- Header -->
<tr><td style="background:#1a5276;padding:22px 28px;border-radius:8px 8px 0 0;">
    <span style="font-size:22px;font-weight:bold;color:#fff;letter-spacing:0.5px;">DA2.8 Bug Zero — Morning Status</span><br>
    <span style="font-size:13px;color:#aed6f1;">{today.strftime('%A, %d %B %Y')}</span>
</td></tr>

<!-- Big Numbers -->
<tr><td style="padding:20px 24px;">
<table width="100%" cellpadding="0" cellspacing="8">
<tr>
    <td width="25%" style="text-align:center;background:#fef9e7;border-radius:8px;padding:14px 8px;">
        <div style="font-size:11px;color:#999;text-transform:uppercase;font-family:Aptos,Calibri,Arial,sans-serif;">Open</div>
        <div style="font-size:38px;font-weight:600;color:#e67e22;font-family:'Segoe UI','Trebuchet MS',Calibri,sans-serif;letter-spacing:-1px;">{total}</div>
    </td>
    <td width="25%" style="text-align:center;background:#fdedec;border-radius:8px;padding:14px 8px;">
        <div style="font-size:11px;color:#999;text-transform:uppercase;font-family:Aptos,Calibri,Arial,sans-serif;">Working Days Left</div>
        <div style="font-size:38px;font-weight:600;color:#c0392b;font-family:'Segoe UI','Trebuchet MS',Calibri,sans-serif;letter-spacing:-1px;">{working_days_left}</div>
        <div style="font-size:10px;color:#999;">({days_left} calendar)</div>
    </td>
    <td width="25%" style="text-align:center;background:#eaf2f8;border-radius:8px;padding:14px 8px;">
        <div style="font-size:11px;color:#999;text-transform:uppercase;font-family:Aptos,Calibri,Arial,sans-serif;">Fix Rate/Day</div>
        <div style="font-size:38px;font-weight:600;color:#2471a3;font-family:'Segoe UI','Trebuchet MS',Calibri,sans-serif;letter-spacing:-1px;">{daily_target:.0f}</div>
        <div style="font-size:10px;color:#999;">incl. ~{avg_daily_inflow:.0f} inflow/day</div>
    </td>
    <td width="25%" style="text-align:center;background:{'#eafaf1' if net > 0 else '#fdedec'};border-radius:8px;padding:14px 8px;">
        <div style="font-size:11px;color:#999;text-transform:uppercase;font-family:Aptos,Calibri,Arial,sans-serif;">Yesterday Net</div>
        <div style="font-size:38px;font-weight:600;color:{net_color};font-family:'Segoe UI','Trebuchet MS',Calibri,sans-serif;letter-spacing:-1px;">{net_arrow}{abs(net)}</div>
        <div style="font-size:10px;color:{net_color};font-weight:bold;">{net_word}</div>
    </td>
</tr>
</table>
</td></tr>

<!-- Yesterday Inflow / Outflow / Net -->
<tr><td style="padding:0 28px 18px 28px;">
<table width="100%" cellpadding="0" cellspacing="0">
<tr>
    <td width="31%" style="text-align:center;background:#fdedec;border:2px solid #f5b7b1;border-radius:8px;padding:14px 10px;">
        <span style="font-size:12px;color:#7f8c8d;font-weight:bold;letter-spacing:1px;">YESTERDAY INFLOW</span><br>
        <span style="font-size:34px;font-weight:600;color:#c0392b;font-family:'Segoe UI','Trebuchet MS',Calibri,sans-serif;">{yest_in}</span>
    </td>
    <td width="3%"></td>
    <td width="31%" style="text-align:center;background:#eafaf1;border:2px solid #abebc6;border-radius:8px;padding:14px 10px;">
        <span style="font-size:12px;color:#7f8c8d;font-weight:bold;letter-spacing:1px;">YESTERDAY OUTFLOW</span><br>
        <span style="font-size:34px;font-weight:600;color:#1e8449;font-family:'Segoe UI','Trebuchet MS',Calibri,sans-serif;">{yest_out}</span>
    </td>
    <td width="3%"></td>
    <td width="31%" style="text-align:center;background:{'#eafaf1' if net > 0 else '#fdedec'};border:2px solid {'#abebc6' if net > 0 else '#f5b7b1'};border-radius:8px;padding:14px 10px;">
        <span style="font-size:12px;color:#7f8c8d;font-weight:bold;letter-spacing:1px;">YESTERDAY NET</span><br>
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
            <td style="padding:7px 8px;font-size:14px;text-align:center;border-top:2px solid #1a5276;color:#c0392b;font-weight:600;background:#eaf2f8;">{total_top_a}</td>
            <td style="padding:7px 8px;font-size:14px;text-align:center;border-top:2px solid #1a5276;color:#8e44ad;font-weight:600;background:#eaf2f8;">{total_repro}</td>
            {total_day_cells}
        </tr>
    </table>
</td></tr>

<!-- Expected Outflow Today (FPD = Today) -->
<tr><td style="padding:0 28px 18px 28px;">
    <div style="font-size:16px;font-weight:600;color:#1e8449;margin-bottom:8px;font-family:'Segoe UI',Calibri,Arial,sans-serif;">&#10004; Expected Outflow Today: {len(expected_outflow)} <span style="font-size:12px;font-weight:normal;color:#7f8c8d;">(FPD = {today.strftime('%d-%b')})</span></div>
    <table width="100%" cellpadding="0" cellspacing="0" style="border:2px solid #abebc6;border-radius:6px;border-collapse:collapse;">
        <tr style="background:#1e8449;">
            <td style="padding:7px 12px;font-size:13px;font-weight:600;color:#fff;border-right:1px solid #27ae60;">Ticket ID</td>
            <td style="padding:7px 12px;font-size:13px;font-weight:600;color:#fff;border-right:1px solid #27ae60;">Domain</td>
            <td style="padding:7px 12px;font-size:13px;font-weight:600;color:#fff;">Title</td>
        </tr>
        {expected_rows}
    </table>
</td></tr>

<!-- Expected Outflow Tomorrow (FPD = Tomorrow) -->
<tr><td style="padding:0 28px 18px 28px;">
    <div style="font-size:16px;font-weight:600;color:#2471a3;margin-bottom:8px;font-family:'Segoe UI',Calibri,Arial,sans-serif;">&#128197; Expected Outflow Tomorrow: {len(expected_outflow_tomorrow)} <span style="font-size:12px;font-weight:normal;color:#7f8c8d;">(FPD = {tomorrow.strftime('%d-%b')})</span></div>
    <table width="100%" cellpadding="0" cellspacing="0" style="border:2px solid #aed6f1;border-radius:6px;border-collapse:collapse;">
        <tr style="background:#2471a3;">
            <td style="padding:7px 12px;font-size:13px;font-weight:600;color:#fff;border-right:1px solid #5499c7;">Ticket ID</td>
            <td style="padding:7px 12px;font-size:13px;font-weight:600;color:#fff;border-right:1px solid #5499c7;">Domain</td>
            <td style="padding:7px 12px;font-size:13px;font-weight:600;color:#fff;">Title</td>
        </tr>
        {tomorrow_rows}
    </table>
</td></tr>

<!-- Crossed FPD (Overdue) — Pre-Integrating only -->
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
    <span style="font-size:11px;color:#999;">Auto-generated | DA2.8 Defect Management | {today.strftime('%d-%b-%Y')}</span>
</td></tr>

</table>
</body>
</html>
"""
    return html


def send_email(html_body, attachment_path, to_addr):
    import win32com.client
    outlook = win32com.client.Dispatch("Outlook.Application")
    mail = outlook.CreateItem(0)
    mail.To = to_addr
    today = date.today()
    total = sum(1 for _ in [])  # placeholder
    mail.Subject = f"DA2.8 Bug Zero Dashboard — {today.strftime('%d-%b-%Y')}"
    mail.HTMLBody = html_body
    if os.path.exists(attachment_path):
        mail.Attachments.Add(attachment_path)
    mail.Send()
    print(f"Email sent to {to_addr}")


def main():
    print("Fetching Bug Zero data...")
    data = fetch_data()
    total = data["total_open"]
    today = data["today"]
    days_left = (date(2026, 5, 31) - today).days

    print(f"Total Open: {total} | Days Left: {days_left}")
    print("Building HTML dashboard...")
    html = build_html(data)

    # Save HTML locally for reference
    reports_dir = r"C:\My Workspace\Projects\MSIL\BugZero_Reports"
    os.makedirs(reports_dir, exist_ok=True)
    html_path = os.path.join(reports_dir, f"DA28_BugZero_Dashboard_{today.strftime('%Y%m%d')}.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"HTML saved: {html_path}")

    # Send email
    downloads = os.path.join(os.path.expanduser("~"), "Downloads")
    attachment = os.path.join(downloads, f"DA28_BugZero_Daily_{today.strftime('%Y%m%d')}.xlsx")
    to = "merlin.devarapaga@harman.com"

    import win32com.client
    outlook = win32com.client.Dispatch("Outlook.Application")
    mail = outlook.CreateItem(0)
    mail.To = to
    mail.Subject = f"DA2.8 Bug Zero Morning Status — {today.strftime('%d-%b-%Y')} | {total} Open | {days_left} Days Left"
    mail.HTMLBody = html
    if os.path.exists(attachment):
        mail.Attachments.Add(attachment)
        print(f"Attached: {attachment}")
    mail.Send()
    print(f"Email sent to {to}")


if __name__ == "__main__":
    main()
