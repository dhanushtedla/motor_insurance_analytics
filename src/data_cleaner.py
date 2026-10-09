"""Cleaning pipeline: every function takes the data dictionary and returns a new, cleaner one.

Raw files are never changed. Cleaned files are written to data/cleaned/.
"""
from pathlib import Path

import numpy as np
import pandas as pd

from src.logger import log_pipeline_step
from src.validation import VALID_POLICY_STATUS, VALID_CLAIM_STATUS, VALID_SEVERITY

PRIMARY_KEYS = {
    "customers": "customer_id",
    "vehicles": "vehicle_id",
    "policies": "policy_id",
    "claims": "claim_id",
    "payments": "payment_id",
}

# columns that must exist for a row to be useful (cannot be guessed)
REQUIRED_NOT_NULL = {
    "customers": ["customer_id"],
    "vehicles": ["vehicle_id", "customer_id"],
    "policies": ["policy_id", "customer_id", "vehicle_id", "premium_amount", "coverage_amount"],
    "claims": ["claim_id", "policy_id", "customer_id", "claim_amount"],
    "payments": ["payment_id", "claim_id", "payment_amount"],
}

DATE_COLUMNS = {
    "customers": ["date_of_birth"],
    "policies": ["policy_start_date", "policy_end_date"],
    "claims": ["claim_date", "accident_date", "approval_date", "settlement_date"],
    "payments": ["payment_date"],
}

NUMERIC_COLUMNS = {
    "customers": ["age"],
    "vehicles": ["vehicle_year", "vehicle_value"],
    "policies": ["premium_amount", "coverage_amount"],
    "claims": ["claim_amount"],
    "payments": ["payment_amount"],
}

ID_COLUMNS = ["customer_id", "vehicle_id", "policy_id", "claim_id", "payment_id"]
STATUS_COLUMNS = ["policy_status", "claim_status", "damage_severity", "payment_status"]


def _is_text(series):
    """True for text columns (not numbers, not dates)."""
    return not pd.api.types.is_numeric_dtype(series) and not pd.api.types.is_datetime64_any_dtype(series)


def _copy(data):
    """Copy the dictionary and every DataFrame so the input is never modified."""
    return {name: df.copy() for name, df in data.items()}


# ---------------------------------------------------------------------------
def handle_missing_values(data):
    """Handle missing values table by table.

    * rows with a missing id or missing money amount are dropped (cannot be guessed)
    * other numbers are filled with the median
    * text is filled with 'Unknown'
    * approval_date / settlement_date stay empty ON PURPOSE: a pending or rejected
      claim has no approval or settlement yet - filling them would be wrong.
    """
    data = _copy(data)
    for name, df in data.items():
        before = len(df)
        df = df.dropna(subset=[c for c in REQUIRED_NOT_NULL.get(name, []) if c in df.columns])
        date_cols = DATE_COLUMNS.get(name, [])
        for col in df.columns:
            if col in date_cols:
                continue
            if _is_text(df[col]):
                df[col] = df[col].fillna("Unknown")
            elif df[col].isna().any():
                df[col] = df[col].fillna(df[col].median())
        data[name] = df
        log_pipeline_step(f"Missing values handled in {name}: {before - len(df)} rows dropped")
    return data


def remove_duplicates(data):
    """Remove exact duplicate rows and repeated primary keys (keep the first one)."""
    data = _copy(data)
    for name, df in data.items():
        before = len(df)
        df = df.drop_duplicates()
        key = PRIMARY_KEYS.get(name)
        if key in df.columns:
            df = df.drop_duplicates(subset=[key], keep="first")
        data[name] = df.reset_index(drop=True)
        log_pipeline_step(f"Duplicates removed in {name}: {before - len(df)}")
    return data


def clean_text_columns(data):
    """Trim spaces, fix ids to UPPER case and status columns to Title Case."""
    data = _copy(data)
    for name, df in data.items():
        for col in df.columns:
            if not _is_text(df[col]):
                continue
            df[col] = df[col].astype(str).str.strip().str.replace(r"\s+", " ", regex=True)
            if col in ID_COLUMNS:
                df[col] = df[col].str.upper()
            elif col in STATUS_COLUMNS:
                df[col] = df[col].str.title()
        data[name] = df
    log_pipeline_step("Text columns cleaned")
    return data


def clean_date_columns(data):
    """Convert date columns to real datetime values (unreadable dates become empty)."""
    data = _copy(data)
    for name, columns in DATE_COLUMNS.items():
        for col in columns:
            if col in data[name].columns:
                data[name][col] = pd.to_datetime(data[name][col], errors="coerce")
    log_pipeline_step("Date columns converted")
    return data


