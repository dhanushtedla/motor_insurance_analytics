"""Insight and pattern engine.

Every generate_* function receives `data`, a dictionary with the CURRENT (filtered) tables:
    data["policies"]  policy master (with claim_count, claim_amount_total)
    data["claims"]    claims master
    data["payments"]  payments
and returns a list of insight cards. Each card has the 4 required parts:
    pattern, evidence, business_meaning, recommendation  (+ score, area used for ranking)
All numbers are calculated from the data. Nothing is hard-coded.
"""
import pandas as pd

from src import insurance_analysis as ia

MIN_GROUP_SIZE = 50          # ignore tiny groups so one lucky claim does not create a "pattern"


def _money(value):
    """Format a number as Indian rupees."""
    if abs(value) >= 1e7:
        return f"₹{value / 1e7:,.2f} Cr"
    if abs(value) >= 1e5:
        return f"₹{value / 1e5:,.2f} L"
    return f"₹{value:,.0f}"


def _card(area, pattern, evidence, meaning, recommendation, score=0.0):
    """Build one insight card (a plain dictionary)."""
    return {"area": area, "pattern": pattern, "evidence": evidence,
            "business_meaning": meaning, "recommendation": recommendation, "score": float(score)}


def _has_data(data, key):
    """True when data[key] exists and has rows."""
    return key in data and data[key] is not None and len(data[key]) > 0


# ---------------------------------------------------------------------------
def generate_portfolio_insights(data):
    """Patterns about policy status and policy mix."""
    if not _has_data(data, "policies"):
        return []
    pol, cards, n = data["policies"], [], len(data["policies"])
    status = pol["policy_status"].value_counts()

    lost = status.get("Expired", 0) + status.get("Cancelled", 0)
    renewed = status.get("Renewed", 0)
    conversion = 100 * renewed / (renewed + status.get("Expired", 0)) if (renewed + status.get("Expired", 0)) else 0
    cards.append(_card(
        "Portfolio", f"Only {conversion:.1f}% of policies that reached their end date were renewed",
        f"Renewed = {renewed:,}, Expired (not renewed) = {status.get('Expired', 0):,}, Cancelled = {status.get('Cancelled', 0):,} "
        f"out of {n:,} policies. Active policies = {status.get('Active', 0):,} ({100 * status.get('Active', 0) / n:.1f}%).",
        "Every non-renewed policy is premium the insurer has to win again; low renewal means higher acquisition cost.",
        "Contact expired-policy customers early (before end date) with renewal offers; study why policies get cancelled.",
        score=100 - conversion))

    top_type = pol["policy_type"].value_counts()
    share = 100 * top_type.iloc[0] / n
    cards.append(_card(
        "Portfolio", f"{top_type.index[0]} dominates the portfolio with {share:.1f}% of policies",
        f"{top_type.index[0]}: {top_type.iloc[0]:,} policies. " + ", ".join(f"{k}: {v:,}" for k, v in top_type.iloc[1:].items()),
        "A portfolio concentrated in one product depends heavily on that product's claim behaviour.",
        "Check the claim-to-premium ratio of this product before growing it further; consider balancing the mix.",
        score=share / 2))
    return cards


