"""Regenerate all published dashboard pages from one LIVE Elvis DB snapshot.

The same scope is used for the Overview cards and both detail pages so their
headline, domain, FPD, and priority totals always reconcile.

Usage: python scripts/update_overview_live.py
"""
import math
import os
import re
from datetime import date, datetime, timedelta
from html import escape

from dotenv import load_dotenv
import mysql.connector

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TARGET_FILES = [os.path.join(REPO_ROOT, "index.html"), os.path.join(REPO_ROOT, "overview.html")]
DETAIL_FILES = {
    "ytb": os.path.join(REPO_ROOT, "ytb.html"),
    "non-ytb": os.path.join(REPO_ROOT, "non-ytb.html"),
    "current-release": os.path.join(REPO_ROOT, "current-release.html"),
}

BASE_WHERE = """
    `ProjectID` = 'MSIL_DA2.8'
    AND `IsDeleted` = 'N'
    AND `ReferenceNumber` <= 2
"""
OPEN_STEPS = ("Categorizing", "Reproduction", "Processing")
YTB_SCOPE = "`FG_SWRev` != 'P8_YTB_NA'"
NONYTB_SCOPE = "`FG_SWRev` = 'P8_YTB_NA'"
NONYTB_TARGET_DATE_TEXT = os.getenv("NONYTB_TARGET_DATE", "2026-10-31")
CURRENT_RELEASE_MILESTONE = os.getenv("CURRENT_RELEASE_MILESTONE", "R10.50")
CURRENT_RELEASE_TARGET_DATE_TEXT = os.getenv("CURRENT_RELEASE_TARGET_DATE", "2026-10-13")


def parse_config_date(value, fallback):
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        return fallback


NONYTB_TARGET_DATE = parse_config_date(NONYTB_TARGET_DATE_TEXT, date(2026, 10, 31))
CURRENT_RELEASE_TARGET_DATE = parse_config_date(CURRENT_RELEASE_TARGET_DATE_TEXT, date(2026, 10, 13))
CURRENT_RELEASE_SCOPE = f"`Milestone` = '{CURRENT_RELEASE_MILESTONE}'"
CURRENT_RELEASE_LABEL = f"Milestone {CURRENT_RELEASE_MILESTONE}"
DETAIL_PAGE_SHELL = {
    "ytb": {
        "label": "YTB",
        "title": "MSIL DA2.8 &mdash; YTB Defects",
    },
    "non-ytb": {
        "label": "Non-YTB",
        "title": "MSIL DA2.8 &mdash; Non YTB Defects",
    },
    "current-release": {
        "label": CURRENT_RELEASE_MILESTONE,
        "title": f"MSIL DA2.8 &mdash; {CURRENT_RELEASE_LABEL} Defects",
    },
}

for env_path in (
    os.path.join(REPO_ROOT, ".env"),
    os.path.join(REPO_ROOT, "scripts", "MSIL_R9.42_Dashboard", ".env"),
):
    if os.path.exists(env_path):
        load_dotenv(env_path)

conn = mysql.connector.connect(
    host=os.getenv("ELVIS_DB_HOST"),
    user=os.getenv("ELVIS_DB_USER"),
    password=os.getenv("ELVIS_DB_PASSWORD"),
    database=os.getenv("ELVIS_DB_NAME"),
    port=int(os.getenv("ELVIS_DB_PORT", "3306")),
    connection_timeout=15,
)
cur = conn.cursor(dictionary=True)
open_steps_sql = "','".join(OPEN_STEPS)


def headline(scope_where):
    cur.execute(f"""
        SELECT
            COUNT(*) AS open_total,
            SUM(CASE WHEN `PlannedFixedDate` IS NULL OR `PlannedFixedDate` = '0000-00-00' THEN 1 ELSE 0 END) AS no_fpd,
            SUM(CASE WHEN `PlannedFixedDate` IS NOT NULL AND `PlannedFixedDate` != '0000-00-00'
                     AND DATE(`PlannedFixedDate`) < CURDATE() THEN 1 ELSE 0 END) AS crossed_fpd,
            SUM(CASE WHEN `SlaveType` = 'TYP_2' THEN 1 ELSE 0 END) AS platform_total
        FROM tbl_ElvisSR
        WHERE {BASE_WHERE} AND {scope_where} AND `TicketStepID` IN ('{open_steps_sql}')
    """)
    return cur.fetchone()


def domain_priority_split(scope_where):
    cur.execute(f"""
        SELECT `FGroup`,
            SUM(CASE WHEN `PriorityID` IN ('top','A(1)') THEN 1 ELSE 0 END) AS top_a,
            SUM(CASE WHEN `PriorityID` IN ('B(2)','C(3)') AND `Occurance` = 'Always' THEN 1 ELSE 0 END) AS bc_always,
            SUM(CASE WHEN `PriorityID` IN ('B(2)','C(3)') AND `Occurance` IN ('Sometimes','Once') THEN 1 ELSE 0 END) AS bc_once_some,
            COUNT(*) AS total
        FROM tbl_ElvisSR
        WHERE {BASE_WHERE} AND {scope_where}
            AND `TicketStepID` IN ('{open_steps_sql}')
        GROUP BY `FGroup`
        HAVING total > 0
        ORDER BY total DESC
    """)
    return cur.fetchall()


