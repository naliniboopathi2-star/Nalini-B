"""
AI SMART ELECTRICAL LOAD PREDICTION
------------------------------------

This program:

1. Checks for load_history.xlsx
2. Creates a sample Excel dataset if it does not exist
3. Loads historical electrical data
4. Prepares machine-learning features
5. Trains Random Forest Regression
6. Tests the model
7. Displays MAE, RMSE and R2
8. Saves the trained model

Python:
    3.10+

Install:
    py -3.10 -m pip install pandas numpy scikit-learn openpyxl joblib

Run:
    py -3.10 train_model.py
"""

from pathlib import Path

import numpy as np
import pandas as pd
import joblib

from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score
)


# =========================================================
# PROJECT SETTINGS
# =========================================================

BASE_DIR = Path(__file__).resolve().parent

EXCEL_FILE = BASE_DIR / "load_history.xlsx"

MODEL_FILE = BASE_DIR / "load_ai_model.pkl"

TEST_RESULT_FILE = BASE_DIR / "model_test_results.xlsx"

MAX_LOAD_W = 2500.0

NUMBER_OF_SAMPLE_ROWS = 1000


# =========================================================
# MACHINE LEARNING FEATURES
# =========================================================

FEATURES = [
    "Voltage_V",
    "Current_A",
    "Power_W",
    "Load_Percentage",
    "Previous_Power_W",
    "Power_Change_W",
    "Hour",
    "Minute",
    "Day_of_Week"
]

TARGET = "Next_5min_Power_W"


# =========================================================
# CREATE SAMPLE EXCEL DATASET
# =========================================================

def create_sample_excel():

    print()
    print("Creating sample historical Excel dataset...")
    print()

    np.random.seed(42)

    n = NUMBER_OF_SAMPLE_ROWS

    time_data = pd.date_range(
        start="2026-01-01 06:00:00",
        periods=n,
        freq="5min"
    )

    t = np.arange(n)

    # -----------------------------------------------------
    # Simulated electrical load behavior
    # -----------------------------------------------------

    daily_pattern = (
        300 *
        np.sin(
            2 * np.pi * (t % 288) / 288 - 1.1
        )
    )

    short_pattern = (
        110 *
        np.sin(
            2 * np.pi * (t % 72) / 72
        )
    )

    gradual_trend = 0.35 * t

    random_noise = np.random.normal(
        0,
        35,
        n
    )

    power = (
        1100
        + daily_pattern
        + short_pattern
        + gradual_trend
        + random_noise
    )

    power = np.clip(
        power,
        400,
        2450
    )

    # -----------------------------------------------------
    # Voltage
    # -----------------------------------------------------

    voltage = (
        230
        + np.random.normal(
            0,
            1.0,
            n
        )
    )

    # -----------------------------------------------------
    # Current
    # -----------------------------------------------------

    current = power / voltage

    # -----------------------------------------------------
    # Create dataframe
    # -----------------------------------------------------

    df = pd.DataFrame({

        "Date":
            time_data.strftime("%Y-%m-%d"),

        "Time":
            time_data.strftime("%H:%M:%S"),

        "Voltage_V":
            np.round(
                voltage,
                2
            ),

        "Current_A":
            np.round(
                current,
                3
            ),

        "Power_W":
            np.round(
                power,
                1
            )
    })

    # -----------------------------------------------------
    # Machine-learning features
    # -----------------------------------------------------

    df["Load_Percentage"] = np.round(
        (
            df["Power_W"]
            / MAX_LOAD_W
        ) * 100,
        2
    )

    df["Previous_Power_W"] = (
        df["Power_W"].shift(1)
    )

    df["Power_Change_W"] = (
        df["Power_W"].diff()
    )

    df["Hour"] = time_data.hour

    df["Minute"] = time_data.minute

    df["Day_of_Week"] = (
        time_data.dayofweek
    )

    # -----------------------------------------------------
    # Target
    # Next 5-minute power
    # -----------------------------------------------------

    df["Next_5min_Power_W"] = (
        df["Power_W"].shift(-1)
    )

    # Remove first/last invalid records
    df = df.dropna().reset_index(
        drop=True
    )

    # -----------------------------------------------------
    # Save Excel
    # -----------------------------------------------------

    df.to_excel(
        EXCEL_FILE,
        index=False
    )

    print(
        "Sample Excel file created:"
    )

    print(EXCEL_FILE)

    print()

    print(
        "Number of records:",
        len(df)
    )

    print()

    print(
        df.head(10).to_string(
            index=False
        )
    )

    return df


# =========================================================
# LOAD EXCEL
# =========================================================

def load_excel():

    if not EXCEL_FILE.exists():

        return create_sample_excel()

    print()
    print(
        "Existing Excel file found:"
    )
    print(EXCEL_FILE)

    df = pd.read_excel(
        EXCEL_FILE
    )

    return df


# =========================================================
# CHECK DATA
# =========================================================