def generate_claim_insights(data):
    """Patterns about claim backlog, rejection, severity, claim types and settlement time."""
    if not _has_data(data, "claims"):
        return []
    clm, cards, n = data["claims"], [], len(data["claims"])

    pending = clm[clm["claim_status"] == "Pending"]
    if len(pending):
        latest = pd.to_datetime(clm["claim_date"]).max()
        age = (latest - pd.to_datetime(pending["claim_date"])).dt.days
        cards.append(_card(
            "Claims", f"{100 * len(pending) / n:.1f}% of claims are still pending",
            f"{len(pending):,} pending claims worth {_money(pending['claim_amount'].sum())}; "
            f"{int((age > 30).sum()):,} of them are older than 30 days (latest claim date in view: {latest:%d %b %Y}).",
            "Pending claims are a liability not yet decided and old ones hurt customer satisfaction.",
            "Prioritise pending claims older than 30 days and check what is delaying approval.",
            score=100 * len(pending) / n))

    rej = clm[clm["claim_status"] == "Rejected"]
    if len(rej):
        by_type = clm.groupby("claim_type")["claim_status"].agg(lambda s: 100 * (s == "Rejected").mean())
        counts = clm["claim_type"].value_counts()
        by_type = by_type[counts[by_type.index] >= MIN_GROUP_SIZE]
        if len(by_type):
            worst = by_type.idxmax()
            overall = 100 * len(rej) / n
            cards.append(_card(
                "Claims", f"{worst} claims are rejected most often ({by_type.max():.1f}% vs {overall:.1f}% overall)",
                f"Rejected claims = {len(rej):,} worth {_money(rej['claim_amount'].sum())}. "
                f"Rejection rate for {worst} = {by_type.max():.1f}%.",
                "A high rejection rate can mean unclear policy terms or possible fraud-screening working well.",
                f"Review rejection reasons for {worst} claims and make sure rejections are consistent and explainable.",
                score=by_type.max() - overall))

    sev = clm.groupby("damage_severity")["claim_amount"].agg(["count", "sum"])
    if "High" in sev.index:
        c_share = 100 * sev.loc["High", "count"] / n
        a_share = 100 * sev.loc["High", "sum"] / sev["sum"].sum()
        cards.append(_card(
            "Claims", f"High-damage claims are {c_share:.1f}% of claims but {a_share:.1f}% of claim cost",
            f"High severity: {int(sev.loc['High', 'count']):,} claims, {_money(sev.loc['High', 'sum'])} of {_money(sev['sum'].sum())} total.",
            "A small group of severe claims drives a disproportionate part of the cost.",
            "Focus inspection, repair-network negotiation and fraud checks on high-severity claims.",
            score=a_share - c_share))

    typ = clm.groupby("claim_type")["claim_amount"].agg(["count", "mean"])
    typ = typ[typ["count"] >= MIN_GROUP_SIZE]
    if len(typ):
        top = typ["mean"].idxmax()
        overall = clm["claim_amount"].mean()
        cards.append(_card(
            "Claims", f"{top} has the highest average claim ({_money(typ['mean'].max())})",
            f"Portfolio average claim = {_money(overall)}; {top} is {typ['mean'].max() / overall:.2f}x that average "
            f"({int(typ.loc[top, 'count']):,} claims).",
            "This claim type is the most expensive each time it happens.",
            f"Review underwriting and settlement limits for {top} claims.",
            score=100 * (typ["mean"].max() / overall - 1)))

    if "settlement_date" in clm.columns:
        days = (pd.to_datetime(clm["settlement_date"]) - pd.to_datetime(clm["claim_date"])).dt.days
        slow = clm.assign(days=days).dropna(subset=["days"]).groupby("claim_type")["days"].agg(["count", "mean"])
        slow = slow[slow["count"] >= MIN_GROUP_SIZE]
        if len(slow):
            worst = slow["mean"].idxmax()
            cards.append(_card(
                "Claims", f"{worst} claims take the longest to settle ({slow['mean'].max():.1f} days)",
                f"Average over all settled claims = {days.mean():.1f} days; fastest type = {slow['mean'].idxmin()} ({slow['mean'].min():.1f} days).",
                "Slow settlement lowers customer trust and can raise complaints.",
                f"Look at the settlement steps for {worst} claims and remove the slowest step.",
                score=slow["mean"].max() - days.mean()))
    return cards


