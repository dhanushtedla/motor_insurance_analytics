 🚗 Motor Insurance Analytics

## Business scenario
A motor insurance company manages customers, vehicles, policies, claims and claim payments.
Management needs one reliable view of policy activity, premium, claim cost, settlement speed and risk.

## Business problem
Raw operational tables are not decision-ready. They must be validated, cleaned, joined, analysed and shown
in a dashboard that tells management **where to look first**.

## Objectives
Validate and clean the data -> EDA and statistics -> insurance KPIs -> patterns, insights and recommendations ->
Streamlit dashboard (with live fleet simulation) -> tests and logging -> Docker -> AWS ECR -> IAM -> EC2.

## Technology stack
Python, Pandas, NumPy, Matplotlib, Seaborn, Plotly, Jupyter, Streamlit, pytest, Git, 

## Data model and table relationships
```
customers 1 ───< policies >─── 1 vehicles
                    │ 1
                    └──< claims 1 ───< payments
```
| Table | Primary key | Foreign keys |
|---|---|---|
| customers | customer_id | - |
| vehicles | vehicle_id | customer_id |
| policies | policy_id | customer_id, vehicle_id |
| claims | claim_id | policy_id, customer_id |
| payments | payment_id | claim_id, policy_id |
Key decisions (be ready to explain them):
* `approval_date` / `settlement_date` stay empty for pending / rejected claims on purpose.
* 59 policies had an **end date before the start date** (all Cancelled). The row is kept (it has real premium and claims); only the wrong end date is blanked.
* **Approved claims = Approved + Settled** (a settled claim was approved first). Approval rate = approved / total x 100.
* `claim_amount` is the amount **requested**. Claim-to-premium = total claim amount / total premium.
* Every vehicle in this data has `vehicle_type = Car`, so vehicle comparisons use make, fuel type and vehicle age.