def detail_snapshot(scope_where, extra_where=None):
    extra_clause = f" AND {extra_where}" if extra_where else ""
    cur.execute(f"""
        SELECT
            SUM(`TicketStepID` IN ('{open_steps_sql}')) AS open_total,
            SUM(`TicketStepID` = 'Integrating') AS integrating,
            SUM(`TicketStepID` = 'Verifying') AS verifying
        FROM tbl_ElvisSR
        WHERE {BASE_WHERE} AND {scope_where}{extra_clause}
    """)
    summary = cur.fetchone()
    cur.execute(f"""
        SELECT `PriorityID`, COUNT(*) AS cnt FROM tbl_ElvisSR
        WHERE {BASE_WHERE} AND {scope_where}{extra_clause} AND `TicketStepID` IN ('{open_steps_sql}')
        GROUP BY `PriorityID`
        ORDER BY FIELD(`PriorityID`, 'top', 'A(1)', 'B(2)', 'C(3)'), `PriorityID`
    """)
    priorities = cur.fetchall()
    cur.execute(f"""
        SELECT `FGroup`, COUNT(*) AS total,
            SUM(`PriorityID` IN ('top','A(1)')) AS top_a,
            SUM(`PriorityID` IN ('B(2)','C(3)') AND `Occurance` = 'Always') AS bc_always,
            SUM(`PriorityID` IN ('B(2)','C(3)') AND `Occurance` = 'Sometimes') AS bc_sometimes,
            SUM(`PriorityID` IN ('B(2)','C(3)') AND `Occurance` = 'Once') AS bc_once,
            SUM(`TicketStepID` = 'Reproduction') AS repro,
            SUM(`PlannedFixedDate` IS NOT NULL AND `PlannedFixedDate` != '0000-00-00'
                AND DATE(`PlannedFixedDate`) < CURDATE()) AS crossed,
            SUM(`PlannedFixedDate` IS NULL OR `PlannedFixedDate` = '0000-00-00') AS no_fpd,
            SUM(DATEDIFF(CURDATE(), DATE(`EnterDateTime`)) BETWEEN 0 AND 7) AS age_0_7,
            SUM(DATEDIFF(CURDATE(), DATE(`EnterDateTime`)) BETWEEN 8 AND 15) AS age_8_15,
            SUM(DATEDIFF(CURDATE(), DATE(`EnterDateTime`)) > 15) AS age_over_15,
            SUM(`SlaveType` = 'TYP_2') AS total_platform,
            SUM(`PriorityID` IN ('top','A(1)') AND `SlaveType` = 'TYP_2') AS top_a_platform,
            SUM(`PriorityID` IN ('B(2)','C(3)') AND `Occurance` = 'Always' AND `SlaveType` = 'TYP_2') AS bc_always_platform,
            SUM(`PriorityID` IN ('B(2)','C(3)') AND `Occurance` = 'Sometimes' AND `SlaveType` = 'TYP_2') AS bc_sometimes_platform,
            SUM(`PriorityID` IN ('B(2)','C(3)') AND `Occurance` = 'Once' AND `SlaveType` = 'TYP_2') AS bc_once_platform,
            SUM(`PlannedFixedDate` IS NOT NULL AND `PlannedFixedDate` != '0000-00-00'
                AND DATE(`PlannedFixedDate`) < CURDATE() AND `SlaveType` = 'TYP_2') AS crossed_platform,
            SUM((`PlannedFixedDate` IS NULL OR `PlannedFixedDate` = '0000-00-00') AND `SlaveType` = 'TYP_2') AS no_fpd_platform
        FROM tbl_ElvisSR
        WHERE {BASE_WHERE} AND {scope_where}{extra_clause} AND `TicketStepID` IN ('{open_steps_sql}')
        GROUP BY `FGroup` ORDER BY total DESC, `FGroup`
    """)
    domains = cur.fetchall()

    cur.execute(f"""
        SELECT `FGroup`,
            SUM(`PriorityID` IN ('top','A(1)')) AS top_a,
            SUM(`PriorityID` IN ('B(2)','C(3)') AND `Occurance` = 'Always') AS bc_always,
            SUM(`PriorityID` IN ('B(2)','C(3)') AND `Occurance` = 'Sometimes') AS bc_sometimes,
            SUM(`PriorityID` IN ('B(2)','C(3)') AND `Occurance` = 'Once') AS bc_once,
            COUNT(*) AS total
        FROM tbl_ElvisSR
                WHERE {BASE_WHERE} AND {scope_where}{extra_clause} AND `TicketStepID` IN ('{open_steps_sql}')
          AND (`PlannedFixedDate` IS NULL OR `PlannedFixedDate` = '0000-00-00')
        GROUP BY `FGroup`
        HAVING total > 0
        ORDER BY total DESC, `FGroup`
    """)
    no_fpd_domains = cur.fetchall()

    cur.execute(f"""
        SELECT `TicketID`, `Title`, `FGroup`, `SlaveType`, `PriorityID`,
               DATE(`PlannedFixedDate`) AS fpd,
               DATEDIFF(CURDATE(), DATE(`PlannedFixedDate`)) AS overdue
        FROM tbl_ElvisSR
                WHERE {BASE_WHERE} AND {scope_where}{extra_clause} AND `TicketStepID` IN ('{open_steps_sql}')
          AND `PlannedFixedDate` IS NOT NULL AND `PlannedFixedDate` != '0000-00-00'
          AND DATE(`PlannedFixedDate`) < CURDATE()
        ORDER BY `PlannedFixedDate`, `FGroup`, `TicketID`
    """)
    crossed = cur.fetchall()

    cur.execute(f"""
        SELECT `TicketID`, `Title`, `FGroup`, `SlaveType`, `PriorityID`, `TicketStepID`,
               `Occurance`,
                             CASE
                                     WHEN `ReferenceNumber` IS NULL OR TRIM(CAST(`ReferenceNumber` AS CHAR)) = '' THEN 0
                                     WHEN `ReferenceNumber` IN (0, 4, 5) THEN 0
                                     ELSE `ReferenceNumber`
                             END AS ext_ref,
               DATE(`PlannedFixedDate`) AS fpd
        FROM tbl_ElvisSR
                WHERE {BASE_WHERE} AND {scope_where}{extra_clause} AND `TicketStepID` IN ('{open_steps_sql}')
          AND `PriorityID` IN ('top', 'A(1)')
        ORDER BY FIELD(`PriorityID`, 'top', 'A(1)'), `FGroup`, `TicketID`
    """)
    top_a_tickets = cur.fetchall()

    today = date.today()
    last5 = [today - timedelta(days=i) for i in range(5)]
    earliest5 = last5[-1]

    cur.execute(f"""
        SELECT `FGroup`, DATE(`EnterDateTime`) AS d, COUNT(*) AS cnt
        FROM tbl_ElvisSR
        WHERE {BASE_WHERE} AND {scope_where}{extra_clause} AND DATE(`EnterDateTime`) >= %s
        GROUP BY `FGroup`, DATE(`EnterDateTime`)
    """, (earliest5,))
    domain_daily_in = {}
    for r in cur.fetchall():
        domain_daily_in.setdefault(r["FGroup"] or "Unknown", {})[str(r["d"])] = r["cnt"]

    domain_daily_out = {}
    cur.execute(f"""
        SELECT `FGroup`, DATE(`FirstIntegrDateTime`) AS d, COUNT(*) AS cnt
        FROM tbl_ElvisSR
                WHERE {BASE_WHERE} AND {scope_where}{extra_clause} AND `Rejected` = 'N'
          AND DATE(`FirstIntegrDateTime`) >= %s
        GROUP BY `FGroup`, DATE(`FirstIntegrDateTime`)
    """, (earliest5,))
    for r in cur.fetchall():
        domain_daily_out.setdefault(r["FGroup"] or "Unknown", {})[str(r["d"])] = r["cnt"]
    cur.execute(f"""
        SELECT `FGroup`, DATE(`FirstConclDateTime`) AS d, COUNT(*) AS cnt
        FROM tbl_ElvisSR
                WHERE {BASE_WHERE} AND {scope_where}{extra_clause} AND `Rejected` = 'Y'
          AND DATE(`FirstConclDateTime`) >= %s
        GROUP BY `FGroup`, DATE(`FirstConclDateTime`)
    """, (earliest5,))
    for r in cur.fetchall():
        key = str(r["d"])
        bucket = domain_daily_out.setdefault(r["FGroup"] or "Unknown", {})
        bucket[key] = bucket.get(key, 0) + r["cnt"]

    cur.execute(f"""
        SELECT `ReferenceNumber` AS ref, COUNT(*) AS cnt
        FROM tbl_ElvisSR
        WHERE {BASE_WHERE} AND {scope_where}{extra_clause} AND DATE(`EnterDateTime`) = CURDATE()
        GROUP BY `ReferenceNumber`
    """)
    today_in_by_ref = {int(r["ref"] if r["ref"] is not None else -1): int(r["cnt"] or 0) for r in cur.fetchall()}
    cur.execute(f"""
        SELECT COUNT(*) AS cnt
        FROM tbl_ElvisSR
                WHERE {BASE_WHERE} AND {scope_where}{extra_clause}
          AND ((`Rejected` = 'N' AND DATE(`FirstIntegrDateTime`) = CURDATE())
               OR (`Rejected` = 'Y' AND DATE(`FirstConclDateTime`) = CURDATE()))
    """)
    today_out = int(cur.fetchone()["cnt"] or 0)
    today_flow = {
        "in0": today_in_by_ref.get(0, 0), "in1": today_in_by_ref.get(1, 0), "in2": today_in_by_ref.get(2, 0),
        "total_in": sum(v for k, v in today_in_by_ref.items() if k in (0, 1, 2)), "out": today_out,
    }

    io_days = 21
    trend_days = 14
    io_dates = [today - timedelta(days=i) for i in range(io_days - 1, -1, -1)]
    flow_start = io_dates[0]

    trend_in_by_day = {str(d): {0: 0, 1: 0, 2: 0} for d in io_dates}
    cur.execute(f"""
        SELECT DATE(`EnterDateTime`) AS d, `ReferenceNumber` AS ref, COUNT(*) AS cnt
        FROM tbl_ElvisSR
                WHERE {BASE_WHERE} AND {scope_where}{extra_clause}
          AND DATE(`EnterDateTime`) >= %s
        GROUP BY DATE(`EnterDateTime`), `ReferenceNumber`
    """, (flow_start,))
    for r in cur.fetchall():
        dkey = str(r["d"])
        ref = int(r["ref"] if r["ref"] is not None else -1)
        if ref in (0, 1, 2):
            trend_in_by_day.setdefault(dkey, {0: 0, 1: 0, 2: 0})[ref] = int(r["cnt"] or 0)

    trend_out_by_day = {str(d): 0 for d in io_dates}
    cur.execute(f"""
        SELECT DATE(`FirstIntegrDateTime`) AS d, COUNT(*) AS cnt
        FROM tbl_ElvisSR
                WHERE {BASE_WHERE} AND {scope_where}{extra_clause} AND `Rejected` = 'N'
          AND DATE(`FirstIntegrDateTime`) >= %s
        GROUP BY DATE(`FirstIntegrDateTime`)
    """, (flow_start,))
    for r in cur.fetchall():
        trend_out_by_day[str(r["d"])] = int(r["cnt"] or 0)

    cur.execute(f"""
        SELECT DATE(`FirstConclDateTime`) AS d, COUNT(*) AS cnt
        FROM tbl_ElvisSR
                WHERE {BASE_WHERE} AND {scope_where}{extra_clause} AND `Rejected` = 'Y'
          AND DATE(`FirstConclDateTime`) >= %s
        GROUP BY DATE(`FirstConclDateTime`)
    """, (flow_start,))
    for r in cur.fetchall():
        dkey = str(r["d"])
        trend_out_by_day[dkey] = trend_out_by_day.get(dkey, 0) + int(r["cnt"] or 0)

    io_rows = []
    running_open = int(summary["open_total"] or 0)
    for d in reversed(io_dates):
        dkey = str(d)
        in0 = int(trend_in_by_day.get(dkey, {}).get(0, 0))
        in1 = int(trend_in_by_day.get(dkey, {}).get(1, 0))
        in2 = int(trend_in_by_day.get(dkey, {}).get(2, 0))
        in_total = in0 + in1 + in2
        out_total = int(trend_out_by_day.get(dkey, 0))
        io_rows.append({
            "date": d,
            "open": running_open,
            "in_total": in_total,
            "out_total": out_total,
            "net": in_total - out_total,
            "in0": in0,
            "in1": in1,
            "in2": in2,
        })
        running_open = running_open - in_total + out_total
    io_rows.reverse()

    trend_rows = io_rows[-trend_days:]

    weekday_rows = [row for row in trend_rows if row["date"].weekday() < 5]
    recent_7 = weekday_rows[-7:] if len(weekday_rows) >= 7 else weekday_rows
    recent_5 = weekday_rows[-5:] if len(weekday_rows) >= 5 else weekday_rows

    def avg(rows, key):
        return (sum(row[key] for row in rows) / len(rows)) if rows else 0.0

    avg_net_reduction_7 = avg(recent_7, "out_total") - avg(recent_7, "in_total")
    avg_out_7 = avg(recent_7, "out_total")
    avg_out_5 = avg(recent_5, "out_total")
    avg_in_7 = avg(recent_7, "in_total")
    projected_zero_days = math.ceil(int(summary["open_total"] or 0) / avg_net_reduction_7) if avg_net_reduction_7 > 0 else None
    projected_zero_date = today + timedelta(days=projected_zero_days) if projected_zero_days is not None else None
    burn_rate = {
        "avg_net_reduction_7": avg_net_reduction_7,
        "avg_out_7": avg_out_7,
        "avg_out_5": avg_out_5,
        "avg_in_7": avg_in_7,
        "projected_zero_days": projected_zero_days,
        "projected_zero_date": projected_zero_date,
        "io_rows": io_rows,
        "trend_rows": trend_rows,
    }

    return {
        "summary": summary, "priorities": priorities, "domains": domains, "crossed": crossed,
        "no_fpd_domains": no_fpd_domains, "top_a_tickets": top_a_tickets,
        "last5": last5, "domain_daily_in": domain_daily_in, "domain_daily_out": domain_daily_out,
        "today_flow": today_flow,
        "io_rows": io_rows,
        "trend_rows": trend_rows,
        "burn_rate": burn_rate,
    }