def generate_premium_insights(data):
    """Patterns about premium by policy type, concentration and the monthly trend."""
    if not _has_data(data, "policies"):
        return []
    pol, cards = data["policies"], []
    total = pol["premium_amount"].sum()

    g = pol.groupby("policy_type")["premium_amount"].agg(["count", "sum", "mean"])
    top = g["sum"].idxmax()
    cards.append(_card(
        "Premium", f"{top} brings in the most premium ({100 * g.loc[top, 'sum'] / total:.1f}% of {_money(total)})",
        f"{top}: {_money(g.loc[top, 'sum'])} from {int(g.loc[top, 'count']):,} policies, average {_money(g.loc[top, 'mean'])}. "
        f"Highest average premium = {g['mean'].idxmax()} ({_money(g['mean'].max())}).",
        "Premium income depends on this product, so its pricing accuracy matters most.",
        "Monitor this product's claim ratio monthly and re-price when it drifts above the portfolio average.",
        score=100 * g.loc[top, "sum"] / total / 2))

    sorted_prem = pol["premium_amount"].sort_values(ascending=False)
    top10 = sorted_prem.head(max(1, int(len(sorted_prem) * 0.1))).sum() / total * 100
    cards.append(_card(
        "Premium", f"The top 10% of policies contribute {top10:.1f}% of total premium",
        f"Top 10% = {max(1, int(len(sorted_prem) * 0.1)):,} policies; median premium = {_money(pol['premium_amount'].median())}, "
        f"mean = {_money(pol['premium_amount'].mean())}.",
        "Premium income is concentrated in a smaller set of large policies.",
        "Protect these high-premium customers with renewal care and watch their claim behaviour.",
        score=top10 - 10))

    if "policy_start_month" in pol.columns:
        monthly = pol.groupby("policy_start_month")["premium_amount"].sum().sort_index()
        if len(monthly) >= 12:
            recent, previous = monthly.tail(6).sum(), monthly.iloc[-12:-6].sum()
            if previous:
                change = 100 * (recent / previous - 1)
                direction = "up" if change >= 0 else "down"
                cards.append(_card(
                    "Premium", f"Premium written in the last 6 months is {direction} {abs(change):.1f}% versus the 6 months before",
                    f"Last 6 months = {_money(recent)}, previous 6 months = {_money(previous)}.",
                    "Falling new premium means slower business growth; rising premium means growth that needs matching claims control.",
                    "Find which policy type or region explains the change and respond with sales or pricing action.",
                    score=abs(change)))
    return cards


def generate_customer_insights(data):
    """Patterns about customer age groups, occupation and state."""
    if not (_has_data(data, "policies") and _has_data(data, "claims")):
        return []
    pol, clm, cards = data["policies"], data["claims"], []

    risk = ia.analyze_vehicle_risk_patterns(pol, by="age_group")
    risk = risk[risk["policies"] >= MIN_GROUP_SIZE]
    if len(risk) >= 2:
        top = risk.sort_values("claim_frequency").iloc[-1]
        avg_freq = pol["claim_count"].sum() / len(pol)
        cards.append(_card(
            "Customer", f"Age group {top['age_group']} files the most claims per policy ({top['claim_frequency']:.2f})",
            f"Portfolio average = {avg_freq:.2f} claims per policy; this group has {int(top['policies']):,} policies "
            f"and {int(top['total_claims']):,} claims.",
            "Claim frequency differs by customer age, so age is a useful risk signal.",
            "Test age-based pricing or driver-awareness programmes for this group.",
            score=100 * (top["claim_frequency"] / avg_freq - 1) if avg_freq else 0))

    by_age = ia.analyze_customer_claims(clm, "age_group")
    by_age = by_age[by_age["total_claims"] >= MIN_GROUP_SIZE]
    if len(by_age):
        top = by_age.sort_values("avg_claim_amount").iloc[-1]
        cards.append(_card(
            "Customer", f"Age group {top['age_group']} has the highest average claim ({_money(top['avg_claim_amount'])})",
            f"Overall average claim = {_money(clm['claim_amount'].mean())}; {int(top['total_claims']):,} claims in this group.",
            "Older / younger segments can be more expensive per claim even if they claim less often.",
            "Compare the premium charged to this age group with the claim cost it creates.",
            score=100 * (top["avg_claim_amount"] / clm["claim_amount"].mean() - 1)))

    occ = ia.analyze_customer_claims(clm, "occupation")
    if len(occ):
        top = occ.iloc[0]
        cards.append(_card(
            "Customer", f"{top['occupation']} customers account for {top['share_of_claim_amount_pct']:.1f}% of claim cost",
            f"{top['occupation']}: {int(top['total_claims']):,} claims, {_money(top['total_claim_amount'])}.",
            "Some customer groups contribute a large share of total claim cost.",
            "Check whether this group's share of premium matches its share of claim cost.",
            score=top["share_of_claim_amount_pct"]))
    return cards