def validate_data(df):

    required_columns = (
        FEATURES
        + [TARGET]
    )

    missing_columns = [
        column
        for column in required_columns
        if column not in df.columns
    ]

    if missing_columns:

        print()
        print(
            "ERROR: Missing Excel columns:"
        )

        for column in missing_columns:
            print(
                " -",
                column
            )

        raise ValueError(
            "Excel file does not contain "
            "all required columns."
        )

    # Convert required fields to numbers

    for column in required_columns:

        df[column] = pd.to_numeric(
            df[column],
            errors="coerce"
        )

    # Remove invalid rows

    df = df.dropna(
        subset=required_columns
    )

    df = df.reset_index(
        drop=True
    )

    if len(df) < 50:

        raise ValueError(
            "At least 50 valid records "
            "are required for training."
        )

    return df


# =========================================================
# TRAIN MODEL
# =========================================================

def train_model(df):

    print()
    print("=" * 60)
    print(
        "AI ELECTRICAL LOAD PREDICTION"
    )
    print(
        "RANDOM FOREST TRAINING"
    )
    print("=" * 60)

    # -----------------------------------------------------
    # Time ordered split
    # -----------------------------------------------------

    split_index = int(
        len(df) * 0.80
    )

    train_df = df.iloc[
        :split_index
    ]

    test_df = df.iloc[
        split_index:
    ]

    X_train = train_df[
        FEATURES
    ]

    y_train = train_df[
        TARGET
    ]

    X_test = test_df[
        FEATURES
    ]

    y_test = test_df[
        TARGET
    ]

    print()
    print(
        "Training records:",
        len(train_df)
    )

    print(
        "Testing records :",
        len(test_df)
    )

    # -----------------------------------------------------
    # Random Forest
    # -----------------------------------------------------

    model = RandomForestRegressor(

        n_estimators=250,

        max_depth=14,

        min_samples_leaf=2,

        random_state=42,

        n_jobs=-1
    )

    print()
    print(
        "Training AI model..."
    )

    model.fit(
        X_train,
        y_train
    )

    print(
        "Training completed."
    )

    # -----------------------------------------------------
    # Prediction
    # -----------------------------------------------------

    predictions = model.predict(
        X_test
    )

    # -----------------------------------------------------
    # Evaluation
    # -----------------------------------------------------

    mae = mean_absolute_error(
        y_test,
        predictions
    )

    rmse = np.sqrt(
        mean_squared_error(
            y_test,
            predictions
        )
    )

    r2 = r2_score(
        y_test,
        predictions
    )

    print()
    print("=" * 60)
    print(
        "MODEL PERFORMANCE"
    )
    print("=" * 60)

    print(
        f"MAE  : {mae:.2f} W"
    )

    print(
        f"RMSE : {rmse:.2f} W"
    )

    print(
        f"R2   : {r2:.4f}"
    )

    print("=" * 60)

    # -----------------------------------------------------
    # Feature importance
    # -----------------------------------------------------

    importance = pd.Series(

        model.feature_importances_,

        index=FEATURES

    ).sort_values(
        ascending=False
    )

    print()
    print(
        "FEATURE IMPORTANCE"
    )

    print(
        importance.to_string()
    )

    # -----------------------------------------------------
    # Save model
    # -----------------------------------------------------

    model_package = {

        "model":
            model,

        "features":
            FEATURES,

        "target":
            TARGET,

        "max_load_w":
            MAX_LOAD_W,

        "mae":
            float(mae),

        "rmse":
            float(rmse),

        "r2":
            float(r2),

        "feature_importance":
            importance.to_dict(),

        "training_rows":
            len(train_df),

        "testing_rows":
            len(test_df)
    }

    joblib.dump(
        model_package,
        MODEL_FILE
    )

    print()
    print(
        "AI model saved:"
    )

    print(
        MODEL_FILE
    )

    # -----------------------------------------------------
    # Save test results
    # -----------------------------------------------------

    result = test_df[
        [
            "Date",
            "Time",
            "Power_W",
            TARGET
        ]
    ].copy()

    result[
        "AI_Predicted_Power_W"
    ] = np.round(
        predictions,
        2
    )

    result[
        "Absolute_Error_W"
    ] = np.round(
        abs(
            result[TARGET]
            -
            result[
                "AI_Predicted_Power_W"
            ]
        ),
        2
    )

    result.to_excel(
        TEST_RESULT_FILE,
        index=False
    )

    print()
    print(
        "Test results saved:"
    )

    print(
        TEST_RESULT_FILE
    )

    return model_package


# =========================================================
# MAIN
# =========================================================

def main():

    print()
    print("=" * 60)
    print(
        "AI SMART ELECTRICAL LOAD SYSTEM"
    )
    print("=" * 60)

    df = load_excel()

    df = validate_data(
        df
    )

    train_model(
        df
    )

    print()
    print("=" * 60)
    print(
        "PROJECT TRAINING COMPLETED"
    )
    print("=" * 60)

    print()
    print(
        "Next step:"
    )

    print(
        "Run: py -3.10 ai_load_monitor.py"
    )

    print()


if __name__ == "__main__":

    main()