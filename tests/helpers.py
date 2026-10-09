"""Small, hand-made tables used by the tests (so every expected answer can be checked by hand)."""
import pandas as pd


def small_data():
    """Return 5 tiny RAW-style tables: 3 customers, 3 vehicles, 3 policies, 4 claims, 1 payment."""
    customers = pd.DataFrame({
        "customer_id": ["C1", "C2", "C3"], "customer_name": ["A", "B", "C"], "gender": ["Male", "Female", "Male"],
        "date_of_birth": ["1990-01-01", "1980-06-15", "2000-12-31"], "age": [36, 46, 25],
        "city": ["Pune", "Delhi", "Surat"], "state": ["Maharashtra", "Delhi", "Gujarat"],
        "occupation": ["Engineer", "Doctor", "Student"]})
    vehicles = pd.DataFrame({
        "vehicle_id": ["V1", "V2", "V3"], "customer_id": ["C1", "C2", "C3"], "vehicle_type": ["Car"] * 3,
        "vehicle_make": ["Tata", "Hyundai", "Tata"], "vehicle_model": ["Punch", "i20", "Tiago"],
        "vehicle_year": [2020, 2016, 2024], "fuel_type": ["Petrol", "Diesel", "CNG"],
        "vehicle_value": [500000.0, 400000.0, 600000.0]})
    policies = pd.DataFrame({
        "policy_id": ["P1", "P2", "P3"], "customer_id": ["C1", "C2", "C3"], "vehicle_id": ["V1", "V2", "V3"],
        "policy_start_date": ["2025-01-01", "2024-01-01", "2025-06-01"],
        "policy_end_date": ["2025-12-31", "2024-12-31", "2025-05-01"],       # P3 ends BEFORE it starts (bad data)
        "policy_type": ["Comprehensive", "Third Party", "Comprehensive"],
        "premium_amount": [1000.0, 500.0, 1500.0], "coverage_amount": [100000.0, 50000.0, 150000.0],
        "policy_status": ["Active", "Expired", "Cancelled"], "payment_frequency": ["Annual"] * 3})
    claims = pd.DataFrame({
        "claim_id": ["CL1", "CL2", "CL3", "CL4"], "policy_id": ["P1", "P1", "P2", "P3"],
        "customer_id": ["C1", "C1", "C2", "C3"],
        "claim_date": ["2025-02-01", "2025-03-01", "2024-02-01", "2025-07-01"],
        "accident_date": ["2025-01-30", "2025-02-27", "2024-01-25", "2025-06-28"],
        "claim_type": ["Accident", "Theft", "Accident", "Fire"], "accident_location": ["City Road"] * 4,
        "claim_amount": [3000.0, 1000.0, 2000.0, 4000.0],
        "claim_status": ["Approved", "Rejected", "Settled", "Pending"],
        "approval_date": ["2025-02-11", None, "2024-02-05", None],
        "settlement_date": [None, None, "2024-02-21", None],
        "damage_severity": ["Medium", "Low", "High", "High"]})
    payments = pd.DataFrame({
        "payment_id": ["PAY1"], "claim_id": ["CL3"], "policy_id": ["P2"], "payment_date": ["2024-02-21"],
        "payment_amount": [1800.0], "payment_status": ["Completed"], "payment_method": ["UPI"]})
    return {"customers": customers, "vehicles": vehicles, "policies": policies, "claims": claims, "payments": payments}
