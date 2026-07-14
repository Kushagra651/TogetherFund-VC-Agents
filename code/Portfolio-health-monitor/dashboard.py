"""
Together Fund — Portfolio Health Monitor
Streamlit dashboard: real-time signal analysis, health badges, trend charts.
"""
import json
import time
import threading
from pathlib import Path
from datetime import datetime, timezone

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd

from app.database import init_db, get_latest_reports, get_company_history
from app.monitor import run_company_analysis, run_full_portfolio
from app.scheduler import start_scheduler

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Together Fund | Portfolio Monitor",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded",
)

COMPANIES_PATH = Path(__file__).parent / "data" / "companies.json"
companies = json.loads(COMPANIES_PATH.read_text())

# ── Bootstrap ─────────────────────────────────────────────────────────────────
init_db()

# Start scheduler once per process
if "scheduler_started" not in st.session_state:
    start_scheduler()
    st.session_state.scheduler_started = True

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

.main { background: #0a0f1e; }
[data-testid="stSidebar"] { background: #0d1326 !important; border-right: 1px solid #1e2d4a; }
[data-testid="stSidebar"] * { color: #e2e8f0 !important; }

/* Header */
.tf-header {
    background: linear-gradient(135deg, #0d1f3c 0%, #1a3a5c 100%);
    border: 1px solid #1e4080;
    border-radius: 16px;
    padding: 28px 36px;
    margin-bottom: 28px;
    display: flex;
    align-items: center;
    justify-content: space-between;
}
.tf-header h1 { color: #f0f4ff; font-size: 1.9rem; font-weight: 700; margin: 0; }
.tf-header p { color: #7ca3d4; margin: 4px 0 0; font-size: 0.9rem; }
.tf-badge { background: #1e4080; border: 1px solid #3a6bc8; border-radius: 20px;
            padding: 6px 14px; color: #93c5fd; font-size: 0.78rem; font-weight: 600; }

/* Status cards */
.card-green  { background: #042a1a; border: 1px solid #16a34a; border-radius: 14px; padding: 20px; }
.card-yellow { background: #2a1f02; border: 1px solid #ca8a04; border-radius: 14px; padding: 20px; }
.card-red    { background: #2a0606; border: 1px solid #dc2626; border-radius: 14px; padding: 20px; }

.card-title { font-size: 1.05rem; font-weight: 700; color: #f0f4ff; margin-bottom: 6px; }
.card-sector { font-size: 0.75rem; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.05em; }
.card-headline { font-size: 0.85rem; color: #cbd5e1; margin-top: 10px; line-height: 1.4; }
.card-funding { font-size: 0.75rem; color: #64748b; margin-top: 8px; }

/* Status pill */
.pill-green  { background:#16a34a22; border:1px solid #16a34a; color:#4ade80; border-radius:20px;
               padding:3px 12px; font-size:0.72rem; font-weight:700; display:inline-block; }
.pill-yellow { background:#ca8a0422; border:1px solid #ca8a04; color:#fbbf24; border-radius:20px;
               padding:3px 12px; font-size:0.72rem; font-weight:700; display:inline-block; }
.pill-red    { background:#dc262622; border:1px solid #dc2626; color:#f87171; border-radius:20px;
               padding:3px 12px; font-size:0.72rem; font-weight:700; display:inline-block; }

/* Metrics row */
.metric-box { background:#111827; border:1px solid #1f2937; border-radius:10px; padding:14px 18px; }
.metric-label { font-size:0.72rem; color:#64748b; text-transform:uppercase; letter-spacing:0.05em; }
.metric-value { font-size:1.5rem; font-weight:700; color:#f0f4ff; }
.metric-delta-up   { color:#4ade80; font-size:0.78rem; }
.metric-delta-down { color:#f87171; font-size:0.78rem; }
.metric-delta-flat { color:#94a3b8; font-size:0.78rem; }

/* Log console */
.log-console {
    background: #050a14;
    border: 1px solid #1e2d4a;
    border-radius: 10px;
    padding: 16px;
    font-family: 'JetBrains Mono', 'Fira Code', monospace;
    font-size: 0.78rem;
    color: #7dd3fc;
    max-height: 320px;
    overflow-y: auto;
    line-height: 1.7;
}

/* Reasoning box */
.reasoning-box {
    background: #0d1626;
    border-left: 3px solid #3a6bc8;
    border-radius: 0 8px 8px 0;
    padding: 14px 18px;
    color: #94a3b8;
    font-size: 0.83rem;
    line-height: 1.6;
    margin-top: 10px;
}

/* Section headers */
.section-title {
    font-size: 0.75rem;
    font-weight: 600;
    color: #475569;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin: 20px 0 12px;
    border-bottom: 1px solid #1e2d4a;
    padding-bottom: 6px;
}

/* Divider */
hr { border-color: #1e2d4a !important; }

[data-testid="collapsedControl"] {
    display: block !important;
    visibility: visible !important;
}
section[data-testid="stSidebar"] {
    display: block !important;
    visibility: visible !important;
}
            
/* Hide Streamlit branding */
#MainMenu,
</style>
""", unsafe_allow_html=True)


# ── Helper functions ──────────────────────────────────────────────────────────

STATUS_EMOJI = {"green": "🟢", "yellow": "🟡", "red": "🔴"}
PILL = {"green": "pill-green", "yellow": "pill-yellow", "red": "pill-red"}
CARD = {"green": "card-green", "yellow": "card-yellow", "red": "card-red"}

def get_company_meta(name: str) -> dict:
    return next((c for c in companies if c["name"] == name), {})

def delta_color_class(pct: float) -> str:
    if pct > 2: return "metric-delta-up"
    if pct < -2: return "metric-delta-down"
    return "metric-delta-flat"

def delta_arrow(pct: float) -> str:
    if pct > 2: return "▲"
    if pct < -2: return "▼"
    return "→"

def headcount_sparkline(history: list[int]) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        y=history, mode="lines+markers",
        line=dict(color="#3a6bc8", width=2.5),
        marker=dict(size=5, color="#93c5fd"),
        fill="tozeroy", fillcolor="rgba(58,107,200,0.08)"
    ))
    fig.update_layout(
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
        xaxis=dict(visible=False),
        yaxis=dict(visible=False, range=[max(0, min(history)-5), max(history)+5]),
        height=70,
    )
    return fig


# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("## 📡 Portfolio Monitor")
    st.markdown("---")

    st.markdown("### 🔄 Refresh Controls")
    refresh_mode = st.radio(
        "Refresh mode",
        ["Single company", "Full portfolio"],
        index=1,
        help="Single: analyse one company. Full: re-scan all 10."
    )

    selected_company = None
    if refresh_mode == "Single company":
        selected_company = st.selectbox("Select company", [c["name"] for c in companies])

    force_refresh = st.checkbox("Force refresh (ignore cache)", value=False)

    if st.button("🚀 Run Analysis", type="primary", use_container_width=True):
        st.session_state.run_analysis = True
        st.session_state.run_single = selected_company if refresh_mode == "Single company" else None
        st.session_state.force = force_refresh

    st.markdown("---")
    st.markdown("### 🔍 Filters")
    filter_status = st.multiselect(
        "Show status",
        ["green", "yellow", "red"],
        default=["green", "yellow", "red"],
        format_func=lambda s: f"{STATUS_EMOJI[s]} {s.capitalize()}"
    )
    filter_sector = st.multiselect(
        "Sector",
        sorted(set(c["sector"] for c in companies)),
        default=[]
    )

    st.markdown("---")
    st.markdown("### 📋 About")
    st.caption("Together Fund Portfolio Health Monitor — AI-powered weekly signal analysis across headcount, news, and hiring data.")
    st.caption(f"Last page load: {datetime.now().strftime('%d %b %Y, %H:%M')}")


# ── Header ────────────────────────────────────────────────────────────────────

reports = get_latest_reports()
n_green  = sum(1 for r in reports if r["health"]["status"] == "green")
n_yellow = sum(1 for r in reports if r["health"]["status"] == "yellow")
n_red    = sum(1 for r in reports if r["health"]["status"] == "red")

st.markdown(f"""
<div class="tf-header">
  <div>
    <h1>📡 Portfolio Health Monitor</h1>
    <p>Together Fund · {len(companies)} companies tracked · Updated weekly</p>
  </div>
  <div style="display:flex;gap:10px;">
    <span class="tf-badge">🟢 {n_green} Healthy</span>
    <span class="tf-badge">🟡 {n_yellow} Watch</span>
    <span class="tf-badge">🔴 {n_red} Urgent</span>
  </div>
</div>
""", unsafe_allow_html=True)


# ── Summary metrics ───────────────────────────────────────────────────────────

col1, col2, col3, col4, col5 = st.columns(5)
metrics = [
    ("Companies Tracked", len(companies), None),
    ("🟢 Healthy", n_green, None),
    ("🟡 Watch", n_yellow, None),
    ("🔴 Urgent", n_red, None),
    ("Last Analysed", len(reports), None),
]
for col, (label, val, _) in zip([col1, col2, col3, col4, col5], metrics):
    col.markdown(f"""
    <div class="metric-box">
      <div class="metric-label">{label}</div>
      <div class="metric-value">{val}</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)


# ── Live Analysis Panel ───────────────────────────────────────────────────────

if st.session_state.get("run_analysis"):
    st.session_state.run_analysis = False
    st.markdown('<div class="section-title">⚡ Live Analysis Log</div>', unsafe_allow_html=True)

    log_placeholder = st.empty()
    log_lines = []

    def stream_log(msg: str):
        ts = datetime.now().strftime("%H:%M:%S")
        log_lines.append(f"<span style='color:#475569'>[{ts}]</span> {msg}")
        log_placeholder.markdown(
            f'<div class="log-console">{"<br>".join(log_lines[-30:])}</div>',
            unsafe_allow_html=True
        )

    progress_bar = st.progress(0, text="Starting analysis...")
    target_companies = (
        [next(c for c in companies if c["name"] == st.session_state.run_single)]
        if st.session_state.run_single
        else companies
    )
    total = len(target_companies)

    for i, company in enumerate(target_companies):
        progress_bar.progress((i) / total, text=f"Analysing {company['name']}...")
        run_company_analysis(company, log_cb=stream_log, force=st.session_state.force)
        progress_bar.progress((i + 1) / total, text=f"Done: {company['name']}")

    progress_bar.progress(1.0, text="✅ Analysis complete!")
    time.sleep(0.8)
    progress_bar.empty()
    st.success(f"✅ Analysed {total} compan{'y' if total==1 else 'ies'}. Dashboard updated.")
    st.rerun()


# ── Portfolio Dashboard ───────────────────────────────────────────────────────

st.markdown('<div class="section-title">📊 Portfolio Overview</div>', unsafe_allow_html=True)

if not reports:
    st.info("No data yet — click **Run Analysis** in the sidebar to scan the portfolio.", icon="ℹ️")
else:
    # Build filtered report list
    filtered = []
    for r in reports:
        meta = get_company_meta(r["company_name"])
        status = r["health"]["status"]
        if status not in filter_status:
            continue
        if filter_sector and meta.get("sector") not in filter_sector:
            continue
        filtered.append((r, meta))

    # Sort: red first, then yellow, then green
    order = {"red": 0, "yellow": 1, "green": 2}
    filtered.sort(key=lambda x: order.get(x[0]["health"]["status"], 3))

    if not filtered:
        st.warning("No companies match the current filters.")
    else:
        cols = st.columns(2)
        for idx, (report, meta) in enumerate(filtered):
            health = report["health"]
            snap   = report["snapshot"]
            status = health["status"]
            hc_delta = snap.get("headcount_delta_pct", 0)
            col = cols[idx % 2]

            with col:
                with st.container():
                    st.markdown(f"""
                    <div class="{CARD[status]}">
                      <div style="display:flex;justify-content:space-between;align-items:flex-start;">
                        <div>
                          <div class="card-sector">{meta.get('sector','—')} · Founded {meta.get('founded','')}</div>
                          <div class="card-title">{STATUS_EMOJI[status]} {report['company_name']}</div>
                        </div>
                        <div><span class="{PILL[status]}">{status.upper()}</span></div>
                      </div>
                      <div class="card-headline">"{health['headline']}"</div>
                      <div class="card-funding">{meta.get('last_funding','')}</div>
                    </div>
                    """, unsafe_allow_html=True)

                    # Mini metrics row
                    m1, m2, m3 = st.columns(3)
                    arrow = delta_arrow(hc_delta)
                    dc = delta_color_class(hc_delta)
                    m1.markdown(f"""<div class="metric-box">
                        <div class="metric-label">Headcount</div>
                        <div class="metric-value">{snap['headcount_current']}</div>
                        <div class="{dc}">{arrow} {hc_delta:+.1f}%</div>
                    </div>""", unsafe_allow_html=True)
                    m2.markdown(f"""<div class="metric-box">
                        <div class="metric-label">News Signals</div>
                        <div class="metric-value">{snap['news_count']}</div>
                        <div class="metric-delta-flat">last 30d</div>
                    </div>""", unsafe_allow_html=True)
                    m3.markdown(f"""<div class="metric-box">
                        <div class="metric-label">Job Postings</div>
                        <div class="metric-value">{snap['job_postings_count']}</div>
                        <div class="metric-delta-flat">found</div>
                    </div>""", unsafe_allow_html=True)

                    # Headcount trend sparkline
                    if meta.get("headcount_history"):
                        st.plotly_chart(
                            headcount_sparkline(meta["headcount_history"]),
                            use_container_width=True, config={"displayModeBar": False}
                        )

                    # Expandable reasoning
                    with st.expander("🧠 Why this status? (Claude's reasoning)"):
                        st.markdown(f"""<div class="reasoning-box">{health['reasoning']}</div>""",
                                    unsafe_allow_html=True)
                        if health.get("signals_used"):
                            st.markdown("**Signals used:**")
                            for sig in health["signals_used"]:
                                st.markdown(f"- {sig}")
                        rec = health.get("recommended_action", "")
                        if rec:
                            st.info(f"**Recommended action:** {rec}", icon="💡")
                        conf = health.get("confidence", "")
                        if conf:
                            st.caption(f"Confidence: {conf.upper()}")

                    # Drill-down history
                    with st.expander("📈 Historical snapshots"):
                        history = get_company_history(report["company_name"], limit=6)
                        if len(history) > 1:
                            df = pd.DataFrame([
                                {
                                    "Date": h["timestamp"][:10],
                                    "Headcount": h["snapshot"]["headcount_current"],
                                    "Status": h["health"]["status"].upper(),
                                    "News": h["snapshot"]["news_count"],
                                }
                                for h in history
                            ])
                            st.dataframe(df, use_container_width=True, hide_index=True)
                        else:
                            st.caption("Run more analyses to build historical trend data.")

                    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)


# ── Portfolio Overview Chart ──────────────────────────────────────────────────

if reports:
    st.markdown('<div class="section-title">📈 Portfolio Headcount Trends</div>', unsafe_allow_html=True)

    trend_data = []
    for company in companies:
        for i, hc in enumerate(company["headcount_history"]):
            trend_data.append({
                "Company": company["name"],
                "Month": f"M{i+1}",
                "Headcount": hc,
                "Sector": company["sector"]
            })

    df_trend = pd.DataFrame(trend_data)
    fig = px.line(
        df_trend, x="Month", y="Headcount", color="Company",
        template="plotly_dark",
        color_discrete_sequence=px.colors.qualitative.Set2,
        height=380,
    )
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#080e1a",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        margin=dict(l=0, r=0, t=40, b=0),
        xaxis=dict(gridcolor="#1a2540"),
        yaxis=dict(gridcolor="#1a2540"),
        font=dict(family="Inter", color="#94a3b8"),
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    # Status distribution donut
    col_a, col_b = st.columns([1, 2])
    with col_a:
        st.markdown('<div class="section-title">📊 Status Distribution</div>', unsafe_allow_html=True)
        if reports:
            statuses = [r["health"]["status"] for r in reports]
            status_counts = {s: statuses.count(s) for s in ["green", "yellow", "red"]}
            fig_pie = go.Figure(go.Pie(
                labels=["Healthy", "Watch", "Urgent"],
                values=[status_counts["green"], status_counts["yellow"], status_counts["red"]],
                hole=0.6,
                marker_colors=["#16a34a", "#ca8a04", "#dc2626"],
                textfont=dict(size=13, color="white"),
            ))
            fig_pie.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                showlegend=True,
                legend=dict(font=dict(color="#94a3b8")),
                margin=dict(l=0, r=0, t=0, b=0),
                height=250,
                font=dict(family="Inter"),
            )
            st.plotly_chart(fig_pie, use_container_width=True, config={"displayModeBar": False})

    with col_b:
        st.markdown('<div class="section-title">🔴 Action Required</div>', unsafe_allow_html=True)
        urgent = [r for r in reports if r["health"]["status"] in ("red", "yellow")]
        if urgent:
            for r in urgent:
                meta = get_company_meta(r["company_name"])
                st.markdown(f"""
                <div style="background:#111827;border:1px solid #1f2937;border-radius:10px;
                            padding:12px 16px;margin-bottom:8px;display:flex;align-items:center;gap:14px;">
                  <div>{STATUS_EMOJI[r['health']['status']]}</div>
                  <div>
                    <div style="font-weight:600;color:#f0f4ff;">{r['company_name']}</div>
                    <div style="font-size:0.78rem;color:#94a3b8;">{r['health']['recommended_action']}</div>
                  </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.success("No urgent actions — portfolio looks healthy!", icon="✅")