def rewrite_overview_nav(html):
    nav_html = f'''<!-- Nav -->
<tr><td style="background:#0b2e4d;padding:10px 28px;">
    <a href="overview.html" style="color:#fff;font-weight:700;text-decoration:none;margin-right:18px;border-bottom:2px solid #f39c12;padding-bottom:4px;">Overview</a>
    <a href="ytb.html" style="color:#d6eaf8;font-weight:600;text-decoration:none;margin-right:18px;">YTB</a>
    <a href="non-ytb.html" style="color:#d6eaf8;font-weight:600;text-decoration:none;margin-right:18px;">Non-YTB</a>
    <a href="current-release.html" style="color:#d6eaf8;font-weight:600;text-decoration:none;">{CURRENT_RELEASE_MILESTONE}</a>
</td></tr>'''
    return re.sub(r'<!-- Nav -->\s*<tr><td style="background:#0b2e4d;padding:10px 28px;">.*?</td></tr>', nav_html, html, count=1, flags=re.DOTALL)


def rewrite_detail_page_shell(html, page_key):
    page = DETAIL_PAGE_SHELL[page_key]
    nav_html = (
        '<tr><td style="background:#0b2e4d;padding:10px 28px;">'
        '<a href="overview.html" style="color:#d6eaf8;font-weight:600;text-decoration:none;margin-right:18px;">Overview</a>'
        f'<a href="ytb.html" style="color:{"#fff" if page_key == "ytb" else "#d6eaf8"};font-weight:{"700" if page_key == "ytb" else "600"};text-decoration:none;margin-right:18px;{"border-bottom:2px solid #f39c12;padding-bottom:4px;" if page_key == "ytb" else ""}">YTB</a>'
        f'<a href="non-ytb.html" style="color:{"#fff" if page_key == "non-ytb" else "#d6eaf8"};font-weight:{"700" if page_key == "non-ytb" else "600"};text-decoration:none;margin-right:18px;{"border-bottom:2px solid #f39c12;padding-bottom:4px;" if page_key == "non-ytb" else ""}">Non-YTB</a>'
        f'<a href="current-release.html" style="color:{"#fff" if page_key == "current-release" else "#d6eaf8"};font-weight:{"700" if page_key == "current-release" else "600"};text-decoration:none;{"border-bottom:2px solid #f39c12;padding-bottom:4px;" if page_key == "current-release" else ""}">{page["label"]}</a>'
        '</td></tr>'
    )
    html = re.sub(r'<tr><td style="background:#0b2e4d;padding:10px 28px;">.*?</td></tr>', nav_html, html, count=1, flags=re.DOTALL)
    html = re.sub(
        r'(<span style="font-size:22px;font-weight:bold;color:#fff;letter-spacing:0.5px;">).*?(</span>)',
        rf'\1{page["title"]}\2',
        html,
        count=1,
    )
    return html


ytb_head = headline(YTB_SCOPE)
nonytb_head = headline(NONYTB_SCOPE)
current_release_head = headline(CURRENT_RELEASE_SCOPE)
ytb_domains = domain_priority_split(YTB_SCOPE)
nonytb_domains = domain_priority_split(NONYTB_SCOPE)
current_release_domains = domain_priority_split(CURRENT_RELEASE_SCOPE)
details = {
    "ytb": detail_snapshot(YTB_SCOPE),
    "non-ytb": detail_snapshot(NONYTB_SCOPE),
    "current-release": detail_snapshot(CURRENT_RELEASE_SCOPE),
}

cur.close()
conn.close()

print("YTB:", ytb_head)
print("Non-YTB:", nonytb_head)
print("Current Release:", current_release_head)
print(f"YTB domains: {len(ytb_domains)}, Non-YTB domains: {len(nonytb_domains)}, Current Release open: {details['current-release']['summary']['open_total']}")


def gen_bars_html(domains, bar_width, pad, max_height=130):
    max_total = int(max((d["total"] for d in domains), default=1))
    cells = []
    for d in domains:
        name = d["FGroup"] or "Unknown"
        top_a, bc_always, bc_once_some, total = int(d["top_a"]), int(d["bc_always"]), int(d["bc_once_some"]), int(d["total"])
        scale = max_height / max_total if max_total else 0
        h_once = round(bc_once_some * scale)
        h_always = round(bc_always * scale)
        h_top_a = round(top_a * scale)
        if bc_once_some and h_once == 0: h_once = 1
        if bc_always and h_always == 0: h_always = 1
        if top_a and h_top_a == 0: h_top_a = 1
        segs = []
        if h_top_a:
            label = str(top_a) if h_top_a >= 9 else ""
            segs.append(f'<div style="width:{bar_width}px;height:{h_top_a}px;background:#c0392b;border-radius:3px 3px 0 0;color:#fff;font-size:8px;font-weight:700;text-align:center;line-height:{h_top_a}px;">{label}</div>')
        if h_always:
            label = str(bc_always) if h_always >= 9 else ""
            radius = "border-radius:3px 3px 0 0;" if not h_top_a else ""
            segs.append(f'<div style="width:{bar_width}px;height:{h_always}px;background:#f39c12;{radius}color:#7d4a00;font-size:8px;font-weight:700;text-align:center;line-height:{h_always}px;">{label}</div>')
        if h_once:
            label = str(bc_once_some) if h_once >= 9 else ""
            radius = "border-radius:3px 3px 0 0;" if not h_top_a and not h_always else ""
            segs.append(f'<div style="width:{bar_width}px;height:{h_once}px;background:#2471a3;{radius}color:#fff;font-size:8px;font-weight:700;text-align:center;line-height:{h_once}px;">{label}</div>')
        segs_html = "\n                        ".join(segs)
        cells.append(
            f'<td style="vertical-align:bottom;text-align:center;padding:0 {pad}px;">\n'
            f'                    <div style="font-size:10px;font-weight:700;color:#2c3e50;">{total}</div>\n'
            f'                    <div style="width:{bar_width}px;margin:2px auto 0;">\n'
            f'                        {segs_html}\n'
            f'                    </div>\n'
            f'                    <div style="font-size:8px;color:#666;margin-top:2px;white-space:nowrap;">{name}</div>\n'
            f'                </td>'
        )
    return "\n                ".join(cells)


ytb_bars_html = gen_bars_html(ytb_domains, bar_width=20 if len(ytb_domains) <= 10 else 14, pad=4 if len(ytb_domains) <= 10 else 2)
nonytb_bars_html = gen_bars_html(nonytb_domains, bar_width=20 if len(nonytb_domains) <= 10 else 14, pad=4 if len(nonytb_domains) <= 10 else 2)
current_release_bars_html = gen_bars_html(current_release_domains, bar_width=20 if len(current_release_domains) <= 10 else 14, pad=4 if len(current_release_domains) <= 10 else 2)


def replace_card(html, card_marker, open_val, crossed_val, nofpd_val, bars_html, legend_totals, platform_val):
    # Update the 3 headline numbers immediately following the marker's OPEN/CROSSED FPD/NO FPD cells
    section_start = html.index(card_marker)
    section_end = html.index("Scope: FG_SWRev", section_start)
    section = html[section_start:section_end]

    platform_badge = ""
    if platform_val:
        platform_badge = (f'<div style="font-size:9px;color:#7d3c98;font-weight:600;margin-top:2px;">'
                           f'<span style="display:inline-block;padding:1px 5px;border-radius:8px;background:#f5eef8;border:1px solid #d7bde2;">Platform: {platform_val}</span></div>')
    section = re.sub(
        r'OPEN</div><div style="font-size:26px;font-weight:700;color:#e67e22;">\d+</div>(?:<div style="font-size:9px;color:#7d3c98;.*?</div>)?',
        f'OPEN</div><div style="font-size:26px;font-weight:700;color:#e67e22;">{open_val}</div>{platform_badge}',
        section, count=1, flags=re.DOTALL)
    section = re.sub(
        r'(CROSSED FPD</div><div style="font-size:26px;font-weight:700;color:#c0392b;">)\d+(</div>)',
        rf'\g<1>{crossed_val}\g<2>', section, count=1)
    section = re.sub(
        r'(NO FPD</div><div style="font-size:26px;font-weight:700;color:#c0392b;">)\d+(</div>)',
        rf'\g<1>{nofpd_val}\g<2>', section, count=1)

    section = re.sub(r'TOP\+A(?:: \d+)? &nbsp;', f'TOP+A: {legend_totals["top_a"]} &nbsp;', section, count=1)
    section = re.sub(r'B\+C Always(?:: \d+)? &nbsp;', f'B+C Always: {legend_totals["bc_always"]} &nbsp;', section, count=1)
    section = re.sub(r'B\+C Once/Sometimes(?:: \d+)?</span>', f'B+C Once/Sometimes: {legend_totals["bc_once_some"]}</span>', section, count=1)

    # Replace the bars table body (between <tr> and </tr> inside the domain table)
    table_marker = 'style="margin-top:8px;border-bottom:2px solid #bdc3c7;height:150px;">'
    t_start = section.index(table_marker) + len(table_marker)
    row_start = section.index("<tr>", t_start) + len("<tr>")
    row_end = section.index("</tr>", row_start)
    section = section[:row_start] + "\n                " + bars_html + "\n            " + section[row_end:]

    return html[:section_start] + section + html[section_end:]


