"""Functions that load the five related CSV tables."""
from pathlib import Path

import pandas as pd

from src.logger import log_pipeline_step, log_error

# table name -> file name. These names are fixed by the project standard.
REQUIRED_FILES = {
    "customers": "customers.csv",
    "vehicles": "vehicles.csv",
    "policies": "policies.csv",
    "claims": "claims.csv",
    "payments": "payments.csv",
}


def check_file_exists(file_path):
    """Raise FileNotFoundError if the file is missing (never ignore a missing file)."""
    if not Path(file_path).is_file():
        log_error(f"Required file not found: {file_path}")
        raise FileNotFoundError(f"Required file not found: {file_path}")
    return True


def load_table(file_path):
    """Read one CSV file into a DataFrame."""
    check_file_exists(file_path)
    df = pd.read_csv(file_path)
    log_pipeline_step(f"Loaded {Path(file_path).name}: {df.shape[0]} rows, {df.shape[1]} columns")
    return df


def load_all_data(data_dir):
    """Load customers, vehicles, policies, claims and payments into a dictionary.

    Relationships:  customers 1--< policies >--1 vehicles,  policies 1--< claims 1--< payments
    """
    data = {}
    for table_name, file_name in REQUIRED_FILES.items():
        data[table_name] = load_table(Path(data_dir) / file_name)
    return data
