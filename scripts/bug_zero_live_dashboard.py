"""
DA2.8 Bug Zero — Live Streamlit Dashboard
Run: streamlit run scripts/bug_zero_live_dashboard.py --server.address 0.0.0.0
"""
import sys, os
# Add C:\pylibs to path for streamlit/plotly
sys.path.insert(0, r"C:\pylibs")

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime, timedelta, date
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

# ── DB connection ──
def get_connection():
    return mysql.connector.connect(
        host=os.getenv("ELVIS_DB_HOST"),
        user=os.getenv("ELVIS_DB_USER"),
        password=os.getenv("ELVIS_DB_PASSWORD"),
        database=os.getenv("ELVIS_DB_NAME"),
        port=int(os.getenv("ELVIS_DB_PORT", 3306)),
        connection_timeout=15,
    )

# ── Fetch all data ──
@st.cache_data(ttl=300)  # cache 5 min
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

    # Reproduction by domain
    cursor.execute(f"""
        SELECT `FGroup`, COUNT(*) as cnt FROM tbl_ElvisSR
        WHERE {BUG_ZERO_WHERE} AND `TicketStepID` = 'Reproduction'
        GROUP BY `FGroup` ORDER BY cnt DESC
    """)
    domain_repro = {r["FGroup"]: r["cnt"] for r in cursor.fetchall()}

    # TOP + A(1) by domain
    cursor.execute(f"""
        SELECT `FGroup`, COUNT(*) as cnt FROM tbl_ElvisSR
        WHERE {BUG_ZERO_WHERE} AND `TicketStepID` IN ('{open_steps_sql}')
          AND `PriorityID` IN ('A(1)', 'top')
        GROUP BY `FGroup` ORDER BY cnt DESC
    """)
    domain_top_a = {r["FGroup"]: r["cnt"] for r in cursor.fetchall()}

    # Platform (TYP_2) by domain
    cursor.execute(f"""
        SELECT `FGroup`, COUNT(*) as cnt FROM tbl_ElvisSR
        WHERE {BUG_ZERO_WHERE} AND `TicketStepID` IN ('{open_steps_sql}')
          AND `SlaveType` = 'TYP_2'
        GROUP BY `FGroup` ORDER BY cnt DESC
    """)
    domain_platform = {r["FGroup"]: r["cnt"] for r in cursor.fetchall()}

    # Project (non-TYP_2) by domain
    cursor.execute(f"""
        SELECT `FGroup`, COUNT(*) as cnt FROM tbl_ElvisSR
        WHERE {BUG_ZERO_WHERE} AND `TicketStepID` IN ('{open_steps_sql}')
          AND (`SlaveType` IS NULL OR `SlaveType` != 'TYP_2')
        GROUP BY `FGroup` ORDER BY cnt DESC
    """)
    domain_project = {r["FGroup"]: r["cnt"] for r in cursor.fetchall()}

    # Priority breakdown
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

    # Domain daily inflow (last 5 days)
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

    # Domain daily outflow (last 5 days)
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

    # Expected outflow today
    cursor.execute(f"""
        SELECT `TicketID`, `Title`, `FGroup`, `PlannedFixedDate`, `SlaveType` FROM tbl_ElvisSR
        WHERE {BUG_ZERO_WHERE} AND `TicketStepID` IN ('{open_steps_sql}')
          AND DATE(`PlannedFixedDate`) = %s
        ORDER BY `FGroup`, `TicketID`
    """, (today,))
    expected_outflow_raw = [(r["TicketID"], r["Title"] or "", r["FGroup"] or "Unknown", r["PlannedFixedDate"], r["SlaveType"] or "NONE") for r in cursor.fetchall()]

    # Expected outflow tomorrow
    tomorrow = today + timedelta(days=1)
    cursor.execute(f"""
        SELECT `TicketID`, `Title`, `FGroup`, `PlannedFixedDate`, `SlaveType` FROM tbl_ElvisSR
        WHERE {BUG_ZERO_WHERE} AND `TicketStepID` IN ('{open_steps_sql}')
          AND DATE(`PlannedFixedDate`) = %s
        ORDER BY `FGroup`, `TicketID`
    """, (tomorrow,))
    expected_outflow_tomorrow_raw = [(r["TicketID"], r["Title"] or "", r["FGroup"] or "Unknown", r["PlannedFixedDate"], r["SlaveType"] or "NONE") for r in cursor.fetchall()]

    # Today's closed tickets (integrated today OR rejected today) — for strikethrough
    cursor.execute(f"""
        SELECT `TicketID` FROM tbl_ElvisSR
        WHERE {BUG_ZERO_WHERE} AND `Rejected` = 'N'
          AND DATE(`FirstIntegrDateTime`) = %s
    """, (today,))
    closed_today = set(r["TicketID"] for r in cursor.fetchall())
    cursor.execute(f"""
        SELECT `TicketID` FROM tbl_ElvisSR
        WHERE {BUG_ZERO_WHERE} AND `Rejected` = 'Y'
          AND DATE(`FirstConclDateTime`) = %s
    """, (today,))
    closed_today |= set(r["TicketID"] for r in cursor.fetchall())

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
    crossed_fpd_raw = [(r["TicketID"], r["Title"] or "", r["FGroup"] or "Unknown", r["PlannedFixedDate"], r["SlaveType"] or "NONE") for r in cursor.fetchall()]

    # FPD Not Available
    cursor.execute(f"""
        SELECT `TicketID`, `Title`, `FGroup`, `TicketStepID`, `SlaveType` FROM tbl_ElvisSR
        WHERE {BUG_ZERO_WHERE} AND `TicketStepID` IN ('{open_steps_sql}')
          AND (`PlannedFixedDate` IS NULL OR DATE(`PlannedFixedDate`) = '0000-00-00' OR YEAR(`PlannedFixedDate`) = 0)
        ORDER BY `FGroup`, `TicketID`
    """)
    fpd_na_raw = [(r["TicketID"], r["Title"] or "", r["FGroup"] or "Unknown", r["TicketStepID"] or "", r["SlaveType"] or "NONE") for r in cursor.fetchall()]

    # IC Platform rejection check
    typ2_ids = set()
    for lst in (crossed_fpd_raw, fpd_na_raw, expected_outflow_raw, expected_outflow_tomorrow_raw):
        for row in lst:
            if row[4] == "TYP_2":
                typ2_ids.add(row[0])
    cursor.execute(f"""
        SELECT `TicketID`, `Title`, `FGroup`, `TicketStepID`, `PlannedFixedDate` FROM tbl_ElvisSR
        WHERE {BUG_ZERO_WHERE} AND `TicketStepID` IN ('{open_steps_sql}')
          AND `SlaveType` = 'TYP_2'
        ORDER BY `FGroup`, `TicketID`
    """)
    all_open_typ2 = [(r["TicketID"], r["Title"] or "", r["FGroup"] or "Unknown", r["TicketStepID"] or "", r["PlannedFixedDate"]) for r in cursor.fetchall()]
    for row in all_open_typ2:
        typ2_ids.add(row[0])

    ic_rejected = set()
    ic_ticket_map = {}
    if typ2_ids:
        id_ph = ",".join(["%s"] * len(typ2_ids))
        cursor.execute(f"""
            SELECT `TicketID`, `IntRefNo`, `Rejected` FROM tbl_ElvisSR
            WHERE `ProjectID` = 'Intelligent Cockpit Platform'
              AND `IntRefNo` IN ({id_ph})
        """, list(str(tid) for tid in typ2_ids))
        for r in cursor.fetchall():
            try:
                da28_tid = int(r["IntRefNo"])
                ic_ticket_map[da28_tid] = r["TicketID"]
                if r["Rejected"] == "Y":
                    ic_rejected.add(da28_tid)
            except (ValueError, TypeError):
                pass

    def _ticket_type(tid, slave_type):
        if slave_type == "TYP_2" and tid not in ic_rejected:
            return "Platform"
        return "Project"

    crossed_fpd = [(tid, title, dom, fpd, _ticket_type(tid, st)) for tid, title, dom, fpd, st in crossed_fpd_raw]
    fpd_not_available = [(tid, title, dom, step, _ticket_type(tid, st)) for tid, title, dom, step, st in fpd_na_raw]
    expected_outflow = [(tid, title, dom, fpd, _ticket_type(tid, st)) for tid, title, dom, fpd, st in expected_outflow_raw]
    expected_outflow_tomorrow = [(tid, title, dom, fpd, _ticket_type(tid, st)) for tid, title, dom, fpd, st in expected_outflow_tomorrow_raw]
    platform_rejected = [(tid, title, dom, step, fpd, ic_ticket_map.get(tid, "")) for tid, title, dom, step, fpd in all_open_typ2 if tid in ic_rejected]

    # Adjust Platform/Project counts for IC rejection
    for tid, title, dom, step, fpd in all_open_typ2:
        if tid in ic_rejected:
            domain_platform[dom] = domain_platform.get(dom, 0) - 1
            domain_project[dom] = domain_project.get(dom, 0) + 1
            if domain_platform.get(dom, 0) <= 0:
                domain_platform.pop(dom, None)

    cursor.close()
    conn.close()

    return {
        "today": today,
        "dates": dates,
        "last5": last5,
        "domain_open": domain_open,
        "domain_repro": domain_repro,
        "domain_top_a": domain_top_a,
        "domain_platform": domain_platform,
        "domain_project": domain_project,
        "priority_open": priority_open,
        "daily_inflow": daily_inflow,
        "daily_outflow": daily_outflow,
        "domain_daily_inflow": domain_daily_inflow,
        "domain_daily_outflow": domain_daily_outflow,
        "expected_outflow": expected_outflow,
        "expected_outflow_tomorrow": expected_outflow_tomorrow,
        "crossed_fpd": crossed_fpd,
        "fpd_not_available": fpd_not_available,
        "platform_rejected": platform_rejected,
        "ic_ticket_map": ic_ticket_map,
        "total_open": sum(domain_open.values()),
        "closed_today": closed_today,
    }