def legend_sums(domains):
    return {
        "top_a": sum(int(d["top_a"] or 0) for d in domains),
        "bc_always": sum(int(d["bc_always"] or 0) for d in domains),
        "bc_once_some": sum(int(d["bc_once_some"] or 0) for d in domains),
    }


def current_release_card(head, domains):
    legend = legend_sums(domains)
    bars_html = gen_bars_html(domains, bar_width=20 if len(domains) <= 10 else 14, pad=4 if len(domains) <= 10 else 2)
    open_total = n(head["open_total"])
    no_fpd = n(head["no_fpd"])
    fpd_total = max(open_total - no_fpd, 0)
    return f'''<!-- Current Milestone Card Start -->
<tr><td style="padding:0 24px 4px 24px;">
    <table width="100%" cellpadding="0" cellspacing="0">
    <tr>
        <td style="vertical-align:top;background:linear-gradient(135deg,#eef7fb 0%,#f8fbfd 100%);border:2px solid #7fb3d5;border-radius:14px;padding:16px;box-shadow:0 10px 22px rgba(26,82,118,0.08);">
            <details style="background:rgba(255,255,255,0.65);border:1px solid #d6eaf8;border-radius:12px;padding:0 12px;">
                <summary style="list-style:none;cursor:pointer;padding:12px 0;font-size:13px;font-weight:700;color:#2471a3;display:flex;align-items:center;justify-content:space-between;gap:12px;text-decoration:none;">
                    <span style="display:flex;flex-wrap:wrap;align-items:center;gap:8px;line-height:1.3;">
                        <span style="font-size:15px;color:#1f618d;">{CURRENT_RELEASE_LABEL}</span>
                        <span style="color:#7f8c8d;font-weight:600;">|</span>
                        <span>Open: {open_total}</span>
                        <span style="color:#7f8c8d;font-weight:600;">|</span>
                        <span>FPD: {fpd_total}</span>
                        <span style="color:#7f8c8d;font-weight:600;">|</span>
                        <span>No FPD: {no_fpd}</span>
                    </span>
                    <span style="display:inline-flex;align-items:center;justify-content:center;width:28px;height:28px;border-radius:999px;background:#ffffff;border:1px solid #d6eaf8;color:#2471a3;font-size:16px;font-weight:700;">+</span>
                </summary>
                <div style="padding:0 0 12px 0;">
                    <div style="margin-top:2px;font-size:10px;font-weight:700;color:#7f8c8d;letter-spacing:0.5px;">CURRENT RELEASE SNAPSHOT
                        <span style="font-weight:normal;margin-left:8px;"><span style="color:#7d3c98;">&#9632;</span> Platform: {n(head["platform_total"])} &nbsp; <span style="color:#c0392b;">&#9632;</span> Crossed FPD: {n(head["crossed_fpd"])} &nbsp; <span style="color:#2471a3;">&#9632;</span> No FPD: {no_fpd}</span>
                    </div>
                    <div style="margin-top:2px;font-size:11px;font-weight:700;color:#7f8c8d;letter-spacing:0.5px;">ALL DOMAINS (Current Release)
                        <span style="font-weight:normal;margin-left:8px;"><span style="color:#c0392b;">&#9632;</span> TOP+A: {legend["top_a"]} &nbsp; <span style="color:#f39c12;">&#9632;</span> B+C Always: {legend["bc_always"]} &nbsp; <span style="color:#2471a3;">&#9632;</span> B+C Once/Sometimes: {legend["bc_once_some"]}</span>
                    </div>
                    <table cellpadding="0" cellspacing="0" style="margin-top:8px;border-bottom:2px solid #bdc3c7;height:150px;">
                        <tr>{bars_html}</tr>
                    </table>
                    <div style="margin-top:12px;font-size:12px;color:#2471a3;">Scope: Milestone = {CURRENT_RELEASE_MILESTONE} | Target close: {CURRENT_RELEASE_TARGET_DATE.strftime("%d-%b")}</div>
                    <a href="current-release.html" style="display:inline-block;margin-top:12px;font-size:13px;font-weight:700;color:#fff;background:#2471a3;padding:8px 14px;border-radius:999px;text-decoration:none;box-shadow:0 6px 14px rgba(36,113,163,0.18);">View milestone detail &rarr;</a>
                </div>
            </details>
        </td>
    </tr>
    </table>
</td></tr>
<!-- Current Milestone Card End -->
'''


def overview_card_block(title, head, domains, scope_text, link_href, link_label, accent):
    legend = legend_sums(domains)
    bars_html = gen_bars_html(domains, bar_width=20 if len(domains) <= 10 else 14, pad=4 if len(domains) <= 10 else 2)
    return f'''<td width="50%" style="vertical-align:top;background:{accent['panel_bg']};border:2px solid {accent['border']};border-radius:14px;padding:16px;box-shadow:0 10px 20px rgba(15,23,42,0.06);">
        <div style="font-size:16px;font-weight:700;color:{accent['title']};margin-bottom:10px;">{title}</div>
        <table width="100%" cellpadding="0" cellspacing="6">
            <tr>
                <td style="text-align:center;background:#fff;border-radius:8px;padding:8px;"><div style="font-size:10px;color:#999;">OPEN</div><div style="font-size:26px;font-weight:700;color:#e67e22;">{n(head['open_total'])}</div><div style="font-size:9px;color:#7d3c98;font-weight:600;margin-top:2px;"><span style="display:inline-block;padding:1px 5px;border-radius:8px;background:#f5eef8;border:1px solid #d7bde2;">Platform: {n(head['platform_total'])}</span></div></td>
                <td style="text-align:center;background:#fff;border-radius:8px;padding:8px;"><div style="font-size:10px;color:#999;">CROSSED FPD</div><div style="font-size:26px;font-weight:700;color:#c0392b;">{n(head['crossed_fpd'])}</div></td>
                <td style="text-align:center;background:#fff;border-radius:8px;padding:8px;"><div style="font-size:10px;color:#999;">NO FPD</div><div style="font-size:26px;font-weight:700;color:#c0392b;">{n(head['no_fpd'])}</div></td>
            </tr>
        </table>
        <div style="margin-top:14px;font-size:11px;font-weight:700;color:#7f8c8d;letter-spacing:0.5px;">ALL DOMAINS (Overall Open)
            <span style="font-weight:normal;margin-left:8px;"><span style="color:#c0392b;">&#9632;</span> TOP+A: {legend['top_a']} &nbsp; <span style="color:#f39c12;">&#9632;</span> B+C Always: {legend['bc_always']} &nbsp; <span style="color:#2471a3;">&#9632;</span> B+C Once/Sometimes: {legend['bc_once_some']}</span>
        </div>
        <table cellpadding="0" cellspacing="0" style="margin-top:8px;border-bottom:2px solid #bdc3c7;height:150px;">
            <tr>{bars_html}</tr>
        </table>
        <div style="margin-top:12px;font-size:12px;color:{accent['scope']};">{scope_text}</div>
        <a href="{link_href}" style="display:inline-block;margin-top:12px;font-size:13px;font-weight:700;color:#fff;background:{accent['button_bg']};padding:8px 14px;border-radius:999px;text-decoration:none;box-shadow:0 6px 14px {accent['shadow']};">{link_label} &rarr;</a>
    </td>'''


