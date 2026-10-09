"""Tests for loading, cleaning, derived columns and saving."""
import tempfile
from pathlib import Path

import pandas as pd

from helpers import small_data
from src.data_cleaner import clean_data, create_derived_columns, remove_duplicates, save_cleaned_data, clean_date_columns
from src.data_loader import load_all_data


def test_load_all_data():
    """Proves: all 5 tables load into a dictionary, and a missing file raises an error (not silently ignored)."""
    with tempfile.TemporaryDirectory() as folder:
        for name, df in small_data().items():
            df.to_csv(Path(folder) / f"{name}.csv", index=False)
        data = load_all_data(folder)
        assert set(data) == {"customers", "vehicles", "policies", "claims", "payments"}
        assert len(data["claims"]) == 4
        (Path(folder) / "payments.csv").unlink()
        try:
            load_all_data(folder)
            assert False, "expected FileNotFoundError"
        except FileNotFoundError:
            pass


def test_remove_duplicates():
    """Proves: a repeated row and a repeated primary key are removed, the first one is kept."""
    data = small_data()
    data["claims"] = pd.concat([data["claims"], data["claims"].iloc[[0]]], ignore_index=True)   # exact duplicate
    clone = data["customers"].iloc[[1]].copy()
    clone["customer_name"] = "Changed"                                                          # same key, different row
    data["customers"] = pd.concat([data["customers"], clone], ignore_index=True)
    out = remove_duplicates(data)
    assert len(out["claims"]) == 4
    assert len(out["customers"]) == 3
    assert out["customers"].loc[out["customers"]["customer_id"] == "C2", "customer_name"].iloc[0] == "B"


def test_create_derived_columns():
    """Proves: derived columns are calculated correctly for hand-checkable rows."""
    data = clean_date_columns(small_data())
    out = create_derived_columns(data, analysis_date="2026-01-01")
    clm = out["claims"].set_index("claim_id")
    assert clm.loc["CL1", "claim_processing_days"] == 10                    # 2025-02-11 - 2025-02-01
    assert clm.loc["CL3", "claim_settlement_days"] == 20                    # 2024-02-21 - 2024-02-01
    assert clm.loc["CL1", "claim_to_premium_ratio"] == 3.0                  # 3000 / 1000
    assert clm.loc["CL1", "claim_to_coverage_ratio"] == 3000 / 100000
    assert abs(clm.loc["CL3", "paid_claim_ratio"] - 0.9) < 1e-9             # 1800 / 2000
    assert out["vehicles"].set_index("vehicle_id").loc["V1", "vehicle_age"] == 6   # 2026 - 2020
    pol = out["policies"].set_index("policy_id")
    assert pol.loc["P1", "policy_duration_days"] == 364
    assert pol.loc["P1", "policy_active_flag"] == 1 and pol.loc["P2", "policy_active_flag"] == 0


def test_clean_data():
    """Proves: the full pipeline keeps good rows, fixes the wrong end date (does not delete the policy), adds derived columns."""
    out = clean_data(small_data())
    assert len(out["policies"]) == 3                                         # bad-date policy P3 is kept
    assert pd.isna(out["policies"].set_index("policy_id").loc["P3", "policy_end_date"])
    assert pd.api.types.is_datetime64_any_dtype(out["claims"]["claim_date"])
    assert "claim_to_premium_ratio" in out["claims"].columns
    assert pd.isna(out["claims"].set_index("claim_id").loc["CL4", "approval_date"])   # pending claim stays empty


def test_save_cleaned_data():
    """Proves: one <table>_cleaned.csv file is written for every table and can be read back."""
    with tempfile.TemporaryDirectory() as folder:
        paths = save_cleaned_data(clean_data(small_data()), folder)
        assert len(paths) == 5
        assert (Path(folder) / "claims_cleaned.csv").exists()
        assert len(pd.read_csv(Path(folder) / "claims_cleaned.csv")) == 4