def validate_numeric_columns(data):
    """Force numeric columns to numbers and drop rows with impossible amounts (<= 0)."""
    data = _copy(data)
    money = ["premium_amount", "coverage_amount", "claim_amount", "payment_amount", "vehicle_value"]
    for name, columns in NUMERIC_COLUMNS.items():
        df = data[name]
        for col in columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        bad = df[[c for c in columns if c in money]].le(0).any(axis=1) | df[columns].isna().any(axis=1)
        data[name] = df[~bad].reset_index(drop=True)
        log_pipeline_step(f"Numeric check {name}: {int(bad.sum())} rows dropped")
    return data


def validate_business_rules(data):
    """Apply the business rules: valid statuses, correct date order, valid relationships."""
    data = _copy(data)

    pol = data["policies"]
    pol = pol[pol["policy_status"].isin(VALID_POLICY_STATUS)]
    pol = pol.copy()
    # an end date before the start date is impossible. The policy itself is real (it still has
    # premium and claims), so we keep the row and only blank the wrong end date.
    wrong_end = pol["policy_end_date"] < pol["policy_start_date"]
    pol.loc[wrong_end, "policy_end_date"] = pd.NaT
    log_pipeline_step(f"Policies with end date before start date (end date blanked): {int(wrong_end.sum())}")
    data["policies"] = pol.reset_index(drop=True)

    clm = data["claims"]
    clm = clm[clm["claim_status"].isin(VALID_CLAIM_STATUS) & clm["damage_severity"].isin(VALID_SEVERITY)]
    clm = clm[clm["policy_id"].isin(data["policies"]["policy_id"])]        # claim must belong to a policy
    clm = clm[~(clm["claim_date"] < clm["accident_date"])]                  # cannot claim before the accident
    clm = clm.copy()
    # approval / settlement before the claim date is impossible -> blank it
    clm.loc[clm["approval_date"] < clm["claim_date"], "approval_date"] = pd.NaT
    clm.loc[clm["settlement_date"] < clm["claim_date"], "settlement_date"] = pd.NaT
    data["claims"] = clm.reset_index(drop=True)

    pay = data["payments"]
    data["payments"] = pay[pay["claim_id"].isin(data["claims"]["claim_id"])].reset_index(drop=True)

    log_pipeline_step("Business rules applied")
    return data


def create_derived_columns(data, analysis_date=None):
    """Add the derived columns from the project standard (section 8)."""
    data = _copy(data)
    today = pd.Timestamp(analysis_date) if analysis_date is not None else pd.Timestamp.today().normalize()

    cus, veh, pol = data["customers"], data["vehicles"], data["policies"]
    clm, pay = data["claims"], data["payments"]

    # customer_age from date_of_birth (exact years)
    dob = pd.to_datetime(cus["date_of_birth"], errors="coerce")
    cus["customer_age"] = ((today - dob).dt.days // 365.25).astype("Int64")

    # vehicle_age = analysis year - vehicle_year
    veh["vehicle_age"] = (today.year - veh["vehicle_year"]).clip(lower=0)

    # policy columns
    pol["policy_duration_days"] = (pol["policy_end_date"] - pol["policy_start_date"]).dt.days
    pol["policy_active_flag"] = (pol["policy_status"] == "Active").astype(int)

    # claim columns
    clm["claim_processing_days"] = (clm["approval_date"] - clm["claim_date"]).dt.days
    clm["claim_settlement_days"] = (clm["settlement_date"] - clm["claim_date"]).dt.days
    prem = pol.set_index("policy_id")[["premium_amount", "coverage_amount"]]
    clm["claim_to_premium_ratio"] = clm["claim_amount"] / clm["policy_id"].map(prem["premium_amount"])
    clm["claim_to_coverage_ratio"] = clm["claim_amount"] / clm["policy_id"].map(prem["coverage_amount"])
    paid = pay.groupby("claim_id")["payment_amount"].sum()
    clm["paid_claim_ratio"] = (clm["claim_id"].map(paid) / clm["claim_amount"]).fillna(0.0)

    data.update({"customers": cus, "vehicles": veh, "policies": pol, "claims": clm, "payments": pay})
    log_pipeline_step("Derived columns created")
    return data


def clean_data(data):
    """Run the whole cleaning pipeline in the standard order."""
    log_pipeline_step("Cleaning started")
    data = handle_missing_values(data)
    data = remove_duplicates(data)
    data = clean_text_columns(data)
    data = clean_date_columns(data)
    data = validate_numeric_columns(data)
    data = validate_business_rules(data)
    data = create_derived_columns(data)
    log_pipeline_step("Cleaning finished")
    return data


def save_cleaned_data(data, output_dir):
    """Save every table as <table>_cleaned.csv and return the list of file paths."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    paths = []
    for name, df in data.items():
        path = out / f"{name}_cleaned.csv"
        df.to_csv(path, index=False)
        paths.append(str(path))
        log_pipeline_step(f"Saved {path.name}: {len(df)} rows")
    return paths