def overview_summary_section():
    ytb_card = overview_card_block(
        "YTB &mdash; Open Tickets",
        ytb_head,
        ytb_domains,
        "Scope: FG_SWRev &ne; P8_YTB_NA",
        "ytb.html",
        "View YTB detail",
        {
            "panel_bg": "#eaf2f8",
            "border": "#2471a3",
            "title": "#1a5276",
            "soft_border": "#d6eaf8",
            "scope": "#2471a3",
            "button_bg": "#2471a3",
            "shadow": "rgba(36,113,163,0.18)",
        },
    )
    nonytb_card = overview_card_block(
        "Non-YTB &mdash; Open Tickets",
        nonytb_head,
        nonytb_domains,
        f"Scope: FG_SWRev = P8_YTB_NA | Target close: {NONYTB_TARGET_DATE.strftime('%d-%b')}",
        "non-ytb.html",
        "View Non-YTB detail",
        {
            "panel_bg": "#f4f4f4",
            "border": "#7f8c8d",
            "title": "#4a4a4a",
            "soft_border": "#d5d8dc",
            "scope": "#566573",
            "button_bg": "#566573",
            "shadow": "rgba(86,101,115,0.18)",
        },
    )
    milestone_card = overview_card_block(
        CURRENT_RELEASE_LABEL,
        current_release_head,
        current_release_domains,
        f"Scope: Milestone = {CURRENT_RELEASE_MILESTONE} | Target close: {CURRENT_RELEASE_TARGET_DATE.strftime('%d-%b')}",
        "current-release.html",
        "View milestone detail",
        {
            "panel_bg": "linear-gradient(135deg,#eef7fb 0%,#f8fbfd 100%)",
            "border": "#7fb3d5",
            "title": "#1f618d",
            "soft_border": "#d6eaf8",
            "scope": "#2471a3",
            "button_bg": "#2471a3",
            "shadow": "rgba(36,113,163,0.18)",
        },
    )
    return f'''<!-- Overview Summary Cards -->
<tr><td style="padding:20px 24px 12px 24px;">
    <table width="100%" cellpadding="0" cellspacing="16">
        <tr>
            {ytb_card}
            {nonytb_card}
        </tr>
    </table>
</td></tr>
{current_release_card(current_release_head, current_release_domains)}
'''


def n(value):
    return int(value or 0)


def cell(value, color="#34495e", bold=False, platform=None):
    weight = "font-weight:600;" if bold else ""
    badge = ""
    if platform:
        badge = (f'<div style="font-size:8px;line-height:1.05;color:#7d3c98;font-weight:600;margin-top:2px;">'
                  f'<span style="display:inline-block;padding:1px 4px;border-radius:8px;background:#f5eef8;border:1px solid #d7bde2;">Platform:{platform}</span></div>')
    return (f'<td style="padding:5px 7px;border-bottom:1px solid #eee;text-align:center;'
            f'color:{color};{weight}"><div>{n(value)}</div>{badge}</td>')


def daily_cell(value, is_in):
    v = n(value)
    if v == 0:
        return ('<td style="padding:3px 8px;border-bottom:1px solid #eee;text-align:center;color:#ccc;">'
                '<div style="font-size:12px;line-height:1.05;">&middot;</div></td>')
    color = "#c0392b" if is_in else "#1e8449"
    return (f'<td style="padding:3px 8px;border-bottom:1px solid #eee;text-align:center;color:{color};font-weight:600;">'
            f'<div style="font-size:12px;line-height:1.05;">{v}</div></td>')


def overall_domain_section(rows, domain_daily_in, domain_daily_out, last5):
    headings = ("Domain", "Total", "TOP+A", "B+C Always", "B+C Sometimes",
                "B+C Once", "Repro", "Crossed FPD", "No FPD", "Aged(0-7)",
                "Aged(8-15)", "Aged(>15)")
    header_cells = []
    for idx, h in enumerate(headings):
        border = "border-right:2px solid #2980b9;" if idx == len(headings) - 1 else "border-right:1px solid #2980b9;"
        header_cells.append(f'<td rowspan="2" style="padding:8px 8px;font-size:13px;color:#fff;font-weight:600;text-align:center;{border}">{h}</td>')
    header = "".join(header_cells)
    date_header = "".join(
        f'<td colspan="2" style="padding:4px 3px;font-size:11px;font-weight:600;color:#fff;text-align:center;'
        f'background:#1a5276;border-bottom:1px solid #2980b9;border-left:2px solid #2980b9;">{d.strftime("%d-%b")}</td>'
        for d in last5
    )
    inout_header = "<td style=\"padding:3px 4px;font-size:10px;font-weight:600;color:#fff;text-align:center;background:#c0392b;\">In</td><td style=\"padding:3px 4px;font-size:10px;font-weight:600;color:#fff;text-align:center;background:#1e8449;\">Out</td>" * len(last5)
    body = []
    keys = ("total", "top_a", "bc_always", "bc_sometimes", "bc_once", "repro",
            "crossed", "no_fpd", "age_0_7", "age_8_15", "age_over_15")
    platform_keys = {
        "total": "total_platform", "top_a": "top_a_platform", "bc_always": "bc_always_platform",
        "bc_sometimes": "bc_sometimes_platform", "bc_once": "bc_once_platform",
        "crossed": "crossed_platform", "no_fpd": "no_fpd_platform",
    }
    for i, row in enumerate(rows):
        bg = "#f8f9fa" if i % 2 == 0 else "#fff"
        name = row["FGroup"] or "Unknown"
        values = "".join(
            cell(row[k], "#c0392b" if k in ("crossed", "no_fpd") else "#34495e", k == "total",
                 platform=row.get(platform_keys[k]) if k in platform_keys else None)
            for k in keys
        )
        daily = "".join(
            daily_cell(domain_daily_in.get(name, {}).get(str(d), 0), True) +
            daily_cell(domain_daily_out.get(name, {}).get(str(d), 0), False)
            for d in last5
        )
        body.append(f'<tr style="background:{bg};"><td style="padding:5px 10px;border-bottom:1px solid #eee;white-space:nowrap;">{escape(name)}</td>{values}{daily}</tr>')
    totals = {key: sum(n(row[key]) for row in rows) for key in keys}
    totals_platform = {key: sum(n(row.get(pk)) for row in rows) for key, pk in platform_keys.items()}
    total_cells = "".join(
        cell(totals[k], "#c0392b" if k in ("crossed", "no_fpd") else "#1a5276", True,
             platform=totals_platform.get(k))
        for k in keys
    )
    total_daily = "".join(
        daily_cell(sum(domain_daily_in.get(row["FGroup"] or "Unknown", {}).get(str(d), 0) for row in rows), True) +
        daily_cell(sum(domain_daily_out.get(row["FGroup"] or "Unknown", {}).get(str(d), 0) for row in rows), False)
        for d in last5
    )
    body.append(f'<tr style="background:#eaf2f8;"><td style="padding:6px 10px;border-top:2px solid #1a5276;font-weight:700;">TOTAL</td>{total_cells}{total_daily}</tr>')
    return f'''<tr><td style="padding:0 28px 12px 28px;">
    <div style="font-size:16px;font-weight:600;color:#2c3e50;margin-bottom:8px;">Domain-wise Split (Overall Open) <span style="font-size:12px;font-weight:normal;color:#7f8c8d;">(Last 5 Days In/Out)</span></div>
    <div style="overflow-x:auto;"><table width="100%" cellpadding="0" cellspacing="0" style="border:2px solid #bdc3c7;border-radius:6px;border-collapse:collapse;font-size:12px;">
        <tr style="background:#1a5276;">{header}{date_header}</tr>
        <tr style="background:#1a5276;">{inout_header}</tr>
        {''.join(body)}
    </table></div>
</td></tr>

'''


def no_fpd_section(rows):
    total = sum(n(row["total"]) for row in rows)
    colors = ("#e74c3c", "#d35400", "#af601a", "#a04000")
    keys = ("top_a", "bc_always", "bc_sometimes", "bc_once")
    body = []
    for i, row in enumerate(rows):
        bg = "#fff8e1" if i % 2 == 0 else "#fff"
        metric_cells = "".join(
            f'<td style="padding:4px 10px;font-size:13px;border-bottom:1px solid #f0f0f0;text-align:center;color:{c};">{n(row[k])}</td>'
            for k, c in zip(keys, colors)
        )
        body.append(
            f'<tr style="background:{bg};"><td style="padding:4px 10px;font-size:13px;border-bottom:1px solid #f0f0f0;white-space:nowrap;">{escape(row["FGroup"] or "Unknown")}</td>'
            f'<td style="padding:4px 10px;font-size:13px;border-bottom:1px solid #f0f0f0;text-align:center;font-weight:600;color:#e67e22;">{n(row["total"])}</td>'
            f'{metric_cells}</tr>'
        )
    return f'''<!-- FPD Not Available (All Milestones) -->
<tr><td style="padding:0 28px 18px 28px;">
    <div style="font-size:16px;font-weight:600;color:#e67e22;margin-bottom:8px;">&#9888; Domain-wise Split (FPD Not Available): {total} <span style="font-size:12px;font-weight:normal;color:#7f8c8d;">(TOP+A, B+C Always, B+C Sometimes, B+C Once)</span></div>
    <table width="100%" cellpadding="0" cellspacing="0" style="border:2px solid #f9e79f;border-radius:6px;border-collapse:collapse;">
        <tr style="background:#d4ac0d;">
            <td style="padding:7px 12px;font-size:13px;font-weight:600;color:#fff;border-right:1px solid #f1c40f;">Domain</td><td style="padding:7px 12px;font-size:13px;font-weight:600;color:#fff;border-right:1px solid #f1c40f;text-align:center;">Total</td><td style="padding:7px 12px;font-size:13px;font-weight:600;color:#fff;text-align:center;border-right:1px solid #f1c40f;">TOP+A</td><td style="padding:7px 12px;font-size:13px;font-weight:600;color:#fff;text-align:center;border-right:1px solid #f1c40f;">B+C Always</td><td style="padding:7px 12px;font-size:13px;font-weight:600;color:#fff;text-align:center;border-right:1px solid #f1c40f;">B+C Sometimes</td><td style="padding:7px 12px;font-size:13px;font-weight:600;color:#fff;text-align:center;border-right:1px solid #f1c40f;">B+C Once</td>
        </tr>
        {''.join(body)}
    </table>
</td></tr>

'''


