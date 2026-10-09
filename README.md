# 🚗 Motor Insurance Analytics

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
Python, Pandas, NumPy, Matplotlib, Seaborn, Plotly, Jupyter, Streamlit, pytest, Git, Docker, AWS (ECR, IAM, EC2).

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

## Project structure
```
motor_insurance_analytics/
├── data/raw/            original CSV files (never changed)
├── data/cleaned/        *_cleaned.csv created by the pipeline
├── notebooks/insurance_analysis.ipynb
├── src/                 data_loader, validation, data_cleaner, insurance_analysis,
│                        visualization, insights, simulation, logger
├── app/streamlit_app.py dashboard
├── reports/business_report.md   (generated from the data)
├── tests/               test_pipeline, test_analysis, test_validation
├── logs/pipeline.log
├── run_pipeline.py  requirements.txt  Dockerfile  .dockerignore  .gitignore
```

## Installation
```bash
python -m venv .venv
.venv\Scripts\activate          # Windows      (Mac/Linux: source .venv/bin/activate)
pip install -r requirements.txt
```

## Data cleaning pipeline
```bash
python run_pipeline.py
```
`load_all_data -> validate_all_tables -> clean_data (missing values -> duplicates -> text -> dates -> numbers ->
business rules -> derived columns) -> save_cleaned_data -> reports/business_report.md`

Key decisions (be ready to explain them):
* `approval_date` / `settlement_date` stay empty for pending / rejected claims on purpose.
* 59 policies had an **end date before the start date** (all Cancelled). The row is kept (it has real premium and claims); only the wrong end date is blanked.
* **Approved claims = Approved + Settled** (a settled claim was approved first). Approval rate = approved / total x 100.
* `claim_amount` is the amount **requested**. Claim-to-premium = total claim amount / total premium.
* Every vehicle in this data has `vehicle_type = Car`, so vehicle comparisons use make, fuel type and vehicle age.

## How to run tests
```bash
pytest -v
```

## How to run Streamlit locally
```bash
streamlit run app/streamlit_app.py
```
Pages: Executive Overview, Policy, Claims (damage severity pie charts), Customer, Vehicle, Premium & Risk,
Insights & Recommendations, **Live Fleet Simulation**.
Sidebar filters change every KPI, chart, insight and the simulation. *Empty filter = show all.*
Use **↺ Reset filters** if you ever see "No claims match".
Download buttons: filtered claims / policies (CSV), business report (Markdown), simulated claim events (CSV).

### Live Fleet Simulation (real-time scenario)
Real **active policies** are placed on a map of India. Each vehicle drives between cities. Accidents occur with the
claim frequency of its policy type, and every accident creates a live claim (FNOL) with claim type, severity, amount
(all sampled from your historical claims), expected payout and an action: *Fast-track* or *REVIEW* (claim > 10x premium).
1 second = 1 simulated day. It is a **simulation**, not real telematics data.

## Docker instructions
```bash
docker build -t motor-insurance-analytics .
docker run -p 8501:8501 motor-insurance-analytics
```
Open http://localhost:8501

## AWS deployment overview
`Docker image -> Amazon ECR -> EC2 pulls image -> container runs Streamlit on 8501 -> Security Group opens 8501 -> public URL`

1. **ECR** (stores your image so EC2 can pull it)
```bash
aws ecr create-repository --repository-name motor-insurance-analytics --region ap-south-1
aws ecr get-login-password --region ap-south-1 | docker login --username AWS --password-stdin <ACCOUNT_ID>.dkr.ecr.ap-south-1.amazonaws.com
docker tag motor-insurance-analytics:latest <ACCOUNT_ID>.dkr.ecr.ap-south-1.amazonaws.com/motor-insurance-analytics:latest
docker push <ACCOUNT_ID>.dkr.ecr.ap-south-1.amazonaws.com/motor-insurance-analytics:latest
```
2. **IAM (least privilege, no keys in code or images)**
   * Your push user/role: `ecr:GetAuthorizationToken` and the push actions on this one repository only
     (`BatchCheckLayerAvailability, InitiateLayerUpload, UploadLayerPart, CompleteLayerUpload, PutImage`).
   * EC2 instance role (instance profile): read-only pull access, e.g. managed policy `AmazonEC2ContainerRegistryReadOnly`.
3. **EC2**: Amazon Linux 2023, t3.small, attach the instance role, Security Group inbound: TCP **8501** (app) and TCP 22 (SSH, **your IP only**).
```bash
sudo dnf install -y docker && sudo systemctl enable --now docker
aws ecr get-login-password --region ap-south-1 | sudo docker login --username AWS --password-stdin <ACCOUNT_ID>.dkr.ecr.ap-south-1.amazonaws.com
sudo docker run -d --restart unless-stopped -p 8501:8501 <ACCOUNT_ID>.dkr.ecr.ap-south-1.amazonaws.com/motor-insurance-analytics:latest
```
4. Open `http://<EC2-PUBLIC-IP>:8501` from another device, test the filters, then submit the URL in the admin Google Form.

## Git
```bash
git init
git add . && git commit -m "Add raw data and project structure"
# commit again after each milestone: pipeline, analysis, dashboard, tests, docker, docs
```

## Key KPIs
Total / Active policies, Total / Average premium, Total claims, Total / Average claim amount, Approval and Rejection rate,
Average settlement days, Claim-to-premium ratio, Paid claim ratio.

## Business questions
Answered in the notebook (section 14) and on the dashboard pages.

## Important insights (from the full data set - the dashboard recalculates them for any filter)
* **Third Party** policies have a claim-to-premium ratio of about **11.7** versus **3.6** for the portfolio.
* About **38%** of claims are more than **10x** the policy premium and make up about **64%** of claim cost.
* Only about **39%** of policies reaching their end date were renewed.
* High-damage claims are about 18% of claims but about 42% of claim cost.

## Recommendations
Review Third Party pricing and coverage limits first; add a review step for claims above 10x premium; start renewal
outreach before policy end dates; clear the pending-claim backlog, oldest claims first.
(The ranked list is generated live on the *Insights & Recommendations* page.)

## Live application URL
`http://<EC2-PUBLIC-IP>:8501`   <- replace after deployment
