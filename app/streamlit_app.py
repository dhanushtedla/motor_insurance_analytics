"""Motor Insurance Analytics Dashboard.   Run:  streamlit run app/streamlit_app.py

Pages: Executive Overview | Policy | Claims | Customer | Vehicle | Premium & Risk |
       Insights & Recommendations | Live Fleet Simulation

HOW FILTERS WORK
  * an EMPTY filter means "show everything" (this fixes the old "No claims for the selected filters" problem)
  * policy-side filters (type, status, vehicle, state/city, policy date) also limit the claims of those policies
  * claim-side filters (status, type, severity, claim date) limit the claims
  * every KPI, chart, insight and simulation uses the filtered data
"""
import html
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))                    # lets "from src import ..." work when started by streamlit

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from run_pipeline import run_pipeline, CLEANED_DIR
from src import insights as ins
from src import insurance_analysis as ia
from src import simulation as sim
from src import visualization as viz

PAGES = ["📊 Executive Overview", "📄 Policy Analysis", "🧾 Claims Analysis", "👤 Customer Analysis",
         "🚗 Vehicle Analysis", "💰 Premium & Risk", "💡 Insights & Recommendations", "📡 Live Fleet Simulation"]
LIST_FILTERS = {                                  # session key -> (label, column)
    "f_policy_type": ("Policy Type", "policy_type"),
    "f_policy_status": ("Policy Status", "policy_status"),
    "f_claim_status": ("Claim Status", "claim_status"),
    "f_claim_type": ("Claim Type", "claim_type"),
    "f_vehicle_type": ("Vehicle Type", "vehicle_type"),
    "f_vehicle_make": ("Vehicle Make", "vehicle_make"),
    "f_state": ("State", "state"),
    "f_city": ("City", "city"),
    "f_severity": ("Damage Severity", "damage_severity"),
}
AREA_COLORS = {"Portfolio": "#1f77b4", "Claims": "#d62728", "Premium": "#2ca02c", "Customer": "#9467bd",
               "Vehicle": "#ff7f0e", "Risk": "#c0392b"}


# ---------------------------------------------------------------------------
# small display helpers
# ---------------------------------------------------------------------------
def show_chart(fig):
    """Show a Plotly chart full width (works on old and new Streamlit versions)."""
    key = "chart_" + str(fig.layout.title.text)
    try:
        st.plotly_chart(fig, width="stretch", key=key)
    except Exception:
        st.plotly_chart(fig, use_container_width=True, key=key)


def show_table(df):
    """Show a DataFrame full width with 2-decimal numbers."""
    df = df.round(2)
    try:
        st.dataframe(df, hide_index=True, width="stretch")
    except Exception:
        st.dataframe(df, hide_index=True, use_container_width=True)


def kpi_row(items):
    """Show a row of KPI cards. items = [(label, value_text), ...]"""
    for column, (label, value) in zip(st.columns(len(items)), items):
        column.metric(label, value)


def render_insight_card(card):
    """Show one insight with the 4 required parts: PATTERN, EVIDENCE, BUSINESS MEANING, RECOMMENDATION."""
    color = AREA_COLORS.get(card["area"], "#555")
    e = html.escape
    st.markdown(
        f"""<div style="border-left:6px solid {color};background:#f7f9fc;padding:10px 16px;margin:10px 0;border-radius:6px;color:#222">
        <div style="font-size:0.75rem;color:{color};font-weight:700">PATTERN · {e(card['area']).upper()}</div>
        <div style="font-weight:600;margin-bottom:6px">{e(card['pattern'])}</div>
        <div><b>EVIDENCE:</b> {e(card['evidence'])}</div>
        <div><b>BUSINESS MEANING:</b> {e(card['business_meaning'])}</div>
        <div><b>RECOMMENDATION:</b> {e(card['recommendation'])}</div></div>""",
        unsafe_allow_html=True)


def render_cards(cards, limit=None):
    """Show a list of insight cards (or a short note when there is nothing to show)."""
    if not cards:
        st.info("Not enough data in the current filter to calculate patterns.")
    for card in cards[:limit]:
        render_insight_card(card)


