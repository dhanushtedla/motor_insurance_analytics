# Motor Insurance Business Report

_Generated: 09 Oct 2026_

## 1. Executive Summary

This report is calculated from the cleaned motor-insurance tables. All numbers below come from the data.

## 2. Business Problem

Management needs a reliable view of policy activity, premium, claim cost, settlement speed and risk.

## 3. Data and Table Summary

Policies: 25,000 | Claims: 10,000 | Payments: 7,000

## 4. Data Quality Findings

- **customers**: passed
- **vehicles**: passed
- **policies**: issues -> 59 policies end before they start
- **claims**: passed
- **payments**: passed
- **relationships**: passed

## 5. Cleaning Performed

Missing ids dropped, duplicates removed, text trimmed, dates converted, amounts checked, business rules applied (wrong end dates blanked) and derived columns added.

## 6. KPI Summary

| KPI | Value |
|---|---|
| Total policies | 25,000 |
| Active policies | 7,551 |
| Total premium | ₹79.56 Cr |
| Average premium | ₹31,823 |
| Total claims | 10,000 |
| Total claim amount | ₹288.54 Cr |
| Average claim amount | ₹2.89 L |
| Claim approval rate | 70.5% |
| Claim rejection rate | 11.6% |
| Average settlement days | 23.9 |
| Claim-to-premium ratio | 3.63 |
| Paid claim ratio | 0.87 |

## 7. EDA Findings

| metric                |      mean |   median |   mode |     variance |   std_dev |   skewness |
|:----------------------|----------:|---------:|-------:|-------------:|----------:|-----------:|
| premium_amount        |  31822.8  |  28917.7 | 100000 |  3.27588e+08 |  18099.4  |       0.86 |
| claim_amount          | 288544    | 205040   | 239364 |  6.91943e+10 | 263048    |       1.95 |
| claim_settlement_days |     23.93 |     24   |     25 | 96.96        |      9.85 |      -0.18 |

## 8. Important Patterns

**PATTERN:** Third Party has a claim-to-premium ratio of 11.71 (portfolio 3.63)

**EVIDENCE:** Premium ₹7.55 Cr vs claims ₹88.41 Cr on 6,215 policies.

**BUSINESS MEANING:** A ratio above 1 means claims requested are larger than the premium collected for this product.

**RECOMMENDATION:** Investigate Third Party pricing, coverage limits and claim approval rules first.

---

**PATTERN:** Riskiest segment: Third Party + Tata (ratio 12.13)

**EVIDENCE:** 1,258 policies, premium ₹1.49 Cr, claims ₹18.09 Cr; portfolio ratio 3.63.

**BUSINESS MEANING:** This combination is a concentrated pocket of high claim cost.

**RECOMMENDATION:** Review pricing and approval checks for this segment before the next renewal cycle.

---

**PATTERN:** West Bengal has the highest claim frequency (0.42 claims per policy)

**EVIDENCE:** Portfolio average = 0.40. West Bengal: 318 claims on 764 policies.

**BUSINESS MEANING:** A region with higher claim frequency than the average is a geographic risk hot-spot.

**RECOMMENDATION:** Investigate road, theft and fraud conditions in West Bengal; consider regional pricing.

---

**PATTERN:** 38.2% of claims are more than 10 times the policy premium

**EVIDENCE:** 3,821 claims, total ₹185.64 Cr (64.3% of claim cost).

**BUSINESS MEANING:** Very large claims against small premiums erode profit quickly.

**RECOMMENDATION:** Add a review step for claims above 10x premium and check them for fraud and coverage limits.

---

## 9. Business Insights

**PATTERN:** Only 38.9% of policies that reached their end date were renewed

**EVIDENCE:** Renewed = 6,665, Expired (not renewed) = 10,464, Cancelled = 320 out of 25,000 policies. Active policies = 7,551 (30.2%).

**BUSINESS MEANING:** Every non-renewed policy is premium the insurer has to win again; low renewal means higher acquisition cost.

**RECOMMENDATION:** Contact expired-policy customers early (before end date) with renewal offers; study why policies get cancelled.

---

**PATTERN:** Comprehensive dominates the portfolio with 60.3% of policies

**EVIDENCE:** Comprehensive: 15,085 policies. Third Party: 6,215, Zero Depreciation: 3,700

