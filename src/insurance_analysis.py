"""KPI and business-analysis functions.

Two kinds of functions live here:
  * calculate_*  -> return ONE number (a KPI)
  * analyze_*    -> return a small DataFrame (a group comparison)

The "master" tables join the five raw tables so every claim / policy row
already knows its customer, vehicle and region.
"""
import numpy as np
import pandas as pd

AGE_BINS = [17, 25, 35, 45, 55, 65, 120]
AGE_LABELS = ["18-25", "26-35", "36-45", "46-55", "56-65", "65+"]
VEH_AGE_BINS = [-1, 2, 5, 8, 100]
VEH_AGE_LABELS = ["0-2 yrs", "3-5 yrs", "6-8 yrs", "9+ yrs"]
APPROVED_STATUSES = ["Approved", "Settled"]     # a Settled claim was approved first


def _safe_div(a, b):
    """Divide a by b, return 0.0 when b is 0 or empty (avoids crashes on empty filters)."""
    return float(a) / float(b) if b else 0.0


def _pick(df, columns):
    """Keep only the columns that really exist in df."""
    return [c for c in columns if c in df.columns]


# ---------------------------------------------------------------------------
# Master tables
# ---------------------------------------------------------------------------
def add_groups(df):
    """Add age_group and vehicle_age_group columns when the source columns exist."""
    df = df.copy()
    if "age" in df.columns:
        df["age_group"] = pd.cut(df["age"], bins=AGE_BINS, labels=AGE_LABELS).astype(str)
    if "vehicle_age" in df.columns:
        df["vehicle_age_group"] = pd.cut(df["vehicle_age"], bins=VEH_AGE_BINS, labels=VEH_AGE_LABELS).astype(str)
    return df


def attach_claim_totals(policies, claims):
    """Add claim_count and claim_amount_total to every policy (0 when it has no claims)."""
    policies = policies.drop(columns=_pick(policies, ["claim_count", "claim_amount_total"])).copy()
    totals = claims.groupby("policy_id")["claim_amount"].agg(claim_count="count", claim_amount_total="sum")
    policies = policies.merge(totals, left_on="policy_id", right_index=True, how="left")
    policies["claim_count"] = policies["claim_count"].fillna(0).astype(int)
    policies["claim_amount_total"] = policies["claim_amount_total"].fillna(0.0)
    return policies


def build_policy_master(data):
    """One row per policy + customer details + vehicle details + claim totals."""
    pol, cus, veh = data["policies"], data["customers"], data["vehicles"]
    cus_cols = _pick(cus, ["customer_id", "gender", "age", "city", "state", "occupation"])
    veh_cols = _pick(veh, ["vehicle_id", "vehicle_type", "vehicle_make", "vehicle_model", "vehicle_year",
                           "fuel_type", "vehicle_value", "vehicle_age"])
    master = pol.merge(cus[cus_cols], on="customer_id", how="left")
    master = master.merge(veh[veh_cols], on="vehicle_id", how="left")
    master = add_groups(master)
    if "policy_start_date" in master.columns:
        master["policy_start_month"] = pd.to_datetime(master["policy_start_date"]).dt.to_period("M").dt.to_timestamp()
    return attach_claim_totals(master, data["claims"])


def build_claims_master(data):
    """One row per claim + policy + customer + vehicle details + amount paid."""
    clm, pol, cus, veh, pay = data["claims"], data["policies"], data["customers"], data["vehicles"], data["payments"]
    pol_cols = _pick(pol, ["policy_id", "vehicle_id", "policy_type", "premium_amount", "coverage_amount",
                           "policy_status", "policy_start_date"])
    cus_cols = _pick(cus, ["customer_id", "gender", "age", "city", "state", "occupation"])
    veh_cols = _pick(veh, ["vehicle_id", "vehicle_type", "vehicle_make", "vehicle_model", "vehicle_year",
                           "fuel_type", "vehicle_value", "vehicle_age"])
    master = clm.merge(pol[pol_cols], on="policy_id", how="left")
    master = master.merge(cus[cus_cols], on="customer_id", how="left")
    master = master.merge(veh[veh_cols], on="vehicle_id", how="left")
    paid = pay.groupby("claim_id")["payment_amount"].sum().rename("paid_amount")
    master = master.merge(paid, left_on="claim_id", right_index=True, how="left")
    master["paid_amount"] = master["paid_amount"].fillna(0.0)
    master = add_groups(master)
    master["claim_month"] = pd.to_datetime(master["claim_date"]).dt.to_period("M").dt.to_timestamp()
    return master


# ---------------------------------------------------------------------------
# Portfolio KPIs
# ---------------------------------------------------------------------------
def calculate_total_customers(customers):
    """Number of unique customers."""
    return int(customers["customer_id"].nunique())