def no_claims_message():
    """Friendly message when the filters leave no claims."""
    st.info("No claims match the current filters. Click **Reset filters** in the sidebar or widen the date range.")


def to_csv_bytes(df):
    """DataFrame -> CSV bytes for download buttons."""
    return df.to_csv(index=False).encode("utf-8")


# ---------------------------------------------------------------------------
# data + filters
# ---------------------------------------------------------------------------
@st.cache_data(show_spinner="Loading data...")
def load_dashboard_data():
    """Load cleaned tables (running the pipeline first if they do not exist) and build the master tables."""
    names = ["customers", "vehicles", "policies", "claims", "payments"]
    if not all((CLEANED_DIR / f"{n}_cleaned.csv").exists() for n in names):
        run_pipeline()
    data = {n: pd.read_csv(CLEANED_DIR / f"{n}_cleaned.csv") for n in names}
    for table, columns in {"policies": ["policy_start_date", "policy_end_date"],
                           "claims": ["claim_date", "accident_date", "approval_date", "settlement_date"],
                           "payments": ["payment_date"]}.items():
        for col in columns:
            data[table][col] = pd.to_datetime(data[table][col], errors="coerce")
    return ia.build_policy_master(data), ia.build_claims_master(data), data["payments"]


def _reset_filters(defaults):
    """Callback of the Reset button: empty every list filter and restore the full date ranges."""
    for key in LIST_FILTERS:
        st.session_state[key] = []
    st.session_state["f_pol_dates"] = defaults["pol"]
    st.session_state["f_clm_dates"] = defaults["clm"]


def _date_filter(label, key, low, high):
    """A date-range input that never breaks when the user has picked only one date."""
    picked = st.sidebar.date_input(label, min_value=low, max_value=high, key=key)
    if isinstance(picked, (list, tuple)):
        if len(picked) == 2:
            return picked[0], picked[1]
        if len(picked) == 1:
            return picked[0], high
        return low, high
    return picked, high


def show_sidebar_filters(pm, cm):
    """Draw all sidebar filters and return the chosen values as a dictionary."""
    st.sidebar.header("🔎 Filters")
    st.sidebar.caption("Empty filter = show everything.")
    low_p, high_p = pm["policy_start_date"].min().date(), pm["policy_start_date"].max().date()
    low_c, high_c = cm["claim_date"].min().date(), cm["claim_date"].max().date()
    defaults = {"pol": (low_p, high_p), "clm": (low_c, high_c)}
    st.session_state.setdefault("f_pol_dates", defaults["pol"])
    st.session_state.setdefault("f_clm_dates", defaults["clm"])
    st.sidebar.button("↺ Reset filters", on_click=_reset_filters, args=(defaults,))

    # City options depend on the chosen states; remove cities that are no longer valid
    states = st.session_state.get("f_state", [])
    cities = sorted(pm.loc[pm["state"].isin(states), "city"].unique()) if states else sorted(pm["city"].unique())
    st.session_state["f_city"] = [c for c in st.session_state.get("f_city", []) if c in cities]

    sources = {"policy_type": pm, "policy_status": pm, "claim_status": cm, "claim_type": cm,
               "vehicle_type": pm, "vehicle_make": pm, "state": pm, "damage_severity": cm}
    chosen = {}
    for key, (label, column) in LIST_FILTERS.items():
        options = cities if column == "city" else sorted(sources[column][column].dropna().unique())
        chosen[column] = st.sidebar.multiselect(label, options, key=key)

    chosen["policy_dates"] = _date_filter("Policy start date range", "f_pol_dates", low_p, high_p)
    chosen["claim_dates"] = _date_filter("Claim date range", "f_clm_dates", low_c, high_c)
    return chosen


def _isin(df, column, values):
    """Keep rows whose column is in values. Empty list = keep everything."""
    return df if not values else df[df[column].isin(values)]