def generate_vehicle_insights(data):
    """Patterns about vehicle make, fuel type and vehicle age."""
    if not (_has_data(data, "policies") and _has_data(data, "claims")):
        return []
    pol, clm, cards = data["policies"], data["claims"], []

    make = ia.analyze_vehicle_claims(clm, "vehicle_make")
    pol_share = pol["vehicle_make"].value_counts(normalize=True) * 100
    if len(make):
        top = make.iloc[0]
        p_share = pol_share.get(top["vehicle_make"], 0)
        cards.append(_card(
            "Vehicle", f"{top['vehicle_make']} generates {top['share_of_claim_amount_pct']:.1f}% of claim value "
                       f"but is {p_share:.1f}% of policies",
            f"{top['vehicle_make']}: {int(top['total_claims']):,} claims, {_money(top['total_claim_amount'])}, "
            f"average claim {_money(top['avg_claim_amount'])}.",
            "If claim share is higher than policy share, this make is costing more than its weight in the portfolio.",
            f"Review underwriting and repair costs for {top['vehicle_make']} vehicles.",
            score=abs(top["share_of_claim_amount_pct"] - p_share)))

    fuel = ia.analyze_vehicle_risk_patterns(pol, "fuel_type")
    fuel = fuel[fuel["policies"] >= MIN_GROUP_SIZE]
    if len(fuel) >= 2:
        top = fuel.iloc[0]
        cards.append(_card(
            "Vehicle", f"{top['fuel_type']} vehicles have the highest claim-to-premium ratio ({top['claim_to_premium_ratio']:.2f})",
            f"Lowest = {fuel.iloc[-1]['fuel_type']} ({fuel.iloc[-1]['claim_to_premium_ratio']:.2f}). "
            f"{top['fuel_type']} has {int(top['policies']):,} policies and {top['claim_frequency']:.2f} claims per policy.",
            "Fuel type changes repair cost and claim cost, so premium should reflect it.",
            f"Check whether {top['fuel_type']} premiums cover the claim cost they create.",
            score=100 * (top["claim_to_premium_ratio"] / max(fuel["claim_to_premium_ratio"].mean(), 1e-9) - 1)))

    age = ia.analyze_vehicle_risk_patterns(pol, "vehicle_age_group")
    age = age[age["policies"] >= MIN_GROUP_SIZE]
    if len(age) >= 2:
        hi, lo = age.iloc[0], age.iloc[-1]
        cards.append(_card(
            "Vehicle", f"Vehicles aged {hi['vehicle_age_group']} have the highest claim-to-premium ratio ({hi['claim_to_premium_ratio']:.2f})",
            f"Lowest group = {lo['vehicle_age_group']} ({lo['claim_to_premium_ratio']:.2f}). "
            f"Difference = {hi['claim_to_premium_ratio'] - lo['claim_to_premium_ratio']:.2f}.",
            "If the gap between age groups is small, vehicle age is not a strong risk driver in this data.",
            "Do not add a vehicle-age loading unless the gap is meaningful after more data is collected.",
            score=100 * (hi["claim_to_premium_ratio"] - lo["claim_to_premium_ratio"]) / max(lo["claim_to_premium_ratio"], 1e-9)))
    return cards