def top_a_section(rows):
    body = []
    for i, row in enumerate(rows):
        bg = "#f4ecf7" if i % 2 == 0 else "#fff"
        ticket_type = "Platform" if row["SlaveType"] == "TYP_2" else "Project"
        fpd = row["fpd"].strftime("%d-%b") if row["fpd"] else "N/A"
        title = escape((row["Title"] or "")[:100])
        body.append(
            f'<tr style="background:{bg};"><td style="padding:4px 8px;border-bottom:1px solid #eee;">{row["TicketID"]}</td>'
            f'<td style="padding:4px 8px;border-bottom:1px solid #eee;text-align:center;color:#7d3c98;font-weight:600;">{n(row.get("ext_ref"))}</td>'
            f'<td style="padding:4px 8px;border-bottom:1px solid #eee;">{escape(row["FGroup"] or "Unknown")}</td>'
            f'<td style="padding:4px 8px;border-bottom:1px solid #eee;">{ticket_type}</td>'
            f'<td style="padding:4px 8px;border-bottom:1px solid #eee;">{escape(row["PriorityID"] or "")}</td>'
            f'<td style="padding:4px 8px;border-bottom:1px solid #eee;">{escape(row.get("Occurance") or "")}</td>'
            f'<td style="padding:4px 8px;border-bottom:1px solid #eee;">{escape(row["TicketStepID"] or "")}</td>'
            f'<td style="padding:4px 8px;border-bottom:1px solid #eee;">{title}</td>'
            f'<td style="padding:4px 8px;border-bottom:1px solid #eee;white-space:nowrap;">{fpd}</td></tr>'
        )
    if not body:
        body.append('<tr><td colspan="9" style="padding:12px;text-align:center;color:#999;">No TOP+A tickets</td></tr>')
    return f'''<!-- Top A Tickets (TOP + A(1) priority, All Milestones) -->
<tr><td style="padding:0 28px 18px 28px;">
    <div style="font-size:16px;font-weight:600;color:#6c3483;margin-bottom:8px;">&#11088; Top A Tickets: {len(rows)} <span style="font-size:12px;font-weight:normal;color:#7f8c8d;">(TOP and A(1) priority open tickets)</span></div>
    <div style="overflow-x:auto;"><table width="100%" cellpadding="0" cellspacing="0" style="border:2px solid #d2b4de;border-radius:6px;border-collapse:collapse;font-size:12px;">
        <tr style="background:#6c3483;"><td style="padding:7px;color:#fff;font-weight:600;">Ticket ID</td><td style="padding:7px;color:#fff;font-weight:600;">Ext Ref</td><td style="padding:7px;color:#fff;font-weight:600;">Domain</td><td style="padding:7px;color:#fff;font-weight:600;">Type</td><td style="padding:7px;color:#fff;font-weight:600;">Priority</td><td style="padding:7px;color:#fff;font-weight:600;">Occurance</td><td style="padding:7px;color:#fff;font-weight:600;">Step</td><td style="padding:7px;color:#fff;font-weight:600;">Title</td><td style="padding:7px;color:#fff;font-weight:600;">FPD</td></tr>{''.join(body)}
    </table></div>
</td></tr>

'''


def burn_rate_section(summary, burn_rate, priority_html, target_date=None):
    projected_zero_date = burn_rate["projected_zero_date"]
    projected_text = projected_zero_date.strftime("%d-%b") if projected_zero_date else "N/A"
    status_color = "#1e8449" if projected_zero_date else "#e74c3c"
    status_text = (
        f'&#9989; Projected zero by {projected_text}' if projected_zero_date
        else '&#9888; Backlog is not shrinking with the latest 7 weekdays'
    )
    fix_rate_needed = math.ceil(burn_rate["avg_net_reduction_7"]) if burn_rate["avg_net_reduction_7"] > 0 else n(summary["open_total"])
    target_html = ""
    if target_date:
        days_left = max((target_date - date.today()).days, 0)
        required_rate = math.ceil(n(summary["open_total"]) / max(days_left, 1)) if n(summary["open_total"]) else 0
        on_track = projected_zero_date is not None and projected_zero_date <= target_date
        fix_rate_needed = required_rate
        target_html = (
            f'<div style="font-size:12px;color:{"#1e8449" if on_track else "#c0392b"};margin-top:6px;">'
            f'Target close: {target_date.strftime("%d-%b-%Y")} | Required net reduction: {required_rate}/day | '
            f'{"On track" if on_track else "At risk"}'
            f'</div>'
        )
    return f'''<!-- Burn Rate + Priority Breakdown -->
<tr><td style="padding:0 28px 18px 28px;">
<table width="100%" cellpadding="0" cellspacing="0">
<tr>
    <td style="background:#f8f9fa;border:1px solid #ddd;border-radius:8px;padding:14px 20px;">
        <div style="font-size:12px;color:#7f8c8d;font-weight:bold;letter-spacing:1px;margin-bottom:6px;">BURN RATE PROJECTION</div>
        <div style="font-size:15px;color:{status_color};font-weight:600;">{status_text}</div>
        <div style="font-size:12px;color:#999;margin-top:4px;">Avg net reduction (7 weekdays): {burn_rate["avg_net_reduction_7"]:.1f}/day | Avg outflow (7d): {burn_rate["avg_out_7"]:.1f}/day | Avg outflow (5d): {burn_rate["avg_out_5"]:.1f}/day | Avg inflow: {burn_rate["avg_in_7"]:.1f}/day | Burn rate needed: {fix_rate_needed}/day</div>
        {target_html}
    </td>
</tr>
<tr><td style="padding-top:10px;">
    <div style="font-size:12px;color:#7f8c8d;font-weight:bold;letter-spacing:1px;margin-bottom:4px;">OPEN BY PRIORITY</div>
    <div>{priority_html}</div>
</td></tr>
</table>
</td></tr>

'''


def build_inflow_outflow_bars(burn_rate):
    rows = burn_rate["io_rows"]
    if not rows:
        return ""
    max_flow = max(max(row["in_total"], row["out_total"]) for row in rows) or 1
    columns = []
    for row in rows:
        in_height = max(4, round((row["in_total"] / max_flow) * 84)) if row["in_total"] else 4
        out_height = max(4, round((row["out_total"] / max_flow) * 84)) if row["out_total"] else 4
        columns.append(
            f'<td style="vertical-align:bottom;text-align:center;padding:0 3px;min-width:42px;">'
            f'<div style="font-size:9px;color:#566573;font-weight:600;margin-bottom:4px;white-space:nowrap;">{row["date"].strftime("%d-%b")}</div>'
            f'<div style="display:flex;justify-content:center;gap:4px;margin-bottom:5px;">'
            f'<span style="font-size:9px;font-weight:700;color:#9b2c2c;">{row["in_total"]}</span>'
            f'<span style="font-size:9px;font-weight:700;color:#1e8449;">{row["out_total"]}</span>'
            f'</div>'
            f'<div style="display:flex;justify-content:center;align-items:flex-end;gap:2px;height:90px;">'
            f'<div title="In {row["in_total"]}" style="width:11px;height:{in_height}px;background:#f7c8c8;border:1px solid #e6a3a3;border-bottom:none;border-radius:3px 3px 0 0;"></div>'
            f'<div title="Out {row["out_total"]}" style="width:11px;height:{out_height}px;background:#d5f0de;border:1px solid #a8d8b6;border-bottom:none;border-radius:3px 3px 0 0;"></div>'
            f'</div>'
            f'<div style="font-size:8px;color:#999;margin-top:3px;">I / O</div>'
            f'</td>'
        )
    return f'''<!-- Inflow / Outflow Bars -->
<tr><td style="padding:0 28px 12px 28px;">
    <div style="font-size:16px;font-weight:bold;color:#2c3e50;margin-bottom:8px;">Inflow / Outflow Bars <span style="font-size:12px;font-weight:normal;color:#7f8c8d;">(Last 3 Weeks)</span></div>
    <div style="overflow-x:auto;"><table cellpadding="0" cellspacing="0" style="border:1px solid #e5eaf0;border-radius:10px;padding:10px 8px;width:100%;background:#fcfdff;box-shadow:inset 0 0 0 1px #f3f6f9;">
        <tr>{''.join(columns)}</tr>
    </table></div>
</td></tr>

'''


