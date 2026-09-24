"""Regenerate all published dashboard pages from one LIVE Elvis DB snapshot.

The same scope is used for the Overview cards and both detail pages so their
headline, domain, FPD, and priority totals always reconcile.

Usage: python scripts/update_overview_live.py
"""
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
}

BASE_WHERE = """
    `ProjectID` = 'MSIL_DA2.8'
    AND `IsDeleted` = 'N'
    AND `ReferenceNumber` <= 2
"""
OPEN_STEPS = ("Categorizing", "Reproduction", "Processing")
YTB_SCOPE = "`FG_SWRev` != 'P8_YTB_NA'"
NONYTB_SCOPE = "`FG_SWRev` = 'P8_YTB_NA'"

load_dotenv()
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
                     AND DATE(`PlannedFixedDate`) < CURDATE() THEN 1 ELSE 0 END) AS crossed_fpd
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


def detail_snapshot(scope_where):
    cur.execute(f"""
        SELECT
            SUM(`TicketStepID` IN ('{open_steps_sql}')) AS open_total,
            SUM(`TicketStepID` = 'Integrating') AS integrating,
            SUM(`TicketStepID` = 'Verifying') AS verifying
        FROM tbl_ElvisSR
        WHERE {BASE_WHERE} AND {scope_where}
    """)
    summary = cur.fetchone()
    cur.execute(f"""
        SELECT `PriorityID`, COUNT(*) AS cnt FROM tbl_ElvisSR
        WHERE {BASE_WHERE} AND {scope_where} AND `TicketStepID` IN ('{open_steps_sql}')
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
            SUM(DATEDIFF(CURDATE(), DATE(`EnterDateTime`)) > 15) AS age_over_15
        FROM tbl_ElvisSR
        WHERE {BASE_WHERE} AND {scope_where} AND `TicketStepID` IN ('{open_steps_sql}')
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
        WHERE {BASE_WHERE} AND {scope_where} AND `TicketStepID` IN ('{open_steps_sql}')
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
        WHERE {BASE_WHERE} AND {scope_where} AND `TicketStepID` IN ('{open_steps_sql}')
          AND `PlannedFixedDate` IS NOT NULL AND `PlannedFixedDate` != '0000-00-00'
          AND DATE(`PlannedFixedDate`) < CURDATE()
        ORDER BY `PlannedFixedDate`, `FGroup`, `TicketID`
    """)
    crossed = cur.fetchall()

    today = date.today()
    last5 = [today - timedelta(days=i) for i in range(5)]
    earliest5 = last5[-1]

    cur.execute(f"""
        SELECT `FGroup`, DATE(`EnterDateTime`) AS d, COUNT(*) AS cnt
        FROM tbl_ElvisSR
        WHERE {BASE_WHERE} AND {scope_where} AND DATE(`EnterDateTime`) >= %s
        GROUP BY `FGroup`, DATE(`EnterDateTime`)
    """, (earliest5,))
    domain_daily_in = {}
    for r in cur.fetchall():
        domain_daily_in.setdefault(r["FGroup"] or "Unknown", {})[str(r["d"])] = r["cnt"]

    domain_daily_out = {}
    cur.execute(f"""
        SELECT `FGroup`, DATE(`FirstIntegrDateTime`) AS d, COUNT(*) AS cnt
        FROM tbl_ElvisSR
        WHERE {BASE_WHERE} AND {scope_where} AND `Rejected` = 'N'
          AND DATE(`FirstIntegrDateTime`) >= %s
        GROUP BY `FGroup`, DATE(`FirstIntegrDateTime`)
    """, (earliest5,))
    for r in cur.fetchall():
        domain_daily_out.setdefault(r["FGroup"] or "Unknown", {})[str(r["d"])] = r["cnt"]
    cur.execute(f"""
        SELECT `FGroup`, DATE(`FirstConclDateTime`) AS d, COUNT(*) AS cnt
        FROM tbl_ElvisSR
        WHERE {BASE_WHERE} AND {scope_where} AND `Rejected` = 'Y'
          AND DATE(`FirstConclDateTime`) >= %s
        GROUP BY `FGroup`, DATE(`FirstConclDateTime`)
    """, (earliest5,))
    for r in cur.fetchall():
        key = str(r["d"])
        bucket = domain_daily_out.setdefault(r["FGroup"] or "Unknown", {})
        bucket[key] = bucket.get(key, 0) + r["cnt"]

    return {
        "summary": summary, "priorities": priorities, "domains": domains, "crossed": crossed,
        "no_fpd_domains": no_fpd_domains,
        "last5": last5, "domain_daily_in": domain_daily_in, "domain_daily_out": domain_daily_out,
    }