def apply_filters(pm, cm, payments, f):
    """Apply the sidebar choices and return (policies, claims, payments) for the dashboard."""
    pol = pm
    for column in ["policy_type", "policy_status", "vehicle_type", "vehicle_make", "state", "city"]:
        pol = _isin(pol, column, f[column])
    start, end = f["policy_dates"]
    day = pol["policy_start_date"].dt.date
    pol = pol[(day >= start) & (day <= end)]

    clm = cm[cm["policy_id"].isin(pol["policy_id"])]
    for column in ["claim_status", "claim_type", "damage_severity"]:
        clm = _isin(clm, column, f[column])
    start, end = f["claim_dates"]
    day = clm["claim_date"].dt.date
    clm = clm[(day >= start) & (day <= end)]

    pol = ia.attach_claim_totals(pol, clm)                 # policy claim totals follow the claim filters
    pay = payments[payments["claim_id"].isin(clm["claim_id"])]
    return pol, clm, pay


def show_sidebar_downloads(pol, clm):
    """Download buttons for the filtered data."""
    st.sidebar.divider()
    st.sidebar.subheader("⬇ Download")
    st.sidebar.download_button("Filtered claims (CSV)", to_csv_bytes(clm), "filtered_claims.csv", "text/csv")
    st.sidebar.download_button("Filtered policies (CSV)", to_csv_bytes(pol), "filtered_policies.csv", "text/csv")


# ---------------------------------------------------------------------------
# pages
# ---------------------------------------------------------------------------
def show_overview(pol, clm, pay):
    """Executive Overview: headline KPIs, status charts and top recommendations."""
    st.header("Executive Overview")
    kpi_row([("Total Policies", f"{ia.calculate_total_policies(pol):,}"),
             ("Active Policies", f"{ia.calculate_active_policies(pol):,}"),
             ("Total Premium", ins._money(ia.calculate_total_premium(pol))),
             ("Total Claims", f"{ia.calculate_total_claims(clm):,}")])
    kpi_row([("Total Claim Amount", ins._money(ia.calculate_total_claim_amount(clm))),
             ("Approval Rate", f"{ia.calculate_claim_approval_rate(clm):.1f}%"),
             ("Avg Settlement Days", f"{ia.calculate_average_claim_settlement_days(clm):.1f}"),
             ("Claim-to-Premium", f"{ia.calculate_claim_to_premium_ratio(clm, pol):.2f}")])
    left, right = st.columns(2)
    with left:
        show_chart(viz.plot_policy_status(pol))
    with right:
        show_chart(viz.plot_claim_status(clm))
    left, right = st.columns(2)
    with left:
        show_chart(viz.plot_damage_severity_distribution(clm))
    with right:
        show_chart(viz.plot_monthly_claims(clm))
    st.subheader("Top priorities for management")
    render_cards(ins.generate_business_recommendations({"policies": pol, "claims": clm, "payments": pay}), limit=3)


def show_policy_analysis(pol, clm, pay):
    """Policy Analysis: status, type, premium patterns, monthly trend."""
    st.header("Policy Analysis")
    kpi_row([("Active", f"{ia.calculate_active_policies(pol):,}"), ("Expired", f"{ia.calculate_expired_policies(pol):,}"),
             ("Cancelled", f"{ia.calculate_cancelled_policies(pol):,}"), ("Renewed", f"{ia.calculate_renewed_policies(pol):,}")])
    left, right = st.columns(2)
    with left:
        show_chart(viz.plot_policy_status(pol))
    with right:
        show_chart(viz.plot_policy_type_distribution(pol))
    show_chart(viz.plot_premium_by_policy_type(pol))
    show_chart(viz.plot_monthly_premium_trend(pol))
    st.subheader("Premium by policy type")
    show_table(ia.calculate_premium_by_policy_type(pol))
    render_cards(ins.generate_portfolio_insights({"policies": pol}))


