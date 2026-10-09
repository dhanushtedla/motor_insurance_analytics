"""Chart functions. Each one receives a DataFrame, does only the aggregation it needs,
builds a Plotly chart with a title and axis labels, and RETURNS the figure
(Streamlit shows it with st.plotly_chart, a notebook shows it with fig.show()).
"""
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

COLORS = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b", "#17becf"]
SEVERITY_COLORS = {"Low": "#2ca02c", "Medium": "#ffbf00", "High": "#d62728"}
STATUS_COLORS = {"Approved": "#2ca02c", "Settled": "#1f77b4", "Pending": "#ffbf00", "Rejected": "#d62728"}


def _empty_figure(title):
    """A blank chart with a message, used when the filters leave no data."""
    fig = go.Figure()
    fig.update_layout(title=title, xaxis={"visible": False}, yaxis={"visible": False},
                      annotations=[{"text": "No data for the selected filters", "showarrow": False,
                                    "font": {"size": 16}}])
    return fig


def _finish(fig, height=380):
    """Common layout for every chart."""
    fig.update_layout(height=height, margin=dict(l=20, r=20, t=60, b=40), legend_title_text="")
    return fig


def _donut(df, column, title, color_map=None):
    """Donut chart of how many rows fall in each value of one column."""
    counts = df[column].value_counts().rename_axis(column).reset_index(name="count")
    fig = px.pie(counts, names=column, values="count", hole=0.45, title=title,
                 color=column, color_discrete_map=color_map, color_discrete_sequence=COLORS)
    fig.update_traces(textinfo="percent+label")
    return _finish(fig)


# ------------------------------- policy charts -------------------------------
def plot_policy_status(policies):
    """How many policies are Active / Expired / Cancelled / Renewed."""
    if policies.empty:
        return _empty_figure("Policy Status")
    return _donut(policies, "policy_status", "Policy Status Share")


def plot_policy_type_distribution(policies):
    """Number of policies of each policy type."""
    if policies.empty:
        return _empty_figure("Policy Types")
    return _donut(policies, "policy_type", "Policy Type Distribution")


def plot_premium_by_policy_type(policies):
    """Total premium for every policy type (label shows the average premium)."""
    if policies.empty:
        return _empty_figure("Premium by Policy Type")
    g = policies.groupby("policy_type").agg(total=("premium_amount", "sum"), avg=("premium_amount", "mean")).reset_index()
    fig = px.bar(g, x="policy_type", y="total", text=g["avg"].map(lambda v: f"Avg ₹{v:,.0f}"),
                 title="Total Premium by Policy Type", labels={"policy_type": "Policy type", "total": "Total premium (₹)"},
                 color="policy_type", color_discrete_sequence=COLORS)
    return _finish(fig)


def plot_monthly_premium_trend(policies):
    """Premium written per month (by policy start date)."""
    if policies.empty:
        return _empty_figure("Monthly Premium Trend")
    g = (policies.assign(month=pd.to_datetime(policies["policy_start_date"]).dt.to_period("M").dt.to_timestamp())
         .groupby("month")["premium_amount"].sum().reset_index())
    fig = px.line(g, x="month", y="premium_amount", markers=True, title="Monthly Premium Trend",
                  labels={"month": "Month", "premium_amount": "Premium (₹)"})
    return _finish(fig)


# ------------------------------- claim charts -------------------------------
def plot_monthly_claims(claims):
    """Number of claims registered each month."""
    if claims.empty:
        return _empty_figure("Monthly Claims")
    g = (claims.assign(month=pd.to_datetime(claims["claim_date"]).dt.to_period("M").dt.to_timestamp())
         .groupby("month").agg(claims=("claim_id", "count")).reset_index())
    fig = px.line(g, x="month", y="claims", markers=True, title="Monthly Claims Registered",
                  labels={"month": "Month", "claims": "Number of claims"})
    return _finish(fig)


def plot_claim_status(claims):
    """Pending / Approved / Rejected / Settled claims."""
    if claims.empty:
        return _empty_figure("Claim Status")
    return _donut(claims, "claim_status", "Claim Status Share", STATUS_COLORS)


def plot_claim_type_distribution(claims):
    """Number of claims for each claim type."""
    if claims.empty:
        return _empty_figure("Claim Types")
    g = claims["claim_type"].value_counts().rename_axis("claim_type").reset_index(name="claims")
    fig = px.bar(g, x="claims", y="claim_type", orientation="h", title="Claims by Claim Type",
                 labels={"claims": "Number of claims", "claim_type": "Claim type"}, text="claims",
                 color="claim_type", color_discrete_sequence=COLORS)
    fig.update_layout(yaxis={"categoryorder": "total ascending"}, showlegend=False)
    return _finish(fig)