**BUSINESS MEANING:** A portfolio concentrated in one product depends heavily on that product's claim behaviour.

**RECOMMENDATION:** Check the claim-to-premium ratio of this product before growing it further; consider balancing the mix.

---

**PATTERN:** 17.9% of claims are still pending

**EVIDENCE:** 1,791 pending claims worth ₹50.83 Cr; 1,616 of them are older than 30 days (latest claim date in view: 08 Oct 2026).

**BUSINESS MEANING:** Pending claims are a liability not yet decided and old ones hurt customer satisfaction.

**RECOMMENDATION:** Prioritise pending claims older than 30 days and check what is delaying approval.

---

**PATTERN:** Natural Disaster claims are rejected most often (12.7% vs 11.6% overall)

**EVIDENCE:** Rejected claims = 1,160 worth ₹34.32 Cr. Rejection rate for Natural Disaster = 12.7%.

**BUSINESS MEANING:** A high rejection rate can mean unclear policy terms or possible fraud-screening working well.

**RECOMMENDATION:** Review rejection reasons for Natural Disaster claims and make sure rejections are consistent and explainable.

---

**PATTERN:** High-damage claims are 18.1% of claims but 42.1% of claim cost

**EVIDENCE:** High severity: 1,814 claims, ₹121.62 Cr of ₹288.54 Cr total.

**BUSINESS MEANING:** A small group of severe claims drives a disproportionate part of the cost.

**RECOMMENDATION:** Focus inspection, repair-network negotiation and fraud checks on high-severity claims.

---

**PATTERN:** Fire has the highest average claim (₹2.99 L)

**EVIDENCE:** Portfolio average claim = ₹2.89 L; Fire is 1.04x that average (759 claims).

**BUSINESS MEANING:** This claim type is the most expensive each time it happens.

**RECOMMENDATION:** Review underwriting and settlement limits for Fire claims.

---

**PATTERN:** Theft claims take the longest to settle (24.1 days)

**EVIDENCE:** Average over all settled claims = 23.9 days; fastest type = Natural Disaster (23.2 days).

**BUSINESS MEANING:** Slow settlement lowers customer trust and can raise complaints.

**RECOMMENDATION:** Look at the settlement steps for Theft claims and remove the slowest step.

---

**PATTERN:** Comprehensive brings in the most premium (68.5% of ₹79.56 Cr)

**EVIDENCE:** Comprehensive: ₹54.50 Cr from 15,085 policies, average ₹36,126. Highest average premium = Zero Depreciation (₹47,318).

**BUSINESS MEANING:** Premium income depends on this product, so its pricing accuracy matters most.

**RECOMMENDATION:** Monitor this product's claim ratio monthly and re-price when it drifts above the portfolio average.

---

**PATTERN:** The top 10% of policies contribute 21.8% of total premium

**EVIDENCE:** Top 10% = 2,500 policies; median premium = ₹28,918, mean = ₹31,823.

**BUSINESS MEANING:** Premium income is concentrated in a smaller set of large policies.

**RECOMMENDATION:** Protect these high-premium customers with renewal care and watch their claim behaviour.

---

**PATTERN:** Premium written in the last 6 months is down 10.8% versus the 6 months before

**EVIDENCE:** Last 6 months = ₹12.12 Cr, previous 6 months = ₹13.58 Cr.

**BUSINESS MEANING:** Falling new premium means slower business growth; rising premium means growth that needs matching claims control.

**RECOMMENDATION:** Find which policy type or region explains the change and respond with sales or pricing action.

---

**PATTERN:** Age group 56-65 files the most claims per policy (0.41)

**EVIDENCE:** Portfolio average = 0.40 claims per policy; this group has 4,753 policies and 1,944 claims.

**BUSINESS MEANING:** Claim frequency differs by customer age, so age is a useful risk signal.

**RECOMMENDATION:** Test age-based pricing or driver-awareness programmes for this group.

---

**PATTERN:** Age group 36-45 has the highest average claim (₹2.92 L)

**EVIDENCE:** Overall average claim = ₹2.89 L; 1,897 claims in this group.

**BUSINESS MEANING:** Older / younger segments can be more expensive per claim even if they claim less often.

**RECOMMENDATION:** Compare the premium charged to this age group with the claim cost it creates.

---

**PATTERN:** Software Engineer customers account for 9.8% of claim cost