def show_claim_analysis(pol, clm, pay):
    """Claims Analysis: volume, status, type, DAMAGE SEVERITY pies, amount, region and settlement."""
    st.header("Claims Analysis")
    if clm.empty:
        no_claims_message()
        return
    kpi_row([("Total Claims", f"{ia.calculate_total_claims(clm):,}"), ("Approved", f"{ia.calculate_approved_claims(clm):,}"),
             ("Rejected", f"{ia.calculate_rejected_claims(clm):,}"), ("Pending", f"{ia.calculate_pending_claims(clm):,}")])
    kpi_row([("Total Claim Amount", ins._money(ia.calculate_total_claim_amount(clm))),
             ("Average Claim", ins._money(ia.calculate_average_claim_amount(clm))),
             ("Avg Processing Days", f"{ia.calculate_average_claim_processing_days(clm):.1f}"),
             ("Avg Settlement Days", f"{ia.calculate_average_claim_settlement_days(clm):.1f}")])

    st.subheader("How much damage is there?")
    left, right = st.columns(2)
    with left:
        show_chart(viz.plot_damage_severity_distribution(clm, by="count"))
    with right:
        show_chart(viz.plot_damage_severity_distribution(clm, by="amount"))
    show_table(ia.analyze_damage_severity(clm))

    left, right = st.columns(2)
    with left:
        show_chart(viz.plot_claim_status(clm))
    with right:
        show_chart(viz.plot_claim_type_distribution(clm))
    left, right = st.columns(2)
    with left:
        show_chart(viz.plot_claim_amount_distribution(clm))
    with right:
        show_chart(viz.plot_monthly_claims(clm))
    left, right = st.columns(2)
    with left:
        show_chart(viz.plot_claims_by_region(clm))
    with right:
        show_chart(viz.plot_claim_severity_by_region(clm))
    left, right = st.columns(2)
    with left:
        show_chart(viz.plot_average_settlement_time(clm, by="claim_type"))
    with right:
        show_chart(viz.plot_average_settlement_time(clm, by="damage_severity"))
    left, right = st.columns(2)
    with left:
        show_chart(viz.plot_payment_status(pay))
    with right:
        show_chart(viz.plot_payment_method(pay))
    with st.expander("Region x claim type heatmap (multivariate)"):
        show_chart(viz.plot_region_type_severity_heatmap(clm))
    render_cards(ins.generate_claim_insights({"policies": pol, "claims": clm, "payments": pay}))


def show_customer_analysis(pol, clm, pay):
    """Customer Analysis: age, gender, occupation, state - claim and premium behaviour."""
    st.header("Customer Analysis")
    if clm.empty:
        no_claims_message()
        return
    kpi_row([("Customers (with policies)", f"{pol['customer_id'].nunique():,}"),
             ("Customers with claims", f"{clm['customer_id'].nunique():,}"),
             ("Avg customer age", f"{pol['age'].mean():.1f}"),
             ("Claims per customer", f"{len(clm) / max(clm['customer_id'].nunique(), 1):.2f}")])
    segment = st.selectbox("Compare customers by", ["age_group", "gender", "occupation", "state"], key="cust_segment")
    claims_by = ia.analyze_customer_claims(clm, segment)
    prem_by = ia.analyze_customer_premium(pol, segment)
    left, right = st.columns(2)
    with left:
        show_chart(viz.plot_segment_bar(claims_by, segment, "total_claim_amount", f"Total Claim Amount by {segment}", "Total claim amount (₹)"))
    with right:
        show_chart(viz.plot_segment_bar(claims_by, segment, "avg_claim_amount", f"Average Claim Amount by {segment}", "Average claim (₹)"))
    left, right = st.columns(2)
    with left:
        show_chart(viz.plot_segment_bar(prem_by, segment, "average_premium", f"Average Premium by {segment}", "Average premium (₹)"))
    with right:
        show_chart(viz.plot_customer_age_vs_claim_amount(clm))
    st.subheader(f"Claim summary by {segment}")
    show_table(claims_by)
    render_cards(ins.generate_customer_insights({"policies": pol, "claims": clm, "payments": pay}))