# ── Streamlit Dashboard ──
st.set_page_config(page_title="DA2.8 Bug Zero Dashboard", layout="wide", page_icon="🎯")

st.markdown("""
<style>
    .stMetric {border: 1px solid #e0e0e0; border-radius: 8px; padding: 12px;}
    div[data-testid="stMetricValue"] {font-size: 2rem;}
    .closed-ticket {text-decoration: line-through; color: #27ae60 !important; opacity: 0.7;}
</style>
""", unsafe_allow_html=True)

st.title("🎯 DA2.8 Bug Zero — Live Dashboard")

# Refresh button
col_title, col_refresh = st.columns([8, 1])
with col_refresh:
    if st.button("🔄 Refresh"):
        st.cache_data.clear()
        st.rerun()

# Load data
with st.spinner("Fetching Bug Zero data from Elvis DB..."):
    data = fetch_data()

today = data["today"]
total = data["total_open"]
deadline = date(2026, 5, 31)
days_left = sum(1 for i in range((deadline - today).days + 1) if (today + timedelta(days=i)).weekday() < 5)
fix_rate = round(total / days_left, 1) if days_left > 0 else total
yesterday = today - timedelta(days=1)
y_inflow = data["daily_inflow"].get(yesterday, 0)
y_outflow = data["daily_outflow"].get(yesterday, 0)
y_net = y_outflow - y_inflow
closed_today = data["closed_today"]