def generate_risk_patterns(data):
    """Patterns where claims cost much more than the premium collected."""
    if not (_has_data(data, "policies") and _has_data(data, "claims")):
        return []
    pol, clm, cards = data["policies"], data["claims"], []
    portfolio = ia.calculate_claim_to_premium_ratio(clm, pol)

    types = ia.analyze_policy_type(pol)
    if len(types):
        top = types.iloc[0]
        cards.append(_card(
            "Risk", f"{top['policy_type']} has a claim-to-premium ratio of {top['claim_to_premium_ratio']:.2f} "
                    f"(portfolio {portfolio:.2f})",
            f"Premium {_money(top['total_premium'])} vs claims {_money(top['total_claim_amount'])} on {int(top['policies']):,} policies.",
            "A ratio above 1 means claims requested are larger than the premium collected for this product.",
            f"Investigate {top['policy_type']} pricing, coverage limits and claim approval rules first.",
            score=100 * (top["claim_to_premium_ratio"] / portfolio - 1) if portfolio else 0))

    seg = pol.groupby(["policy_type", "vehicle_make"]).agg(
        n=("policy_id", "count"), prem=("premium_amount", "sum"), clm=("claim_amount_total", "sum")).reset_index()
    seg = seg[seg["n"] >= MIN_GROUP_SIZE]
    if len(seg):
        seg["ratio"] = seg["clm"] / seg["prem"]
        top = seg.sort_values("ratio").iloc[-1]
        cards.append(_card(
            "Risk", f"Riskiest segment: {top['policy_type']} + {top['vehicle_make']} (ratio {top['ratio']:.2f})",
            f"{int(top['n']):,} policies, premium {_money(top['prem'])}, claims {_money(top['clm'])}; portfolio ratio {portfolio:.2f}.",
            "This combination is a concentrated pocket of high claim cost.",
            "Review pricing and approval checks for this segment before the next renewal cycle.",
            score=100 * (top["ratio"] / portfolio - 1) if portfolio else 0))

    if "state" in clm.columns and "state" in pol.columns:
        reg = ia.analyze_vehicle_risk_patterns(pol, "state")
        reg = reg[reg["policies"] >= MIN_GROUP_SIZE]
        if len(reg):
            top = reg.sort_values("claim_frequency").iloc[-1]
            avg_freq = pol["claim_count"].sum() / len(pol)
            cards.append(_card(
                "Risk", f"{top['state']} has the highest claim frequency ({top['claim_frequency']:.2f} claims per policy)",
                f"Portfolio average = {avg_freq:.2f}. {top['state']}: {int(top['total_claims']):,} claims on {int(top['policies']):,} policies.",
                "A region with higher claim frequency than the average is a geographic risk hot-spot.",
                f"Investigate road, theft and fraud conditions in {top['state']}; consider regional pricing.",
                score=100 * (top["claim_frequency"] / avg_freq - 1) if avg_freq else 0))

    if "claim_to_premium_ratio" in clm.columns:
        big = clm[clm["claim_to_premium_ratio"] > 10]
        if len(big):
            cards.append(_card(
                "Risk", f"{100 * len(big) / len(clm):.1f}% of claims are more than 10 times the policy premium",
                f"{len(big):,} claims, total {_money(big['claim_amount'].sum())} ({100 * big['claim_amount'].sum() / clm['claim_amount'].sum():.1f}% of claim cost).",
                "Very large claims against small premiums erode profit quickly.",
                "Add a review step for claims above 10x premium and check them for fraud and coverage limits.",
                score=100 * len(big) / len(clm)))
    return cards


def generate_business_recommendations(data):
    """Rank every pattern by its score and return the top 5 as prioritised recommendations."""
    pool = []
    for func in (generate_portfolio_insights, generate_claim_insights, generate_premium_insights,
                 generate_customer_insights, generate_vehicle_insights, generate_risk_patterns):
        pool.extend(func(data))
    pool.sort(key=lambda card: card["score"], reverse=True)
    top = pool[:5]
    for rank, card in enumerate(top, start=1):
        card["pattern"] = f"Priority {rank}: {card['pattern']}"
    return top


# ---------------------------------------------------------------------------
# Report text (used by run_pipeline.py and the dashboard download button)
# ---------------------------------------------------------------------------
def _cards_to_markdown(cards):
    """Turn insight cards into Markdown text."""
    lines = []
    for card in cards:
        lines += [f"**PATTERN:** {card['pattern']}", "",
                  f"**EVIDENCE:** {card['evidence']}", "",
                  f"**BUSINESS MEANING:** {card['business_meaning']}", "",
                  f"**RECOMMENDATION:** {card['recommendation']}", "", "---", ""]
    return "\n".join(lines)