**EVIDENCE:** Software Engineer: 980 claims, ₹28.37 Cr.

**BUSINESS MEANING:** Some customer groups contribute a large share of total claim cost.

**RECOMMENDATION:** Check whether this group's share of premium matches its share of claim cost.

---

**PATTERN:** Maruti Suzuki generates 31.5% of claim value but is 38.0% of policies

**EVIDENCE:** Maruti Suzuki: 3,820 claims, ₹91.00 Cr, average claim ₹2.38 L.

**BUSINESS MEANING:** If claim share is higher than policy share, this make is costing more than its weight in the portfolio.

**RECOMMENDATION:** Review underwriting and repair costs for Maruti Suzuki vehicles.

---

**PATTERN:** CNG vehicles have the highest claim-to-premium ratio (3.74)

**EVIDENCE:** Lowest = Electric (3.44). CNG has 4,005 policies and 0.40 claims per policy.

**BUSINESS MEANING:** Fuel type changes repair cost and claim cost, so premium should reflect it.

**RECOMMENDATION:** Check whether CNG premiums cover the claim cost they create.

---

**PATTERN:** Vehicles aged 0-2 yrs have the highest claim-to-premium ratio (3.69)

**EVIDENCE:** Lowest group = 6-8 yrs (3.55). Difference = 0.15.

**BUSINESS MEANING:** If the gap between age groups is small, vehicle age is not a strong risk driver in this data.

**RECOMMENDATION:** Do not add a vehicle-age loading unless the gap is meaningful after more data is collected.

---

## 10. Recommendations

**PATTERN:** Priority 1: Riskiest segment: Third Party + Tata (ratio 12.13)

**EVIDENCE:** 1,258 policies, premium ₹1.49 Cr, claims ₹18.09 Cr; portfolio ratio 3.63.

**BUSINESS MEANING:** This combination is a concentrated pocket of high claim cost.

**RECOMMENDATION:** Review pricing and approval checks for this segment before the next renewal cycle.

---

**PATTERN:** Priority 2: Third Party has a claim-to-premium ratio of 11.71 (portfolio 3.63)

**EVIDENCE:** Premium ₹7.55 Cr vs claims ₹88.41 Cr on 6,215 policies.

**BUSINESS MEANING:** A ratio above 1 means claims requested are larger than the premium collected for this product.

**RECOMMENDATION:** Investigate Third Party pricing, coverage limits and claim approval rules first.

---

**PATTERN:** Priority 3: Only 38.9% of policies that reached their end date were renewed

**EVIDENCE:** Renewed = 6,665, Expired (not renewed) = 10,464, Cancelled = 320 out of 25,000 policies. Active policies = 7,551 (30.2%).

**BUSINESS MEANING:** Every non-renewed policy is premium the insurer has to win again; low renewal means higher acquisition cost.

**RECOMMENDATION:** Contact expired-policy customers early (before end date) with renewal offers; study why policies get cancelled.

---

**PATTERN:** Priority 4: 38.2% of claims are more than 10 times the policy premium

**EVIDENCE:** 3,821 claims, total ₹185.64 Cr (64.3% of claim cost).

**BUSINESS MEANING:** Very large claims against small premiums erode profit quickly.

**RECOMMENDATION:** Add a review step for claims above 10x premium and check them for fraud and coverage limits.

---

**PATTERN:** Priority 5: Comprehensive brings in the most premium (68.5% of ₹79.56 Cr)

**EVIDENCE:** Comprehensive: ₹54.50 Cr from 15,085 policies, average ₹36,126. Highest average premium = Zero Depreciation (₹47,318).

**BUSINESS MEANING:** Premium income depends on this product, so its pricing accuracy matters most.

**RECOMMENDATION:** Monitor this product's claim ratio monthly and re-price when it drifts above the portfolio average.

---

## 11. Dashboard Summary

Seven pages (Executive Overview, Policy, Claims, Customer, Vehicle, Premium & Risk, Insights) plus a Live Fleet Simulation page. Sidebar filters update every KPI, chart and insight.

## 12. Deployment Summary

Docker image -> Amazon ECR -> EC2 -> Streamlit on port 8501.

## 13. Conclusion

The portfolio shows clear claim-cost pockets (see Important Patterns). Act on the ranked recommendations first.