def calculate_total_policies(policies):
    """Number of unique policies."""
    return int(policies["policy_id"].nunique())


def _count_status(policies, status):
    """Count policies with one status."""
    return int((policies["policy_status"] == status).sum())


def calculate_active_policies(policies):
    """Policies whose status is Active."""
    return _count_status(policies, "Active")


def calculate_expired_policies(policies):
    """Policies whose status is Expired."""
    return _count_status(policies, "Expired")


def calculate_cancelled_policies(policies):
    """Policies whose status is Cancelled."""
    return _count_status(policies, "Cancelled")


def calculate_renewed_policies(policies):
    """Policies whose status is Renewed."""
    return _count_status(policies, "Renewed")


# ---------------------------------------------------------------------------
# Premium KPIs
# ---------------------------------------------------------------------------
def calculate_total_premium(policies):
    """Sum of premium_amount."""
    return float(policies["premium_amount"].sum())


def calculate_average_premium(policies):
    """Average premium per policy."""
    return float(policies["premium_amount"].mean()) if len(policies) else 0.0


def calculate_average_coverage(policies):
    """Average coverage amount per policy."""
    return float(policies["coverage_amount"].mean()) if len(policies) else 0.0


def calculate_premium_by_policy_type(policies):
    """Policies, total premium and average premium for each policy type."""
    out = policies.groupby("policy_type").agg(
        policies=("policy_id", "count"),
        total_premium=("premium_amount", "sum"),
        average_premium=("premium_amount", "mean"),
    ).reset_index()
    out["premium_share_pct"] = 100 * out["total_premium"] / out["total_premium"].sum() if len(out) else 0
    return out.sort_values("total_premium", ascending=False).reset_index(drop=True)


# ---------------------------------------------------------------------------
# Claim KPIs
# ---------------------------------------------------------------------------
def calculate_total_claims(claims):
    """Number of unique claims."""
    return int(claims["claim_id"].nunique())


def calculate_approved_claims(claims):
    """Approved claims. A Settled claim was approved first, so both count."""
    return int(claims["claim_status"].isin(APPROVED_STATUSES).sum())


def calculate_rejected_claims(claims):
    """Claims with status Rejected."""
    return int((claims["claim_status"] == "Rejected").sum())


def calculate_pending_claims(claims):
    """Claims with status Pending."""
    return int((claims["claim_status"] == "Pending").sum())


def calculate_total_claim_amount(claims):
    """Sum of claim_amount."""
    return float(claims["claim_amount"].sum())


def calculate_average_claim_amount(claims):
    """Average claim_amount."""
    return float(claims["claim_amount"].mean()) if len(claims) else 0.0


def calculate_claim_approval_rate(claims):
    """Approved claims / total claims x 100."""
    return 100 * _safe_div(calculate_approved_claims(claims), len(claims))


def calculate_claim_rejection_rate(claims):
    """Rejected claims / total claims x 100."""
    return 100 * _safe_div(calculate_rejected_claims(claims), len(claims))


# ---------------------------------------------------------------------------
# Settlement KPIs
# ---------------------------------------------------------------------------
def _days_between(claims, later, earlier="claim_date"):
    """Average days between two date columns (ignores empty dates)."""
    days = (pd.to_datetime(claims[later]) - pd.to_datetime(claims[earlier])).dt.days
    return float(days.mean()) if days.notna().any() else 0.0


def calculate_average_claim_processing_days(claims):
    """Average days from claim_date to approval_date."""
    return _days_between(claims, "approval_date")


def calculate_average_claim_settlement_days(claims):
    """Average days from claim_date to settlement_date."""
    return _days_between(claims, "settlement_date")


def calculate_total_payment_amount(payments):
    """Sum of payment_amount."""
    return float(payments["payment_amount"].sum())


def calculate_average_payment_amount(payments):
    """Average payment_amount."""
    return float(payments["payment_amount"].mean()) if len(payments) else 0.0


# ---------------------------------------------------------------------------
# Risk ratios
# ---------------------------------------------------------------------------
def calculate_claim_to_premium_ratio(claims, policies):
    """Total claim amount / total premium (portfolio loss ratio)."""
    return _safe_div(claims["claim_amount"].sum(), policies["premium_amount"].sum())


def calculate_claim_to_coverage_ratio(claims, policies):
    """Total claim amount / total coverage amount."""
    return _safe_div(claims["claim_amount"].sum(), policies["coverage_amount"].sum())


def calculate_paid_claim_ratio(payments, claims):
    """Money paid / amount claimed, only for claims that have a payment."""
    paid_ids = payments["claim_id"].unique()
    claimed = claims.loc[claims["claim_id"].isin(paid_ids), "claim_amount"].sum()
    return _safe_div(payments["payment_amount"].sum(), claimed)


