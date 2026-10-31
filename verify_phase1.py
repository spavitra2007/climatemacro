
from pathlib import Path
import pandas as pd

DATA_PATH = Path("data/processed/weather_daily.csv")
FORECAST_PATH = Path("outputs/models/january_2026_forecast.csv")

print("=" * 55)
print("PHASE 1: DATASET AND FORECAST VERIFICATION")
print("=" * 55)

# 1. Verify the historical dataset
if not DATA_PATH.exists():
    raise FileNotFoundError(f"Dataset not found: {DATA_PATH}")

df = pd.read_csv(DATA_PATH, parse_dates=["time"])
df = df.sort_values("time").reset_index(drop=True)

rain_col = "precipitation_sum (mm)"

print("\n1. HISTORICAL DATASET")
print("Rows:", len(df))
print("Columns:", len(df.columns))
print("Start date:", df["time"].min().date())
print("End date:", df["time"].max().date())
print("Missing values:", int(df.isna().sum().sum()))
print("Duplicate dates:", int(df["time"].duplicated().sum()))

if df["time"].max().date() != pd.Timestamp("2025-12-31").date():
    print("WARNING: Dataset does not end on 2025-12-31.")
else:
    print("PASS: Dataset ends on 2025-12-31.")

# 2. Verify the saved forecast
print("\n2. JANUARY 1, 2026 FORECAST")

if not FORECAST_PATH.exists():
    raise FileNotFoundError(f"Forecast file not found: {FORECAST_PATH}")

forecast_df = pd.read_csv(
    FORECAST_PATH,
    parse_dates=["forecast_date"]
)

print(forecast_df.to_string(index=False))

expected_date = pd.Timestamp("2026-01-01")
matching = forecast_df[
    forecast_df["forecast_date"].dt.normalize() == expected_date
]

if matching.empty:
    print("FAIL: January 1, 2026 forecast is missing.")
else:
    prediction = float(matching["predicted_rainfall_mm"].iloc[0])
    print(f"PASS: Forecast exists: {prediction:.2f} mm")

# 3. Check whether actual rainfall is available
print("\n3. ACTUAL RAINFALL VERIFICATION")

actual = df[df["time"].dt.normalize() == expected_date]

if actual.empty:
    print("Actual January 1, 2026 rainfall is NOT in this dataset.")
    print("The 0.01 mm prediction cannot be verified against this file.")
else:
    actual_rainfall = actual[rain_col].iloc[0]
    print(f"Actual rainfall: {actual_rainfall:.2f} mm")

    if not matching.empty:
        error = abs(prediction - actual_rainfall)
        print(f"Absolute prediction error: {error:.2f} mm")

print("\nVerification complete.")
