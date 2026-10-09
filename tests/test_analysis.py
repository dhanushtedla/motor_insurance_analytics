"""Tests for the KPI functions (expected values are worked out by hand from tests/helpers.py)."""
import pandas as pd

from helpers import small_data
from src import insurance_analysis as ia

# Claims: CL1 Approved 3000 | CL2 Rejected 1000 | CL3 Settled 2000 | CL4 Pending 4000
# Policies: P1 Active 1000 | P2 Expired 500 | P3 Cancelled 1500


def test_calculate_total_policies():
    """Proves: counts unique policy ids (a repeated id is not counted twice)."""
    pol = pd.concat([small_data()["policies"], small_data()["policies"].iloc[[0]]])
    assert ia.calculate_total_policies(pol) == 3


def test_calculate_active_policies():
    """Proves: only policies with status Active are counted."""
    assert ia.calculate_active_policies(small_data()["policies"]) == 1


def test_calculate_total_claims():
    """Proves: counts unique claims."""
    assert ia.calculate_total_claims(small_data()["claims"]) == 4


def test_calculate_total_premium():
    """Proves: premium is the plain sum 1000 + 500 + 1500."""
    assert ia.calculate_total_premium(small_data()["policies"]) == 3000


def test_calculate_claim_approval_rate():
    """Proves: (Approved + Settled) / total x 100 = 2 / 4 = 50, and an empty table gives 0 (no crash)."""
    claims = small_data()["claims"]
    assert ia.calculate_claim_approval_rate(claims) == 50.0
    assert ia.calculate_claim_approval_rate(claims.iloc[0:0]) == 0.0


def test_calculate_average_claim_amount():
    """Proves: (3000 + 1000 + 2000 + 4000) / 4 = 2500."""
    assert ia.calculate_average_claim_amount(small_data()["claims"]) == 2500