def show_vehicle_analysis(pol, clm, pay):
    """Vehicle Analysis: make, fuel type, vehicle age and vehicle type claim patterns."""
    st.header("Vehicle Analysis")
    if clm.empty:
        no_claims_message()
        return
    if pol["vehicle_type"].nunique() <= 1:
        st.caption(f"All vehicles in the current data are of one type ({pol['vehicle_type'].iloc[0]}), "
                   "so compare make, fuel type and vehicle age instead.")
    kpi_row([("Vehicles insured", f"{pol['vehicle_id'].nunique():,}"),
             ("Avg vehicle age", f"{pol['vehicle_age'].mean():.1f} yrs"),
             ("Avg vehicle value", ins._money(pol["vehicle_value"].mean())),
             ("Claims per policy", f"{pol['claim_count'].sum() / max(len(pol), 1):.2f}")])
    segment = st.selectbox("Compare vehicles by", ["vehicle_make", "fuel_type", "vehicle_age_group", "vehicle_model", "vehicle_type"],
                           key="veh_segment")
    left, right = st.columns(2)
    with left:
        show_chart(viz.plot_claim_amount_by_vehicle_type(clm, by=segment))
    with right:
        show_chart(viz.plot_vehicle_type_claim_performance(pol, by=segment))
    left, right = st.columns(2)
    with left:
        show_chart(viz.plot_vehicle_age_vs_claim_amount(clm))
    with right:
        show_chart(viz.plot_segment_bar(ia.analyze_vehicle_risk_patterns(pol, segment), segment,
                                        "claim_frequency", f"Claims per Policy by {segment}", "Claims per policy"))
    st.subheader(f"Claim cost by {segment}")
    show_table(ia.analyze_vehicle_claims(clm, segment))
    st.subheader(f"Risk by {segment}")
    show_table(ia.analyze_vehicle_risk_patterns(pol, segment))
    render_cards(ins.generate_vehicle_insights({"policies": pol, "claims": clm, "payments": pay}))


def show_premium_analysis(pol, clm, pay):
    """Premium & Risk: premium, claim-to-premium ratio, coverage and risk segments."""
    st.header("Premium & Risk")
    if clm.empty:
        no_claims_message()
        return
    kpi_row([("Total Premium", ins._money(ia.calculate_total_premium(pol))),
             ("Average Premium", ins._money(ia.calculate_average_premium(pol))),
             ("Average Coverage", ins._money(ia.calculate_average_coverage(pol)))])
    kpi_row([("Claim-to-Premium", f"{ia.calculate_claim_to_premium_ratio(clm, pol):.2f}"),
             ("Claim-to-Coverage", f"{ia.calculate_claim_to_coverage_ratio(clm, pol):.4f}"),
             ("Paid Claim Ratio", f"{ia.calculate_paid_claim_ratio(pay, clm):.2f}")])
    st.caption("Claim-to-premium = total claim amount requested / total premium collected. Above 1.0 means claims are bigger than premium.")
    left, right = st.columns(2)
    with left:
        show_chart(viz.plot_claim_to_premium_by_policy_type(pol))
    with right:
        show_chart(viz.plot_premium_by_policy_type(pol))
    show_chart(viz.plot_segment_risk_heatmap(pol))
    left, right = st.columns(2)
    with left:
        show_chart(viz.plot_policy_vehicle_sunburst(clm))
    with right:
        show_chart(viz.plot_monthly_premium_trend(pol))
    st.subheader("Highest-risk segments (policy type x vehicle make)")
    seg = ia.analyze_vehicle_risk_patterns(pol.assign(segment=pol["policy_type"] + " + " + pol["vehicle_make"]), "segment")
    show_table(seg[seg["policies"] >= ins.MIN_GROUP_SIZE].head(10))
    st.subheader("Statistics (mean, median, mode, variance, std)")
    show_table(ia.calculate_descriptive_statistics(pol, clm))
    render_cards(ins.generate_risk_patterns({"policies": pol, "claims": clm, "payments": pay}))
    render_cards(ins.generate_premium_insights({"policies": pol, "claims": clm, "payments": pay}))


