"""Validation of the raw tables and of the relationships between them.

Every validate_* function returns a small dictionary:
    {"table": name, "passed": True/False, "missing_columns": [...], "issues": [...]}
Validation only REPORTS problems. Fixing them is the job of data_cleaner.py.
"""
import pandas as pd

from src.logger import log_pipeline_step

REQUIRED_COLUMNS = {
    "customers": ["customer_id", "customer_name", "gender", "date_of_birth", "age", "city", "state", "occupation"],
    "vehicles": ["vehicle_id", "customer_id", "vehicle_type", "vehicle_make", "vehicle_model",
                 "vehicle_year", "fuel_type", "vehicle_value"],
    "policies": ["policy_id", "customer_id", "vehicle_id", "policy_start_date", "policy_end_date",
                 "policy_type", "premium_amount", "coverage_amount", "policy_status", "payment_frequency"],
    "claims": ["claim_id", "policy_id", "customer_id", "claim_date", "accident_date", "claim_type",
               "accident_location", "claim_amount", "claim_status", "approval_date", "settlement_date",
               "damage_severity"],
    "payments": ["payment_id", "claim_id", "policy_id", "payment_date", "payment_amount",
                 "payment_status", "payment_method"],
}

# Business rules: the only values allowed in these columns
VALID_POLICY_STATUS = ["Active", "Expired", "Cancelled", "Renewed"]
VALID_CLAIM_STATUS = ["Pending", "Approved", "Rejected", "Settled"]
VALID_SEVERITY = ["Low", "Medium", "High"]


# ---------- small helpers (each does one job) ----------
def _result(table, df, primary_key):
    """Start a result dictionary and run the checks every table needs."""
    missing = [c for c in REQUIRED_COLUMNS[table] if c not in df.columns]
    issues = []
    if not missing and primary_key:
        if df[primary_key].isna().any():
            issues.append(f"{int(df[primary_key].isna().sum())} missing values in {primary_key}")
        if df[primary_key].duplicated().any():
            issues.append(f"{int(df[primary_key].duplicated().sum())} duplicate {primary_key} values")
    return {"table": table, "passed": True, "missing_columns": missing, "issues": issues}


def _check_positive(df, column, issues):
    """Add an issue if a numeric column has non-numeric, negative or zero values."""
    values = pd.to_numeric(df[column], errors="coerce")
    bad = int(((values <= 0) | (values.isna() & df[column].notna())).sum())
    if bad:
        issues.append(f"{bad} invalid (non-numeric / <= 0) values in {column}")


def _check_dates(df, columns, issues):
    """Add an issue for every date column that has unreadable (non-empty) dates."""
    for col in columns:
        parsed = pd.to_datetime(df[col], errors="coerce")
        bad = int((parsed.isna() & df[col].notna()).sum())
        if bad:
            issues.append(f"{bad} unreadable dates in {col}")


def _check_allowed(df, column, allowed, issues):
    """Add an issue if a column has values outside the business rule list."""
    bad = int((~df[column].dropna().isin(allowed)).sum())
    if bad:
        issues.append(f"{bad} values in {column} are not in {allowed}")


def _finish(result):
    """Mark the table as passed or failed and log the outcome."""
    result["passed"] = not result["missing_columns"] and not result["issues"]
    state = "PASSED" if result["passed"] else "ISSUES FOUND"
    log_pipeline_step(f"Validation {result['table']}: {state} {result['missing_columns']} {result['issues']}")
    return result


# ---------- table validators ----------
def validate_customers(df):
    """Check columns, unique customer_id, valid dates of birth and age range."""
    result = _result("customers", df, "customer_id")
    if not result["missing_columns"]:
        _check_dates(df, ["date_of_birth"], result["issues"])
        age = pd.to_numeric(df["age"], errors="coerce")
        if ((age < 18) | (age > 100)).any():
            result["issues"].append("age outside 18-100 found")
    return _finish(result)


