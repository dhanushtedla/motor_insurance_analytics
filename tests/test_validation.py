"""Tests for validation: good data passes, specific bad data is reported."""
from helpers import small_data
from src import validation as v


def test_validate_customers():
    """Proves: clean customers pass; a duplicate id and an impossible age are reported."""
    df = small_data()["customers"]
    assert v.validate_customers(df)["passed"]
    bad = df.copy()
    bad.loc[1, "customer_id"] = "C1"
    bad.loc[2, "age"] = 5
    result = v.validate_customers(bad)
    assert not result["passed"]
    assert any("duplicate" in issue for issue in result["issues"])
    assert any("age" in issue for issue in result["issues"])


def test_validate_policies():
    """Proves: a policy ending before it starts and an invalid status are caught; missing columns are listed."""
    result = v.validate_policies(small_data()["policies"])          # P3 has end < start in the fixture
    assert not result["passed"]
    assert any("end before they start" in issue for issue in result["issues"])
    bad = small_data()["policies"]
    bad.loc[0, "policy_status"] = "Frozen"
    assert any("policy_status" in issue for issue in v.validate_policies(bad)["issues"])
    assert "policy_status" in v.validate_policies(small_data()["policies"].drop(columns=["policy_status"]))["missing_columns"]


def test_validate_claims():
    """Proves: good claims pass; a negative amount and a claim filed before the accident are caught."""
    df = small_data()["claims"]
    assert v.validate_claims(df)["passed"]
    bad = df.copy()
    bad.loc[0, "claim_amount"] = -5
    bad.loc[1, "claim_date"] = "2025-01-01"
    issues = " | ".join(v.validate_claims(bad)["issues"])
    assert "claim_amount" in issues and "before the accident" in issues


def test_validate_relationships():
    """Proves: every foreign key must match a parent row - an orphan claim and an orphan payment are reported."""
    data = small_data()
    assert v.validate_relationships(data)["passed"]
    data["claims"].loc[0, "policy_id"] = "P999"
    data["payments"].loc[0, "claim_id"] = "CL999"
    result = v.validate_relationships(data)
    assert not result["passed"]
    assert len(result["issues"]) == 2