# ---------------------------------------------------------------------------
# Group analysis
# ---------------------------------------------------------------------------
def _claim_summary(claims, by):
    """Claims count, total / average amount, share and settlement days for any grouping."""
    claims = claims.copy()
    if "claim_settlement_days" not in claims.columns:
        claims["claim_settlement_days"] = (pd.to_datetime(claims["settlement_date"])
                                           - pd.to_datetime(claims["claim_date"])).dt.days
    out = claims.groupby(by, observed=True).agg(
        total_claims=("claim_id", "count"),
        total_claim_amount=("claim_amount", "sum"),
        avg_claim_amount=("claim_amount", "mean"),
        avg_settlement_days=("claim_settlement_days", "mean"),
    ).reset_index()
    total = out["total_claim_amount"].sum()
    out["share_of_claim_amount_pct"] = 100 * out["total_claim_amount"] / total if total else 0.0
    return out.sort_values("total_claim_amount", ascending=False).reset_index(drop=True)


def _risk_summary(policies, by):
    """Policies, premium, claims, claim frequency and claim-to-premium ratio for any grouping."""
    out = policies.groupby(by, observed=True).agg(
        policies=("policy_id", "count"),
        total_premium=("premium_amount", "sum"),
        total_claims=("claim_count", "sum"),
        total_claim_amount=("claim_amount_total", "sum"),
    ).reset_index()
    out["claim_frequency"] = out["total_claims"] / out["policies"]
    out["avg_claim_amount"] = np.where(out["total_claims"] > 0, out["total_claim_amount"] / out["total_claims"].replace(0, 1), 0.0)
    out["claim_to_premium_ratio"] = np.where(out["total_premium"] > 0, out["total_claim_amount"] / out["total_premium"].replace(0, 1), 0.0)
    return out.sort_values("claim_to_premium_ratio", ascending=False).reset_index(drop=True)


def analyze_customer_claims(claims, by="age_group"):
    """Claim behaviour by customer segment (age_group, gender, occupation, state ...)."""
    return _claim_summary(claims, by)


def analyze_customer_premium(policies, by="age_group"):
    """Premium by customer segment."""
    out = policies.groupby(by, observed=True).agg(
        policies=("policy_id", "count"),
        total_premium=("premium_amount", "sum"),
        average_premium=("premium_amount", "mean"),
    ).reset_index()
    return out.sort_values("total_premium", ascending=False).reset_index(drop=True)


def analyze_vehicle_claims(claims, by="vehicle_make"):
    """Claim behaviour by vehicle make / fuel type / vehicle age group / vehicle type."""
    return _claim_summary(claims, by)


def analyze_vehicle_risk_patterns(policies, by="vehicle_make"):
    """Claim frequency and claim-to-premium ratio by vehicle group."""
    return _risk_summary(policies, by)


def analyze_claim_type(claims):
    """Claim count and cost for each claim type."""
    return _claim_summary(claims, "claim_type")


def analyze_claim_status(claims):
    """Claim count and cost for each claim status."""
    return _claim_summary(claims, "claim_status")


def analyze_policy_type(policies):
    """Premium, claims and claim-to-premium ratio for each policy type."""
    return _risk_summary(policies, "policy_type")


def analyze_region(claims, level="state"):
    """Claim frequency (count) and severity (average amount) by state or city."""
    return _claim_summary(claims, level)


def analyze_vehicle_type(claims):
    """Claim count and cost for each vehicle type."""
    return _claim_summary(claims, "vehicle_type")


def analyze_damage_severity(claims):
    """Claim count and cost for Low / Medium / High damage."""
    return _claim_summary(claims, "damage_severity")


# ---------------------------------------------------------------------------
# Statistics (section 26)
# ---------------------------------------------------------------------------
def calculate_descriptive_statistics(policies, claims):
    """Mean, median, mode, variance and std for premium, claim amount and settlement days."""
    rows = []
    series = {
        "premium_amount": policies["premium_amount"],
        "claim_amount": claims["claim_amount"],
        "claim_settlement_days": claims.get("claim_settlement_days", pd.Series(dtype=float)),
    }
    for name, s in series.items():
        s = pd.to_numeric(s, errors="coerce").dropna()
        if s.empty:
            continue
        mode = s.round(0).mode()
        rows.append({"metric": name, "mean": s.mean(), "median": s.median(),
                     "mode": mode.iloc[0] if len(mode) else np.nan,
                     "variance": s.var(), "std_dev": s.std(), "skewness": s.skew()})
    return pd.DataFrame(rows)