def validate_vehicles(df):
    """Check columns, unique vehicle_id, vehicle value and vehicle year."""
    result = _result("vehicles", df, "vehicle_id")
    if not result["missing_columns"]:
        _check_positive(df, "vehicle_value", result["issues"])
        year = pd.to_numeric(df["vehicle_year"], errors="coerce")
        if ((year < 1980) | (year > pd.Timestamp.today().year + 1)).any():
            result["issues"].append("vehicle_year outside a realistic range")
    return _finish(result)


def validate_policies(df):
    """Check columns, unique policy_id, amounts, dates, end-after-start and status values."""
    result = _result("policies", df, "policy_id")
    if not result["missing_columns"]:
        _check_positive(df, "premium_amount", result["issues"])
        _check_positive(df, "coverage_amount", result["issues"])
        _check_dates(df, ["policy_start_date", "policy_end_date"], result["issues"])
        start = pd.to_datetime(df["policy_start_date"], errors="coerce")
        end = pd.to_datetime(df["policy_end_date"], errors="coerce")
        if (end < start).any():
            result["issues"].append(f"{int((end < start).sum())} policies end before they start")
        _check_allowed(df, "policy_status", VALID_POLICY_STATUS, result["issues"])
    return _finish(result)


def validate_claims(df):
    """Check columns, unique claim_id, claim amount, dates and status / severity values."""
    result = _result("claims", df, "claim_id")
    if not result["missing_columns"]:
        _check_positive(df, "claim_amount", result["issues"])
        _check_dates(df, ["claim_date", "accident_date", "approval_date", "settlement_date"], result["issues"])
        claim = pd.to_datetime(df["claim_date"], errors="coerce")
        accident = pd.to_datetime(df["accident_date"], errors="coerce")
        if (claim < accident).any():
            result["issues"].append(f"{int((claim < accident).sum())} claims filed before the accident")
        _check_allowed(df, "claim_status", VALID_CLAIM_STATUS, result["issues"])
        _check_allowed(df, "damage_severity", VALID_SEVERITY, result["issues"])
    return _finish(result)


def validate_payments(df):
    """Check columns, unique payment_id, payment amount and payment date."""
    result = _result("payments", df, "payment_id")
    if not result["missing_columns"]:
        _check_positive(df, "payment_amount", result["issues"])
        _check_dates(df, ["payment_date"], result["issues"])
    return _finish(result)


def validate_relationships(data):
    """Check that every foreign key points to a row that really exists."""
    issues = []
    checks = [
        ("policies", "customer_id", "customers", "customer_id"),
        ("policies", "vehicle_id", "vehicles", "vehicle_id"),
        ("claims", "policy_id", "policies", "policy_id"),
        ("claims", "customer_id", "customers", "customer_id"),
        ("payments", "claim_id", "claims", "claim_id"),
        ("payments", "policy_id", "policies", "policy_id"),
    ]
    for child, child_col, parent, parent_col in checks:
        orphans = ~data[child][child_col].dropna().isin(data[parent][parent_col])
        if orphans.any():
            issues.append(f"{int(orphans.sum())} rows in {child}.{child_col} have no match in {parent}.{parent_col}")
    result = {"table": "relationships", "passed": not issues, "missing_columns": [], "issues": issues}
    return _finish(result)


def validate_all_tables(data):
    """Run every validator and return one combined report."""
    log_pipeline_step("Validation started")
    report = {
        "customers": validate_customers(data["customers"]),
        "vehicles": validate_vehicles(data["vehicles"]),
        "policies": validate_policies(data["policies"]),
        "claims": validate_claims(data["claims"]),
        "payments": validate_payments(data["payments"]),
    }
    # relationship checks only make sense when all columns exist
    if all(not r["missing_columns"] for r in report.values()):
        report["relationships"] = validate_relationships(data)
    report["all_passed"] = all(r["passed"] for r in report.values())
    report["has_missing_columns"] = any(r["missing_columns"] for r in report.values() if isinstance(r, dict))
    log_pipeline_step(f"Validation finished. all_passed={report['all_passed']}")
    return report