ytb_head = headline(YTB_SCOPE)
nonytb_head = headline(NONYTB_SCOPE)
ytb_domains = domain_priority_split(YTB_SCOPE)
nonytb_domains = domain_priority_split(NONYTB_SCOPE)
details = {
    "ytb": detail_snapshot(YTB_SCOPE),
    "non-ytb": detail_snapshot(NONYTB_SCOPE),
}

cur.close()
conn.close()

print("YTB:", ytb_head)
print("Non-YTB:", nonytb_head)
print(f"YTB domains: {len(ytb_domains)}, Non-YTB domains: {len(nonytb_domains)}")


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
        if h_once:
            label = str(bc_once_some) if h_once >= 9 else ""
            segs.append(f'<div style="width:{bar_width}px;height:{h_once}px;background:#2471a3;border-radius:3px 3px 0 0;color:#fff;font-size:8px;font-weight:700;text-align:center;line-height:{h_once}px;">{label}</div>')
        if h_always:
            label = str(bc_always) if h_always >= 9 else ""
            radius = "border-radius:3px 3px 0 0;" if not h_once else ""
            segs.append(f'<div style="width:{bar_width}px;height:{h_always}px;background:#f39c12;{radius}color:#7d4a00;font-size:8px;font-weight:700;text-align:center;line-height:{h_always}px;">{label}</div>')
        if h_top_a:
            label = str(top_a) if h_top_a >= 9 else ""
            radius = "border-radius:3px 3px 0 0;" if not h_once and not h_always else ""
            segs.append(f'<div style="width:{bar_width}px;height:{h_top_a}px;background:#c0392b;{radius}color:#fff;font-size:8px;font-weight:700;text-align:center;line-height:{h_top_a}px;">{label}</div>')
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


def replace_card(html, card_marker, open_val, crossed_val, nofpd_val, bars_html):
    # Update the 3 headline numbers immediately following the marker's OPEN/CROSSED FPD/NO FPD cells
    section_start = html.index(card_marker)
    section_end = html.index("Scope: FG_SWRev", section_start)
    section = html[section_start:section_end]

    section = re.sub(
        r'(OPEN</div><div style="font-size:26px;font-weight:700;color:#e67e22;">)\d+(</div>)',
        rf'\g<1>{open_val}\g<2>', section, count=1)
    section = re.sub(
        r'(CROSSED FPD</div><div style="font-size:26px;font-weight:700;color:#c0392b;">)\d+(</div>)',
        rf'\g<1>{crossed_val}\g<2>', section, count=1)
    section = re.sub(
        r'(NO FPD</div><div style="font-size:26px;font-weight:700;color:#c0392b;">)\d+(</div>)',
        rf'\g<1>{nofpd_val}\g<2>', section, count=1)

    # Replace the bars table body (between <tr> and </tr> inside the domain table)
    table_marker = 'style="margin-top:8px;border-bottom:2px solid #bdc3c7;height:150px;">'
    t_start = section.index(table_marker) + len(table_marker)
    row_start = section.index("<tr>", t_start) + len("<tr>")
    row_end = section.index("</tr>", row_start)
    section = section[:row_start] + "\n                " + bars_html + "\n            " + section[row_end:]

    return html[:section_start] + section + html[section_end:]


def n(value):
    return int(value or 0)


def cell(value, color="#34495e", bold=False):
    weight = "font-weight:600;" if bold else ""
    return (f'<td style="padding:5px 7px;border-bottom:1px solid #eee;text-align:center;'
            f'color:{color};{weight}">{n(value)}</td>')


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
    for i, row in enumerate(rows):
        bg = "#f8f9fa" if i % 2 == 0 else "#fff"
        name = row["FGroup"] or "Unknown"
        values = "".join(cell(row[k], "#c0392b" if k in ("crossed", "no_fpd") else "#34495e", k == "total") for k in keys)
        daily = "".join(
            daily_cell(domain_daily_in.get(name, {}).get(str(d), 0), True) +
            daily_cell(domain_daily_out.get(name, {}).get(str(d), 0), False)
            for d in last5
        )
        body.append(f'<tr style="background:{bg};"><td style="padding:5px 10px;border-bottom:1px solid #eee;white-space:nowrap;">{escape(name)}</td>{values}{daily}</tr>')
    totals = {key: sum(n(row[key]) for row in rows) for key in keys}
    total_cells = "".join(cell(totals[k], "#c0392b" if k in ("crossed", "no_fpd") else "#1a5276", True) for k in keys)
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
    if "getElementById('last-updated')" not in html:
        relative_script = '''<script>
(function renderRelativeUpdate() {
    var el = document.getElementById('last-updated');
    if (!el) return;
    var ts = new Date(el.getAttribute('data-timestamp'));
    function render() {
        var mins = Math.max(0, Math.floor((Date.now() - ts.getTime()) / 60000));
        if (mins < 1) el.textContent = 'Updated just now';
        else if (mins < 60) el.textContent = 'Updated ' + mins + ' min ago';
        else if (mins < 1440) el.textContent = 'Updated ' + Math.floor(mins / 60) + ' hr ago';
        else el.textContent = 'Updated ' + Math.floor(mins / 1440) + ' d ago';
    }
    render();
    setInterval(render, 60000);
})();
</script>
'''
        html = html.replace("</body>", relative_script + "</body>")
    return html, now