# ── KPI Cards ──
st.markdown("### 📊 Key Metrics")
k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Total Open", total)
k2.metric("Working Days Left", days_left)
k3.metric("Fix Rate/Day", fix_rate)
k4.metric("Yesterday Net", f"{y_net:+d}", delta=f"{'▲ reducing' if y_net > 0 else '▼ growing'}", delta_color="normal" if y_net > 0 else "inverse")
k5.metric("Closed Today", len(closed_today))

# Priority breakdown
st.markdown("### 🔥 Priority Breakdown")
p1, p2, p3, p4 = st.columns(4)
prio = data["priority_open"]
p1.metric("TOP", prio.get("top", 0))
p2.metric("A(1)", prio.get("A(1)", 0))
p3.metric("B(2)", prio.get("B(2)", 0))
p4.metric("C(3)", prio.get("C(3)", 0))

# ── Closing Trend Chart ──
st.markdown("### 📈 Closing Trend (from May 8)")
trend_dates = sorted(data["dates"])
inflows = [data["daily_inflow"].get(d, 0) for d in trend_dates]
outflows = [data["daily_outflow"].get(d, 0) for d in trend_dates]
nets = [o - i for i, o in zip(inflows, outflows)]

# Calculate running open count
open_counts = []
running = total
for d in reversed(trend_dates):
    if d == today:
        open_counts.insert(0, running)
    else:
        net_d = data["daily_outflow"].get(d, 0) - data["daily_inflow"].get(d, 0)
        running += net_d  # going backwards, reverse the net
        open_counts.insert(0, running)

date_labels = [d.strftime("%d-%b") for d in trend_dates]

fig = go.Figure()
fig.add_trace(go.Scatter(x=date_labels, y=open_counts, name="Open", mode="lines+markers",
                         line=dict(color="#e67e22", width=3), marker=dict(size=6)))
fig.add_trace(go.Bar(x=date_labels, y=inflows, name="Inflow", marker_color="#e74c3c", opacity=0.7))
fig.add_trace(go.Bar(x=date_labels, y=outflows, name="Outflow", marker_color="#27ae60", opacity=0.7))
fig.add_trace(go.Scatter(x=date_labels, y=nets, name="Net", mode="lines+markers",
                         line=dict(color="#3498db", width=2, dash="dash"), marker=dict(size=5)))