def show_insights(pol, clm, pay):
    """Insights & Recommendations: every pattern with evidence, meaning and action."""
    st.header("Insights & Recommendations")
    data = {"policies": pol, "claims": clm, "payments": pay}
    st.subheader("🎯 Top 5 recommended actions")
    render_cards(ins.generate_business_recommendations(data))
    for title, func in [("Portfolio", ins.generate_portfolio_insights), ("Claims", ins.generate_claim_insights),
                        ("Premium", ins.generate_premium_insights), ("Customers", ins.generate_customer_insights),
                        ("Vehicles", ins.generate_vehicle_insights), ("Risk patterns", ins.generate_risk_patterns)]:
        with st.expander(f"{title} insights"):
            render_cards(func(data))
    st.divider()
    if st.button("📝 Prepare business report for the current filters"):
        st.session_state["report_md"] = ins.generate_business_report(data, title="Motor Insurance Report (filtered view)")
    if "report_md" in st.session_state:
        st.download_button("⬇ Download business report (Markdown)", st.session_state["report_md"],
                           "business_report.md", "text/markdown")


# ---------------------------------------------------------------------------
# live simulation page
# ---------------------------------------------------------------------------
def build_fleet_map(fleet):
    """Map of India with moving vehicles (🚗) and accident spots (💥)."""
    fig = go.Figure()
    lon_line, lat_line = [], []
    for _, v in fleet.iterrows():                               # faint route lines
        lon_line += [v["start_lon"], v["dest_lon"], None]
        lat_line += [v["start_lat"], v["dest_lat"], None]
    fig.add_trace(go.Scattergeo(lon=lon_line, lat=lat_line, mode="lines", line=dict(width=0.6, color="#9db7d5"),
                                hoverinfo="skip", showlegend=False))
    fig.add_trace(go.Scattergeo(lon=[c[1] for c in sim.CITY_COORDS.values()], lat=[c[0] for c in sim.CITY_COORDS.values()],
                                mode="markers", marker=dict(size=4, color="#666"), text=list(sim.CITY_COORDS.keys()),
                                hoverinfo="text", showlegend=False))
    for status, emoji, size, color, label in [("Moving", "🚗", 14, "#2ca02c", "Moving"), ("Accident", "💥", 22, "#d62728", "Accident")]:
        part = fleet[fleet["status"] == status]
        fig.add_trace(go.Scattergeo(
            lon=part["lon"], lat=part["lat"], mode="markers+text", text=[emoji] * len(part), textfont=dict(size=size),
            marker=dict(size=6, color=color), name=label, textposition="middle center",
            hovertext=part["make"] + " " + part["model"] + " | " + part["policy_type"] + " | heading to " + part["dest"],
            hoverinfo="text"))
    fig.update_geos(scope="asia", lataxis_range=[6, 36], lonaxis_range=[67, 98], showland=True, landcolor="#f3f1ea",
                    showocean=True, oceancolor="#e6f0fa", showcountries=True, countrycolor="#b0b0b0", projection_type="mercator")
    fig.update_layout(height=560, margin=dict(l=0, r=0, t=10, b=0), legend=dict(orientation="h", y=0.02), title_text="Live fleet map")
    return fig


def _start_simulation(pol, size):
    """Create a fresh simulation state in st.session_state."""
    rng = np.random.default_rng(42)
    st.session_state["sim"] = {"fleet": sim.build_fleet(pol, size, rng), "events": [], "tick": 0, "rng": rng,
                               "size": size, "sig": (len(pol),), "start": pd.Timestamp.today().normalize()}


