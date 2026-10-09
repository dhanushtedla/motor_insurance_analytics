"""Pipeline entry point.  Run:  python run_pipeline.py

load -> validate -> clean -> save cleaned tables -> write business report
"""
from pathlib import Path

from src.data_loader import load_all_data
from src.validation import validate_all_tables
from src.data_cleaner import clean_data, save_cleaned_data
from src.insurance_analysis import build_policy_master, build_claims_master
from src.insights import generate_business_report
from src.logger import setup_logger, log_pipeline_step, log_error

ROOT = Path(__file__).resolve().parent
RAW_DIR = ROOT / "data" / "raw"
CLEANED_DIR = ROOT / "data" / "cleaned"
REPORT_PATH = ROOT / "reports" / "business_report.md"


def run_pipeline(raw_dir=RAW_DIR, cleaned_dir=CLEANED_DIR, report_path=REPORT_PATH):
    """Run the full pipeline and return the cleaned data dictionary."""
    setup_logger()
    log_pipeline_step("Pipeline started")
    try:
        data = load_all_data(raw_dir)

        report = validate_all_tables(data)
        if report["has_missing_columns"]:
            raise ValueError("Required columns are missing - fix the raw files before cleaning.")

        cleaned = clean_data(data)
        save_cleaned_data(cleaned, cleaned_dir)

        masters = {"policies": build_policy_master(cleaned), "claims": build_claims_master(cleaned),
                   "payments": cleaned["payments"]}
        Path(report_path).parent.mkdir(parents=True, exist_ok=True)
        Path(report_path).write_text(generate_business_report(masters, report), encoding="utf-8")
        log_pipeline_step(f"Business report written to {report_path}")
        log_pipeline_step("Pipeline completed successfully")
        return cleaned
    except Exception as error:                      # log the real reason, then stop
        log_error(f"Pipeline failed: {type(error).__name__}: {error}")
        raise


if __name__ == "__main__":
    run_pipeline()