fig.update_layout(barmode="group", height=400, margin=dict(l=40, r=20, t=30, b=40),
                  legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0.5, xanchor="center"),
                  yaxis2=dict(overlaying="y", side="right"))
st.plotly_chart(fig, use_container_width=True)

# ── Domain Table ──
st.markdown("### 🏢 Domain-wise Status")
all_domains = sorted(data["domain_open"].keys())
domain_rows = []
for dom in all_domains:
    row = {
        "Domain": dom,
        "Open": data["domain_open"].get(dom, 0),
        "Platform": data["domain_platform"].get(dom, 0),
        "Project": data["domain_project"].get(dom, 0),
        "TOP+A": data["domain_top_a"].get(dom, 0),
        "Repro": data["domain_repro"].get(dom, 0),
    }
    for d in data["last5"]:
        dl = d.strftime("%d-%b")
        row[f"{dl} In"] = data["domain_daily_inflow"].get(dom, {}).get(d, 0)
        row[f"{dl} Out"] = data["domain_daily_outflow"].get(dom, {}).get(d, 0)
    domain_rows.append(row)

# Add totals row
totals = {"Domain": "TOTAL", "Open": sum(r["Open"] for r in domain_rows),
          "Platform": sum(r["Platform"] for r in domain_rows),
          "Project": sum(r["Project"] for r in domain_rows),
          "TOP+A": sum(r["TOP+A"] for r in domain_rows),
          "Repro": sum(r["Repro"] for r in domain_rows)}
for d in data["last5"]:
    dl = d.strftime("%d-%b")
    totals[f"{dl} In"] = sum(r[f"{dl} In"] for r in domain_rows)
    totals[f"{dl} Out"] = sum(r[f"{dl} Out"] for r in domain_rows)
domain_rows.append(totals)

df_domain = pd.DataFrame(domain_rows)
st.dataframe(df_domain, use_container_width=True, hide_index=True,
             column_config={"Open": st.column_config.NumberColumn(format="%d"),
                           "Platform": st.column_config.NumberColumn(format="%d"),
                           "Project": st.column_config.NumberColumn(format="%d")})

# ── Expected Outflow Today (with strikethrough for closed) ──
st.markdown(f"### ✅ Expected Outflow Today ({len(data['expected_outflow'])} tickets)")
ic_map = data.get("ic_ticket_map", {})
if data["expected_outflow"]:
    eo_rows = []
    for tid, title, dom, fpd, ttype in sorted(data["expected_outflow"], key=lambda x: x[2]):
        is_closed = tid in closed_today
        eo_rows.append({
            "Status": "✅ Closed" if is_closed else "⏳ Open",
            "Ticket ID": tid,
            "IC Platform": ic_map.get(tid, ""),
            "Domain": dom,
            "Type": ttype,
            "Title": title[:80],
        })
    df_eo = pd.DataFrame(eo_rows)
    st.dataframe(df_eo, use_container_width=True, hide_index=True)
    closed_count = sum(1 for r in eo_rows if r["Status"] == "✅ Closed")
    st.caption(f"✅ {closed_count} closed / ⏳ {len(eo_rows) - closed_count} remaining")
else:
    st.info("No tickets with FPD today")

# ── Expected Outflow Tomorrow ──
st.markdown(f"### 📅 Expected Outflow Tomorrow ({len(data['expected_outflow_tomorrow'])} tickets)")
if data["expected_outflow_tomorrow"]:
    et_rows = []
    for tid, title, dom, fpd, ttype in sorted(data["expected_outflow_tomorrow"], key=lambda x: x[2]):
        et_rows.append({
            "Ticket ID": tid,
            "IC Platform": ic_map.get(tid, ""),
            "Domain": dom,
            "Type": ttype,
            "Title": title[:80],
        })
    st.dataframe(pd.DataFrame(et_rows), use_container_width=True, hide_index=True)
else:
    st.info("No tickets with FPD tomorrow")