def update_detail_page(html, data, head, deadline):
    summary = data["summary"]
    for label, value in (("Open", summary["open_total"]), ("Integrating", summary["integrating"]),
                         ("Verification", summary["verifying"]), ("Crossed FPD", head["crossed_fpd"]),
                         ("No FPD", head["no_fpd"])):
        html = replace_number_card(html, label, value)
    days_left = max((deadline - date.today()).days, 0)
    fix_rate = n(summary["open_total"]) if days_left == 0 else (n(summary["open_total"]) + days_left - 1) // days_left
    html = replace_number_card(html, "Expected Fix Rate", fix_rate)
    html = re.sub(r'\(backlog ÷ \d+ days\)', f'(backlog ÷ {days_left} days)', html, count=1)
    html = re.sub(r'Fix rate needed: \d+/day', f'Fix rate needed: {fix_rate}/day', html, count=1)
    priority_html = "".join(f'<span style="display:inline-block;margin-right:12px;font-size:14px;"><strong style="color:#1a5276;">{escape(row["PriorityID"] or "Unknown")}</strong>: <span style="font-weight:600;color:#d35400;">{n(row["cnt"])}</span></span>' for row in data["priorities"])
    html = re.sub(r'(<div[^>]*>OPEN BY PRIORITY</div>\s*)<div>.*?</div>', rf'\1<div>{priority_html}</div>', html, count=1, flags=re.DOTALL)
    overall_start = html.index('<tr><td style="padding:0 28px 12px 28px;">')
    fpd_start = html.index('<!-- FPD Not Available', overall_start)
    html = html[:overall_start] + overall_domain_section(data["domains"], data["domain_daily_in"], data["domain_daily_out"], data["last5"]) + html[fpd_start:]
    fpd_start = html.index('<!-- FPD Not Available')
    crossed_start = html.index('<!-- Crossed FPD', fpd_start)
    html = html[:fpd_start] + no_fpd_section(data["domains"]) + html[crossed_start:]
    crossed_start = html.index('<!-- Crossed FPD')
    next_start = html.index('<!-- Platform Rejected', crossed_start)
    html = html[:crossed_start] + crossed_section(data["crossed"]) + html[next_start:]
    current_open = n(summary["open_total"])
    chart_start = html.find('<!-- Open Curve Chart -->')
    chart_end = html.find('Daily Inflow / Outflow', chart_start)
    if chart_start >= 0 and chart_end > chart_start:
        chart = html[chart_start:chart_end]
        labels = list(re.finditer(r'(<text[^>]*fill="#d35400"[^>]*>)\d+(</text>)', chart))
        if labels:
            latest = labels[-1]
            chart = chart[:latest.start()] + latest.group(1) + str(current_open) + latest.group(2) + chart[latest.end():]
            html = html[:chart_start] + chart + html[chart_end:]
    html = re.sub(r'Cumulative In \(Opening \+ Inflow\):.*?</div>', f'Current open snapshot: <strong style="color:#2471a3;">{current_open}</strong></div>', html, count=1, flags=re.DOTALL)
    html = re.sub(r'(Closing Trend.*?<tr style="background:[^"]+;"><td[^>]*>[^<]+</td><td[^>]*>)\d+(</td>)', rf'\g<1>{current_open}\g<2>', html, count=1, flags=re.DOTALL)
    html = html.replace("Closing Trend (Last 2 Weeks)", "Closing Trend (Last 15 Days)")
    html, now = stamp_timestamp(html)
    stamp = now.strftime("%Y%m%d_%H%M%S")
    html = re.sub(r'Updated on : \d+_\d+', f'Updated on : {stamp}', html, count=1)
    return html


for path in TARGET_FILES:
    with open(path, "r", encoding="utf-8") as f:
        html = f.read()

    html = replace_card(html, "YTB &mdash; Open Tickets", ytb_head["open_total"], ytb_head["crossed_fpd"], ytb_head["no_fpd"], ytb_bars_html)
    html = replace_card(html, "Non-YTB &mdash; Open Tickets", nonytb_head["open_total"], nonytb_head["crossed_fpd"], nonytb_head["no_fpd"], nonytb_bars_html)
    html, _ = stamp_timestamp(html)

    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Updated {path}")

deadlines = {"ytb": date(2026, 9, 24), "non-ytb": date(2026, 10, 24)}
heads = {"ytb": ytb_head, "non-ytb": nonytb_head}
for name, path in DETAIL_FILES.items():
    with open(path, "r", encoding="utf-8") as f:
        html = f.read()
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