def generate_business_report(data, validation_report=None, title="Motor Insurance Business Report"):
    """Write the final business report (section 36) as Markdown text, from the given data."""
    pol, clm, pay = data["policies"], data["claims"], data["payments"]
    kpis = [
        ("Total policies", f"{ia.calculate_total_policies(pol):,}"),
        ("Active policies", f"{ia.calculate_active_policies(pol):,}"),
        ("Total premium", _money(ia.calculate_total_premium(pol))),
        ("Average premium", _money(ia.calculate_average_premium(pol))),
        ("Total claims", f"{ia.calculate_total_claims(clm):,}"),
        ("Total claim amount", _money(ia.calculate_total_claim_amount(clm))),
        ("Average claim amount", _money(ia.calculate_average_claim_amount(clm))),
        ("Claim approval rate", f"{ia.calculate_claim_approval_rate(clm):.1f}%"),
        ("Claim rejection rate", f"{ia.calculate_claim_rejection_rate(clm):.1f}%"),
        ("Average settlement days", f"{ia.calculate_average_claim_settlement_days(clm):.1f}"),
        ("Claim-to-premium ratio", f"{ia.calculate_claim_to_premium_ratio(clm, pol):.2f}"),
        ("Paid claim ratio", f"{ia.calculate_paid_claim_ratio(pay, clm):.2f}"),
    ]
    out = [f"# {title}", "", f"_Generated: {pd.Timestamp.today():%d %b %Y}_", "",
           "## 1. Executive Summary", "",
           "This report is calculated from the cleaned motor-insurance tables. All numbers below come from the data.", "",
           "## 2. Business Problem", "",
           "Management needs a reliable view of policy activity, premium, claim cost, settlement speed and risk.", "",
           "## 3. Data and Table Summary", "",
           f"Policies: {len(pol):,} | Claims: {len(clm):,} | Payments: {len(pay):,}", ""]
    out += ["## 4. Data Quality Findings", ""]
    if validation_report:
        for table, res in validation_report.items():
            if isinstance(res, dict):
                out.append(f"- **{table}**: {'passed' if res['passed'] else 'issues -> ' + '; '.join(res['issues'])}")
    else:
        out.append("- Validation report not supplied.")
    out += ["", "## 5. Cleaning Performed", "",
            "Missing ids dropped, duplicates removed, text trimmed, dates converted, amounts checked, "
            "business rules applied (wrong end dates blanked) and derived columns added.", "",
            "## 6. KPI Summary", "", "| KPI | Value |", "|---|---|"]
    out += [f"| {k} | {v} |" for k, v in kpis]
    out += ["", "## 7. EDA Findings", "",
            ia.calculate_descriptive_statistics(pol, clm).round(2).to_markdown(index=False)
            if _has_tabulate() else "(install `tabulate` to print the statistics table)", ""]
    out += ["## 8. Important Patterns", "", _cards_to_markdown(generate_risk_patterns(data)),
            "## 9. Business Insights", "",
            _cards_to_markdown(generate_portfolio_insights(data) + generate_claim_insights(data)
                               + generate_premium_insights(data) + generate_customer_insights(data)
                               + generate_vehicle_insights(data)),
            "## 10. Recommendations", "", _cards_to_markdown(generate_business_recommendations(data)),
            "## 11. Dashboard Summary", "",
            "Seven pages (Executive Overview, Policy, Claims, Customer, Vehicle, Premium & Risk, Insights) plus a Live Fleet Simulation page. "
            "Sidebar filters update every KPI, chart and insight.", "",
            "## 12. Deployment Summary", "", "Docker image -> Amazon ECR -> EC2 -> Streamlit on port 8501.", "",
            "## 13. Conclusion", "",
            "The portfolio shows clear claim-cost pockets (see Important Patterns). Act on the ranked recommendations first."]
    return "\n".join(out)


def _has_tabulate():
    """True when the optional 'tabulate' package is installed (needed for to_markdown)."""
    try:
        import tabulate  # noqa: F401
        return True
    except ImportError:
        return False