# ── Crossed FPD ──
st.markdown(f"### ⚠️ Crossed FPD — Overdue ({len(data['crossed_fpd'])} tickets)")
if data["crossed_fpd"]:
    cf_rows = []
    for tid, title, dom, fpd, ttype in sorted(data["crossed_fpd"], key=lambda x: x[2]):
        fpd_d = fpd.date() if isinstance(fpd, datetime) else fpd
        days_overdue = (today - fpd_d).days if fpd_d else 0
        cf_rows.append({
            "Ticket ID": tid,
            "IC Platform": ic_map.get(tid, ""),
            "Domain": dom,
            "Type": ttype,
            "Title": title[:80],
            "FPD": fpd_d.strftime("%d-%b") if fpd_d else "",
            "Overdue (days)": days_overdue,
        })
    df_cf = pd.DataFrame(cf_rows)
    # Domain filter
    domains_cf = ["All"] + sorted(df_cf["Domain"].unique().tolist())
    sel_dom = st.selectbox("Filter by Domain", domains_cf, key="cf_domain")
    if sel_dom != "All":
        df_cf = df_cf[df_cf["Domain"] == sel_dom]
    st.dataframe(df_cf, use_container_width=True, hide_index=True)
else:
    st.success("No overdue tickets!")

# ── FPD Not Available ──
st.markdown(f"### ⚠️ FPD Not Available ({len(data['fpd_not_available'])} tickets)")
if data["fpd_not_available"]:
    fn_rows = []
    for tid, title, dom, step, ttype in sorted(data["fpd_not_available"], key=lambda x: x[2]):
        fn_rows.append({
            "Ticket ID": tid,
            "IC Platform": ic_map.get(tid, ""),
            "Domain": dom,
            "Type": ttype,
            "Title": title[:80],
            "Step": step,
        })
    df_fn = pd.DataFrame(fn_rows)
    domains_fn = ["All"] + sorted(df_fn["Domain"].unique().tolist())
    sel_dom_fn = st.selectbox("Filter by Domain", domains_fn, key="fn_domain")
    if sel_dom_fn != "All":
        df_fn = df_fn[df_fn["Domain"] == sel_dom_fn]
    st.dataframe(df_fn, use_container_width=True, hide_index=True)
else:
    st.success("All tickets have FPD!")

# ── Platform Rejected ──
st.markdown(f"### 🚫 Platform Rejected ({len(data['platform_rejected'])} tickets)")
if data["platform_rejected"]:
    pr_rows = []
    for tid, title, dom, step, fpd, ic_tid in sorted(data["platform_rejected"], key=lambda x: x[2]):
        fpd_str = ""
        if fpd:
            fpd_d = fpd.date() if isinstance(fpd, datetime) else fpd
            try:
                fpd_str = fpd_d.strftime("%d-%b") if fpd_d and fpd_d.year > 1 else ""
            except Exception:
                fpd_str = ""
        pr_rows.append({
            "Ticket ID": tid,
            "IC Platform": ic_tid,
            "Domain": dom,
            "Step": step,
            "FPD": fpd_str,
        })
    st.dataframe(pd.DataFrame(pr_rows), use_container_width=True, hide_index=True)
else:
    st.info("No platform-rejected tickets")

# ── Platform vs Project Pie Chart ──
st.markdown("### 🔮 Platform vs Project Split")
c1, c2 = st.columns(2)
total_plat = sum(data["domain_platform"].values())
total_proj = sum(data["domain_project"].values())
with c1:
    fig_pie = go.Figure(data=[go.Pie(labels=["Platform", "Project"], values=[total_plat, total_proj],
                                      marker=dict(colors=["#8e44ad", "#2471a3"]),
                                      textinfo="label+value+percent", hole=0.4)])
    fig_pie.update_layout(height=300, margin=dict(l=20, r=20, t=30, b=20), title="Overall")
    st.plotly_chart(fig_pie, use_container_width=True)
with c2:
    # Top 10 domains by open count
    top10 = sorted(data["domain_open"].items(), key=lambda x: -x[1])[:10]
    fig_bar = go.Figure()
    fig_bar.add_trace(go.Bar(name="Platform", x=[d[0] for d in top10],
                             y=[data["domain_platform"].get(d[0], 0) for d in top10],
                             marker_color="#8e44ad"))
    fig_bar.add_trace(go.Bar(name="Project", x=[d[0] for d in top10],
                             y=[data["domain_project"].get(d[0], 0) for d in top10],
                             marker_color="#2471a3"))
    fig_bar.update_layout(barmode="stack", height=300, margin=dict(l=20, r=20, t=30, b=20), title="Top 10 Domains")
    st.plotly_chart(fig_bar, use_container_width=True)

# Footer
st.markdown("---")
st.caption(f"Data refreshed at {datetime.now().strftime('%H:%M:%S')} | Auto-refresh every 5 min | Last DB query cached for 5 min")
st.caption("💡 Other team members can access this dashboard at `http://<your-machine-IP>:8501`")