def plot_claim_amount_distribution(claims):
    """Histogram of claim amounts (shows the skew: many small claims, few huge ones)."""
    if claims.empty:
        return _empty_figure("Claim Amount Distribution")
    fig = px.histogram(claims, x="claim_amount", nbins=40, title="Claim Amount Distribution",
                       labels={"claim_amount": "Claim amount (₹)"}, color_discrete_sequence=[COLORS[0]])
    fig.update_layout(yaxis_title="Number of claims")
    return _finish(fig)


def plot_damage_severity_distribution(claims, by="count"):
    """PIE chart of damage severity. by='count' -> number of claims, by='amount' -> money."""
    if claims.empty:
        return _empty_figure("Damage Severity")
    if by == "amount":
        g = claims.groupby("damage_severity")["claim_amount"].sum().reset_index(name="value")
        title = "Claim AMOUNT by Damage Severity"
    else:
        g = claims["damage_severity"].value_counts().reset_index(name="value")
        title = "Number of Claims by Damage Severity"
    fig = px.pie(g, names="damage_severity", values="value", title=title, hole=0.0,
                 color="damage_severity", color_discrete_map=SEVERITY_COLORS)
    fig.update_traces(textinfo="percent+label")
    return _finish(fig)


def plot_claim_amount_by_vehicle_type(claims, by="vehicle_type"):
    """Average and total claim amount for each vehicle group (vehicle_type, vehicle_make, fuel_type)."""
    if claims.empty or by not in claims.columns:
        return _empty_figure("Claim Amount by Vehicle")
    g = claims.groupby(by).agg(total=("claim_amount", "sum"), avg=("claim_amount", "mean")).reset_index()
    label = by.replace("_", " ").title()
    fig = px.bar(g, x=by, y="total", text=g["avg"].map(lambda v: f"Avg ₹{v:,.0f}"),
                 title=f"Claim Amount by {label}", labels={by: label, "total": "Total claim amount (₹)"},
                 color=by, color_discrete_sequence=COLORS)
    return _finish(fig)


def plot_payment_status(payments):
    """Share of payments by status (Completed, Pending ...)."""
    if payments.empty:
        return _empty_figure("Payment Status")
    return _donut(payments, "payment_status", "Payment Status")


def plot_payment_method(payments):
    """Share of payments by payment method (UPI, Bank Transfer ...)."""
    if payments.empty:
        return _empty_figure("Payment Method")
    return _donut(payments, "payment_method", "Payments by Method")


# ------------------------------- region charts -------------------------------
def plot_claims_by_region(claims, level="state"):
    """Number of claims per state or city (claim frequency)."""
    if claims.empty:
        return _empty_figure("Claims by Region")
    g = claims.groupby(level).agg(claims=("claim_id", "count")).reset_index().sort_values("claims").tail(15)
    fig = px.bar(g, x="claims", y=level, orientation="h", title=f"Claims by {level.title()} (top 15)",
                 labels={"claims": "Number of claims", level: level.title()}, color="claims",
                 color_continuous_scale="Blues")
    return _finish(fig, 450)


def plot_claim_severity_by_region(claims, level="state"):
    """Average claim amount per state or city (claim severity)."""
    if claims.empty:
        return _empty_figure("Claim Severity by Region")
    g = claims.groupby(level).agg(avg=("claim_amount", "mean")).reset_index().sort_values("avg").tail(15)
    fig = px.bar(g, x="avg", y=level, orientation="h", title=f"Average Claim Amount by {level.title()} (top 15)",
                 labels={"avg": "Average claim amount (₹)", level: level.title()}, color="avg",
                 color_continuous_scale="Reds")
    return _finish(fig, 450)


def plot_region_type_severity_heatmap(claims):
    """Multivariate: average claim amount for every state x claim type."""
    if claims.empty:
        return _empty_figure("Region x Claim Type")
    pivot = claims.pivot_table(index="state", columns="claim_type", values="claim_amount", aggfunc="mean")
    fig = px.imshow(pivot, aspect="auto", color_continuous_scale="YlOrRd",
                    title="Average Claim Amount: State x Claim Type",
                    labels={"color": "Avg claim (₹)", "x": "Claim type", "y": "State"})
    return _finish(fig, 480)


# ------------------------------ settlement / risk ------------------------------
def plot_average_settlement_time(claims, by="claim_type"):
    """Average days from claim date to settlement date for each group."""
    if claims.empty:
        return _empty_figure("Settlement Time")
    days = (pd.to_datetime(claims["settlement_date"]) - pd.to_datetime(claims["claim_date"])).dt.days
    g = claims.assign(days=days).dropna(subset=["days"]).groupby(by).agg(days=("days", "mean")).reset_index()
    if g.empty:
        return _empty_figure("Average Settlement Time")
    fig = px.bar(g, x=by, y="days", text=g["days"].round(1), title=f"Average Settlement Days by {by.replace('_', ' ').title()}",
                 labels={by: by.replace("_", " ").title(), "days": "Average days to settle"},
                 color=by, color_discrete_sequence=COLORS)
    return _finish(fig)