def show_live_simulation(pol, clm):
    """Live Fleet Simulation: vehicles move on the map and accidents become live claim events."""
    st.header("📡 Live Fleet Simulation")
    st.caption("Real active policies from your data are placed on the road. Accidents happen with the probabilities, "
               "severity mix and claim amounts found in your historical claims. 1 second = 1 simulated day. "
               "This is a simulation for training - not live telematics.")
    profile = sim.learn_risk_profile(pol, clm)
    if profile is None or pol.empty:
        no_claims_message()
        return

    c1, c2, c3, c4 = st.columns([2, 2, 1, 1])
    size = c1.slider("Vehicles on the road", 20, 300, 120, 10, key="sim_size")
    rate = c2.slider("Accident speed-up (x real rate)", 1, 50, 5, key="sim_rate",
                     help="1 = real historical frequency. Higher = more accidents so you can watch events quickly.")
    running = c3.toggle("▶ Run live", key="sim_running")
    if c4.button("Reset"):
        st.session_state.pop("sim", None)

    state = st.session_state.get("sim")
    if state is None or state["size"] != size or state["sig"] != (len(pol),):
        _start_simulation(pol, size)

    @st.fragment(run_every=1 if running else None)
    def live_panel():
        s = st.session_state["sim"]
        if running:                                                 # advance one day per refresh
            s["tick"] += 1
            s["fleet"], new_events = sim.step_fleet(s["fleet"], profile, s["rng"], s["tick"], s["start"], rate)
            s["events"].extend(new_events)
        events = pd.DataFrame(s["events"])
        fleet = s["fleet"]

        exposure = events["claim_amount"].sum() if len(events) else 0
        payout = events["expected_payout"].sum() if len(events) else 0
        review = int(events["action"].str.startswith("REVIEW").sum()) if len(events) else 0
        kpi_row([("Simulated day", f"{s['tick']}"), ("Vehicles moving", f"{int((fleet['status'] == 'Moving').sum())} / {len(fleet)}"),
                 ("Accidents so far", f"{len(events)}"), ("Claim exposure", ins._money(exposure)),
                 ("Expected payout", ins._money(payout)), ("Flagged for review", f"{review}")])
        if len(events):
            last = events.iloc[-1]
            st.warning(f"🚨 NEW CLAIM (FNOL): {last['make']} {last['policy_type']} near {last['near_city']} - "
                       f"{last['claim_type']}, {last['severity']} damage, estimated ₹{last['claim_amount']:,}. Action: {last['action']}")
        try:
            st.plotly_chart(build_fleet_map(fleet), width="stretch", key="sim_map")
        except Exception:
            st.plotly_chart(build_fleet_map(fleet), use_container_width=True, key="sim_map")
        if len(events):
            left, right = st.columns([3, 2])
            with left:
                st.subheader("Live claim feed")
                show_table(events.tail(12).iloc[::-1])
            with right:
                st.subheader("Accidents by severity")
                counts = events["severity"].value_counts()
                pie = go.Figure(go.Pie(labels=counts.index, values=counts.values, hole=0.4,
                                       marker=dict(colors=[viz.SEVERITY_COLORS.get(k, "#999") for k in counts.index])))
                pie.update_layout(height=300, margin=dict(l=0, r=0, t=10, b=0))
                try:
                    st.plotly_chart(pie, width="stretch", key="sim_pie")
                except Exception:
                    st.plotly_chart(pie, use_container_width=True, key="sim_pie")
            st.download_button("⬇ Download simulated claim events (CSV)", to_csv_bytes(events), "simulated_claim_events.csv", "text/csv", key="sim_dl")
        else:
            st.info("Switch on **▶ Run live** to start the simulation. Raise the speed-up slider to see accidents sooner.")

    live_panel()


# ---------------------------------------------------------------------------
def main():
    """Page set-up, sidebar filters, page navigation."""
    st.set_page_config(page_title="Motor Insurance Analytics", page_icon="🚗", layout="wide")
    st.title("🚗 Motor Insurance Analytics Dashboard")

    pm, cm, payments = load_dashboard_data()
    filters = show_sidebar_filters(pm, cm)
    pol, clm, pay = apply_filters(pm, cm, payments, filters)
    show_sidebar_downloads(pol, clm)

    if pol.empty:
        st.warning("No policies match the current filters. Click **Reset filters** in the sidebar.")
        return
    st.caption(f"Showing {len(pol):,} policies · {len(clm):,} claims · {len(pay):,} payments (after filters)")

    page = st.radio("Page", PAGES, horizontal=True, label_visibility="collapsed", key="page")
    pages = {PAGES[0]: show_overview, PAGES[1]: show_policy_analysis, PAGES[2]: show_claim_analysis,
             PAGES[3]: show_customer_analysis, PAGES[4]: show_vehicle_analysis, PAGES[5]: show_premium_analysis,
             PAGES[6]: show_insights}
    if page == PAGES[7]:
        show_live_simulation(pol, clm)
    else:
        pages[page](pol, clm, pay)


if __name__ == "__main__":
    main()