def build_recent_trend_block(summary, burn_rate, target_date=None):
    rows_asc = burn_rate["trend_rows"]
    rows_desc = list(reversed(rows_asc))
    values = [row["open"] for row in rows_asc] or [n(summary["open_total"])]
    max_value = max(values) if values else 1
    min_value = min(values) if values else 0
    width = 760
    chart_height = 130
    left_x = 40
    bottom_y = 160
    points = []
    point_marks = []
    for idx, row in enumerate(rows_asc):
        x = left_x + (width * idx / max(len(rows_asc) - 1, 1))
        y = bottom_y - ((row["open"] - min_value) / max(max_value - min_value, 1)) * chart_height
        points.append(f"{x:.1f},{y:.1f}")
        point_marks.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.6" fill="#f5b041" stroke="#fff" stroke-width="1.2"/>')
        point_marks.append(f'<text x="{x:.1f}" y="{y - 8:.1f}" text-anchor="middle" font-size="9" font-weight="700" fill="#7d6608" font-family="Segoe UI,Calibri,Arial,sans-serif">{row["open"]}</text>')
    if not points:
        points = [f"{left_x:.1f},{bottom_y:.1f}"]
    poly_points = " ".join(points)
    projected_label = burn_rate["projected_zero_date"].strftime("%d-%b") if burn_rate["projected_zero_date"] else "N/A"
    target_note = ""
    if target_date:
        target_note = f' | Target close: {target_date.strftime("%d-%b")}'
    rows_html = []
    for row in rows_desc:
        bg = "#f0fdf4" if len(rows_html) % 2 == 0 else "#fff"
        rows_html.append(
            f'<tr style="background:{bg};"><td style="padding:7px 14px;border-bottom:1px solid #eee;font-size:14px;font-family:\'Segoe UI\',Calibri,Arial,sans-serif;">{row["date"].strftime("%d-%b (%a)")}</td>'
            f'<td style="padding:7px 14px;border-bottom:1px solid #eee;text-align:center;font-size:15px;font-weight:600;color:#e67e22;font-family:\'Segoe UI\',Calibri,Arial,sans-serif;">{row["open"]}</td>'
            f'<td style="padding:7px 14px;border-bottom:1px solid #eee;text-align:center;font-size:15px;font-weight:600;color:#c0392b;font-family:\'Segoe UI\',Calibri,Arial,sans-serif;">{row["in_total"]}</td>'
            f'<td style="padding:7px 14px;border-bottom:1px solid #eee;text-align:center;font-size:15px;font-weight:600;color:#1e8449;font-family:\'Segoe UI\',Calibri,Arial,sans-serif;">{row["out_total"]}</td>'
            f'<td style="padding:7px 14px;border-bottom:1px solid #eee;text-align:center;font-size:15px;font-family:\'Segoe UI\',Calibri,Arial,sans-serif;">{row["net"]}</td>'
            f'<td style="padding:7px 14px;border-bottom:1px solid #eee;text-align:center;font-size:15px;color:#943126;font-family:\'Segoe UI\',Calibri,Arial,sans-serif;">{row["in0"]}</td>'
            f'<td style="padding:7px 14px;border-bottom:1px solid #eee;text-align:center;font-size:15px;color:#1f618d;font-family:\'Segoe UI\',Calibri,Arial,sans-serif;">{row["in1"]}</td>'
            f'<td style="padding:7px 14px;border-bottom:1px solid #eee;text-align:center;font-size:15px;color:#7d6608;font-family:\'Segoe UI\',Calibri,Arial,sans-serif;">{row["in2"]}</td></tr>'
        )
    inflow_outflow_bars = build_inflow_outflow_bars(burn_rate)
    return f'''{inflow_outflow_bars}<!-- Open Curve Chart -->
<tr><td style="padding:0 28px 18px 28px;">
    <div style="font-size:16px;font-weight:bold;color:#2c3e50;margin-bottom:10px;">Open Trend &rarr; Zero <span style="font-size:12px;font-weight:normal;color:#27ae60;">(Projected zero: {projected_label}{target_note})</span></div>
    <svg width="820" height="200" style="display:block;">
        <rect x="40" y="30" width="760" height="130" fill="#fef9e7" rx="4"/>
        <line x1="40" y1="160" x2="800" y2="160" stroke="#27ae60" stroke-width="1" stroke-dasharray="4,3"/>
        <polyline points="{poly_points}" fill="none" stroke="#e67e22" stroke-width="2.5" stroke-linejoin="round" stroke-linecap="round"/>
        {''.join(point_marks)}
        <text x="35" y="34" text-anchor="end" font-size="10" fill="#999" font-family="Segoe UI,Calibri,Arial,sans-serif">{max_value}</text><text x="35" y="164" text-anchor="end" font-size="10" fill="#999" font-family="Segoe UI,Calibri,Arial,sans-serif">{min_value}</text>
    </svg>
    <div style="margin-top:12px;font-size:12px;color:#666;font-family:'Segoe UI',Calibri,Arial,sans-serif;">Latest trend is rebuilt from the live 14-day window ending today.</div>
    <div style="margin-top:18px;font-size:16px;font-weight:bold;color:#2c3e50;margin-bottom:10px;">Closing Trend (Last 14 Days)</div>
    <div style="overflow-x:auto;"><table width="100%" cellpadding="0" cellspacing="0" style="border:1px solid #ddd;border-radius:6px;">
        <tr style="background:#34495e;">
            <td style="padding:6px 12px;font-size:13px;font-weight:bold;color:#fff;">Date</td>
            <td style="padding:6px 12px;font-size:13px;font-weight:bold;color:#fdebd0;text-align:center;">Open</td>
            <td style="padding:6px 12px;font-size:13px;font-weight:bold;color:#f5b7b1;text-align:center;">Total In</td>
            <td style="padding:6px 12px;font-size:13px;font-weight:bold;color:#abebc6;text-align:center;">Out</td>
            <td style="padding:6px 12px;font-size:13px;font-weight:bold;color:#fff;text-align:center;">Net</td>
            <td style="padding:6px 12px;font-size:13px;font-weight:bold;color:#f5b7b1;text-align:center;">In 0 (Harman)</td>
            <td style="padding:6px 12px;font-size:13px;font-weight:bold;color:#d6eaf8;text-align:center;">In 1 (MSIL)</td>
            <td style="padding:6px 12px;font-size:13px;font-weight:bold;color:#fcf3cf;text-align:center;">In 2 (QG)</td>
        </tr>{''.join(rows_html)}
    </table></div>
</td></tr>

'''


def crossed_section(rows):
    body = []
    for i, row in enumerate(rows):
        bg = "#fef2f2" if i % 2 == 0 else "#fff"
        ticket_type = "Platform" if row["SlaveType"] == "TYP_2" else "Project"
        fpd = row["fpd"].strftime("%d-%b") if row["fpd"] else "N/A"
        title = escape((row["Title"] or "")[:100])
        body.append(
            f'<tr style="background:{bg};"><td style="padding:4px 8px;border-bottom:1px solid #eee;">{row["TicketID"]}</td>'
            f'<td style="padding:4px 8px;border-bottom:1px solid #eee;"></td>'
            f'<td style="padding:4px 8px;border-bottom:1px solid #eee;">{escape(row["FGroup"] or "Unknown")}</td>'
            f'<td style="padding:4px 8px;border-bottom:1px solid #eee;">{ticket_type}</td>'
            f'<td style="padding:4px 8px;border-bottom:1px solid #eee;">{escape(row["PriorityID"] or "")}</td>'
            f'<td style="padding:4px 8px;border-bottom:1px solid #eee;">{title}</td>'
            f'<td style="padding:4px 8px;border-bottom:1px solid #eee;white-space:nowrap;">{fpd}</td>'
            f'<td style="padding:4px 8px;border-bottom:1px solid #eee;text-align:center;color:#c0392b;font-weight:600;">{n(row["overdue"])}d</td></tr>'
        )
    if not body:
        body.append('<tr><td colspan="8" style="padding:12px;text-align:center;color:#999;">No crossed-FPD tickets</td></tr>')
    return f'''<!-- Crossed FPD (Overdue, All Milestones) — Pre-Integrating only -->
<tr><td style="padding:0 28px 18px 28px;">
    <div style="font-size:16px;font-weight:600;color:#c0392b;margin-bottom:8px;">&#9888; Crossed FPD (Overdue): {len(rows)} <span style="font-size:12px;font-weight:normal;color:#7f8c8d;">(Pre-Integrating tickets past their planned fix date)</span></div>
    <div style="overflow-x:auto;"><table width="100%" cellpadding="0" cellspacing="0" style="border:2px solid #f5b7b1;border-radius:6px;border-collapse:collapse;font-size:12px;">
        <tr style="background:#c0392b;"><td style="padding:7px;color:#fff;font-weight:600;">Ticket ID</td><td style="padding:7px;color:#fff;font-weight:600;">IC Platform</td><td style="padding:7px;color:#fff;font-weight:600;">Domain</td><td style="padding:7px;color:#fff;font-weight:600;">Type</td><td style="padding:7px;color:#fff;font-weight:600;">Priority</td><td style="padding:7px;color:#fff;font-weight:600;">Title</td><td style="padding:7px;color:#fff;font-weight:600;">FPD</td><td style="padding:7px;color:#fff;font-weight:600;">Overdue</td></tr>{''.join(body)}
    </table></div>
</td></tr>

'''


def replace_number_card(html, label, value):
    pattern = rf'({re.escape(label)}</div>\s*<div[^>]*>)\d+(</div>)'
    return re.sub(pattern, rf'\g<1>{n(value)}\g<2>', html, count=1, flags=re.IGNORECASE)


def insert_open_platform_badge(html, platform_val):
    badge = ""
    if platform_val:
        badge = (f'<div style="font-size:9px;color:#7d3c98;font-weight:600;margin-top:2px;">'
                  f'<span style="display:inline-block;padding:1px 5px;border-radius:8px;background:#f5eef8;border:1px solid #d7bde2;">Platform: {platform_val}</span></div>')
    pattern = re.compile(r'(>Open</div>\s*<div style="font-size:30px;[^"]*">\d+</div>)(<div style="font-size:9px;color:#7d3c98;.*?</div>)?', re.DOTALL)
    return pattern.sub(lambda m: m.group(1) + badge, html, count=1)