def plot_claim_to_premium_by_policy_type(policies):
    """Claim cost / premium for each policy type. Above 1.0 means claims cost more than premium collected."""
    if policies.empty:
        return _empty_figure("Claim-to-Premium")
    g = policies.groupby("policy_type").agg(prem=("premium_amount", "sum"), clm=("claim_amount_total", "sum")).reset_index()
    g["ratio"] = g["clm"] / g["prem"]
    fig = px.bar(g, x="policy_type", y="ratio", text=g["ratio"].round(2), title="Claim-to-Premium Ratio by Policy Type",
                 labels={"policy_type": "Policy type", "ratio": "Claim cost / premium"},
                 color="ratio", color_continuous_scale="RdYlGn_r")
    fig.add_hline(y=1.0, line_dash="dash", annotation_text="Break-even (1.0)")
    return _finish(fig)


def plot_vehicle_age_vs_claim_amount(claims):
    """Average claim amount for each vehicle age (bubble size = number of claims)."""
    if claims.empty:
        return _empty_figure("Vehicle Age vs Claim Amount")
    g = claims.groupby("vehicle_age").agg(avg=("claim_amount", "mean"), n=("claim_id", "count")).reset_index()
    fig = px.scatter(g, x="vehicle_age", y="avg", size="n", title="Vehicle Age vs Average Claim Amount",
                     labels={"vehicle_age": "Vehicle age (years)", "avg": "Average claim amount (₹)", "n": "Claims"})
    fig.add_trace(go.Scatter(x=g["vehicle_age"], y=g["avg"], mode="lines", showlegend=False))
    return _finish(fig)


def plot_customer_age_vs_claim_amount(claims):
    """Average claim amount for every customer age group."""
    if claims.empty:
        return _empty_figure("Customer Age vs Claim Amount")
    g = claims.groupby("age_group").agg(avg=("claim_amount", "mean"), n=("claim_id", "count")).reset_index().sort_values("age_group")
    fig = px.bar(g, x="age_group", y="avg", text=g["n"].map(lambda v: f"{v} claims"),
                 title="Customer Age Group vs Average Claim Amount",
                 labels={"age_group": "Customer age group", "avg": "Average claim amount (₹)"},
                 color="avg", color_continuous_scale="Purples")
    return _finish(fig)


def plot_vehicle_type_claim_performance(policies, by="vehicle_make"):
    """Bubble chart: claim frequency (x) vs claim-to-premium ratio (y) for each vehicle group."""
    if policies.empty or by not in policies.columns:
        return _empty_figure("Vehicle Claim Performance")
    g = policies.groupby(by).agg(n=("policy_id", "count"), clm=("claim_count", "sum"),
                                 amt=("claim_amount_total", "sum"), prem=("premium_amount", "sum")).reset_index()
    g["frequency"] = g["clm"] / g["n"]
    g["ratio"] = g["amt"] / g["prem"]
    fig = px.scatter(g, x="frequency", y="ratio", size="n", color=by, text=by,
                     title=f"Claim Performance by {by.replace('_', ' ').title()}",
                     labels={"frequency": "Claims per policy", "ratio": "Claim-to-premium ratio"})
    fig.update_traces(textposition="top center")
    return _finish(fig, 420)


def plot_policy_vehicle_sunburst(claims):
    """Multivariate: policy type -> vehicle make, sized by claim amount."""
    if claims.empty:
        return _empty_figure("Policy Type x Vehicle Make")
    fig = px.sunburst(claims, path=["policy_type", "vehicle_make"], values="claim_amount",
                      title="Claim Amount: Policy Type > Vehicle Make")
    return _finish(fig, 450)


def plot_segment_risk_heatmap(policies, rows="policy_type", cols="vehicle_make"):
    """Claim-to-premium ratio for every combination of two policy groups (finds risky segments)."""
    if policies.empty:
        return _empty_figure("Risk Heatmap")
    g = policies.groupby([rows, cols]).agg(prem=("premium_amount", "sum"), clm=("claim_amount_total", "sum")).reset_index()
    g["ratio"] = g["clm"] / g["prem"]
    pivot = g.pivot(index=rows, columns=cols, values="ratio")
    fig = px.imshow(pivot, text_auto=".2f", aspect="auto", color_continuous_scale="RdYlGn_r",
                    title=f"Claim-to-Premium Ratio: {rows.replace('_', ' ').title()} x {cols.replace('_', ' ').title()}")
    return _finish(fig)


def plot_segment_bar(summary, x, y, title, y_label, color=None):
    """Generic bar chart for any summary table made by the analyze_* functions."""
    if summary is None or summary.empty:
        return _empty_figure(title)
    data = summary.sort_values(x) if x in ("age_group", "vehicle_age_group") else summary
    fig = px.bar(data, x=x, y=y, title=title, text_auto=".3s", color=color or y,
                 labels={x: x.replace("_", " ").title(), y: y_label}, color_continuous_scale="Blues")
    fig.update_layout(coloraxis_showscale=False)
    return _finish(fig)