def stamp_timestamp(html):
    now = datetime.now().astimezone()
    iso, display = now.isoformat(timespec="seconds"), now.strftime("%d-%b-%Y %H:%M")
    updated_span = f'<span id="last-updated" data-timestamp="{iso}" style="font-size:10px;font-weight:normal;color:rgba(255,255,255,0.5);">Last updated: {display}</span>'
    if 'id="last-updated"' in html:
        html = re.sub(r'<span id="last-updated".*?</span>', updated_span, html, count=1)
    else:
        match = re.search(r'(<tr><td style="background:#1a5276;padding:18px 28px;">)\s*(<span.*?</span>)\s*(</td></tr>)', html, re.DOTALL)
        if match:
            replacement = match.group(1) + f'<table width="100%"><tr><td>{match.group(2)}</td><td style="text-align:right;">{updated_span}</td></tr></table>' + match.group(3)
            html = html[:match.start()] + replacement + html[match.end():]
    # Show the fixed date/time only; strip any old relative-time ("X min/hr ago") script.
    html = re.sub(r"<script>\s*\(function[^(]*\(\)\s*\{\s*var el = document\.getElementById\(.last-updated.\).*?</script>\s*", "", html, count=1, flags=re.DOTALL)
    return html, now


def refresh_today_closing_row(html, flow):
    """Recompute today's row in the 'Closing Trend' table (Total In / Out / Net / In 0-2)
    from the live today_flow snapshot, since these were previously left stale."""
    header_idx = html.find("Closing Trend")
    if header_idx < 0:
        return html
    row_start = html.find("<tr", html.find("</tr>", header_idx) + 5)
    row_end = html.find("</tr>", row_start) + len("</tr>")
    if row_start < 0 or row_end <= row_start:
        return html
    row = html[row_start:row_end]
    cells = re.findall(r'<td\b.*?</td>', row, flags=re.DOTALL)
    if len(cells) != 8:
        return html
    net = flow["total_in"] - flow["out"]
    net_color = "#27ae60" if net >= 0 else "#e74c3c"

    def rebuild(cell, value):
        prefix = re.match(r'<td[^>]*>', cell).group(0)
        return f'{prefix}{value}</td>'

    cells[2] = rebuild(cells[2], flow["total_in"])
    cells[3] = rebuild(cells[3], flow["out"])
    cells[4] = rebuild(cells[4], f'<span style="color:{net_color};font-weight:600;">{net}</span>')
    cells[5] = rebuild(cells[5], flow["in0"])
    cells[6] = rebuild(cells[6], flow["in1"])
    cells[7] = rebuild(cells[7], flow["in2"])
    row_tag_match = re.match(r'<tr[^>]*>', row)
    new_row = row_tag_match.group(0) + "".join(cells) + "</tr>"
    return html[:row_start] + new_row + html[row_end:]


def update_detail_page(html, data, head, deadline):
    summary = data["summary"]
    for label, value in (("Open", summary["open_total"]), ("Integrating", summary["integrating"]),
                         ("Verification", summary["verifying"]), ("Crossed FPD", head["crossed_fpd"]),
                         ("No FPD", head["no_fpd"])):
        html = replace_number_card(html, label, value)
    html = insert_open_platform_badge(html, head.get("platform_total"))
    burn_rate = data["burn_rate"]
    if deadline:
        days_to_target = max((deadline - date.today()).days, 1)
        fix_rate = math.ceil(n(summary["open_total"]) / days_to_target) if n(summary["open_total"]) else 0
    else:
        fix_rate = math.ceil(burn_rate["avg_net_reduction_7"]) if burn_rate["avg_net_reduction_7"] > 0 else n(summary["open_total"])
    html = replace_number_card(html, "Expected Fix Rate", fix_rate)
    projected_date = burn_rate["projected_zero_date"].strftime("%d-%b") if burn_rate["projected_zero_date"] else "N/A"
    rate_note = f'(target close: {deadline.strftime("%d-%b")}; projected zero: {projected_date})' if deadline else f'(latest 7 weekdays; projected zero: {projected_date})'
    html = re.sub(r'(Expected Fix Rate</div>\s*<div[^>]*>\d+</div>\s*<div style="font-size:9px;color:#999;">).*?(</div>)', rf'\1{rate_note}\2', html, count=1, flags=re.DOTALL)
    html = re.sub(r'Fix rate needed: \d+/day', f'Fix rate needed: {fix_rate}/day', html, count=1)
    priority_html = "".join(f'<span style="display:inline-block;margin-right:12px;font-size:14px;"><strong style="color:#1a5276;">{escape(row["PriorityID"] or "Unknown")}</strong>: <span style="font-weight:600;color:#d35400;">{n(row["cnt"])}</span></span>' for row in data["priorities"])
    burn_start = html.index('<!-- Burn Rate + Priority Breakdown -->')
    overall_anchor = html.index('<tr><td style="padding:0 28px 12px 28px;">', burn_start)
    html = html[:burn_start] + burn_rate_section(summary, burn_rate, priority_html, deadline) + html[overall_anchor:]
    html = re.sub(r'(<div[^>]*>OPEN BY PRIORITY</div>\s*)<div>.*?</div>', rf'\1<div>{priority_html}</div>', html, count=1, flags=re.DOTALL)
    overall_start = html.index('<tr><td style="padding:0 28px 12px 28px;">')
    fpd_start = html.index('<!-- FPD Not Available', overall_start)
    html = html[:overall_start] + overall_domain_section(data["domains"], data["domain_daily_in"], data["domain_daily_out"], data["last5"]) + html[fpd_start:]
    fpd_start = html.index('<!-- FPD Not Available')
    crossed_start = html.index('<!-- Crossed FPD', fpd_start)
    html = html[:fpd_start] + top_a_section(data["top_a_tickets"]) + no_fpd_section(data["domains"]) + html[crossed_start:]
    top_start = html.index('<!-- Top A Tickets')
    fpd_start = html.index('<!-- FPD Not Available')
    if fpd_start < top_start:
        top_end = html.index('<!-- Crossed FPD', top_start)
        top_block = html[top_start:top_end]
        fpd_block = html[fpd_start:top_start]
        html = html[:fpd_start] + top_block + fpd_block + html[top_end:]
    crossed_start = html.index('<!-- Crossed FPD')
    next_start = html.index('<!-- Platform Rejected', crossed_start)
    html = html[:crossed_start] + crossed_section(data["crossed"]) + html[next_start:]
    chart_start = html.find('<!-- Inflow / Outflow Bars -->')
    if chart_start < 0:
        chart_start = html.find('<!-- Open Curve Chart -->')
    footer_start = html.find('<!-- Footer -->', chart_start)
    if chart_start >= 0 and footer_start > chart_start:
        html = html[:chart_start] + build_recent_trend_block(summary, burn_rate, deadline) + html[footer_start:]
    html, now = stamp_timestamp(html)
    stamp = now.strftime("%Y%m%d_%H%M%S")
    html = re.sub(r'Updated on : \d+_\d+', f'Updated on : {stamp}', html, count=1)
    return html


for path in TARGET_FILES:
    with open(path, "r", encoding="utf-8") as f:
        html = f.read()

    html = rewrite_overview_nav(html)
    cards_start = html.find('<!-- Two summary cards -->')
    if cards_start < 0:
        cards_start = html.find('<!-- Overview Cards Carousel -->')
    if cards_start < 0:
        cards_start = html.find('<!-- Overview Summary Cards -->')
    footer_idx = html.index('<!-- Footer -->')
    html = html[:cards_start] + overview_summary_section() + html[footer_idx:]
    html, _ = stamp_timestamp(html)

    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Updated {path}")

deadlines = {"ytb": None, "non-ytb": NONYTB_TARGET_DATE, "current-release": CURRENT_RELEASE_TARGET_DATE}
heads = {"ytb": ytb_head, "non-ytb": nonytb_head, "current-release": current_release_head}
for name, path in DETAIL_FILES.items():
    template_path = path if os.path.exists(path) else DETAIL_FILES["ytb"]
    if template_path != path and not os.path.exists(path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(template_path, "r", encoding="utf-8") as f:
        html = f.read()
    html = rewrite_detail_page_shell(html, name)
    html = update_detail_page(html, details[name], heads[name], deadlines[name])
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Updated {path}")

for name, data in details.items():
    domain_total = sum(n(row["total"]) for row in data["domains"])
    no_fpd_total = sum(n(row["no_fpd"]) for row in data["domains"])
    crossed_total = sum(n(row["crossed"]) for row in data["domains"])
    priority_total = sum(n(row["cnt"]) for row in data["priorities"])
    expected = n(data["summary"]["open_total"])
    assert domain_total == expected, f"{name}: domain total {domain_total} != open {expected}"
    assert priority_total == expected, f"{name}: priority total {priority_total} != open {expected}"
    assert no_fpd_total == n(heads[name]["no_fpd"]), f"{name}: no-FPD totals do not reconcile"
    assert crossed_total == n(heads[name]["crossed_fpd"]), f"{name}: crossed-FPD totals do not reconcile"
    assert len(data["crossed"]) == n(heads[name]["crossed_fpd"]), f"{name}: crossed-FPD rows do not reconcile"
    print(f"Validated {name}: open={expected}, no_fpd={no_fpd_total}, crossed={crossed_total}")
