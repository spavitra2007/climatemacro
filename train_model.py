
from pathlib import Path

import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.dummy import DummyRegressor

DATA_PATH = Path("data/processed/weather_daily.csv")
OUTPUT_DIR = Path("outputs/models")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

df = pd.read_csv(DATA_PATH, parse_dates=["time"])
df = df.sort_values("time").reset_index(drop=True)

rain = "precipitation_sum (mm)"

# Predict the following day's rainfall.
df["target_tomorrow_mm"] = df[rain].shift(-1)

# Use today's weather and past rainfall only.
feature_cols = [
    "temperature_2m_mean (°C)",
    "temperature_2m_max (°C)",
    "wind_speed_10m_max (km/h)",
    "rain_sum (mm)",
    "precipitation_hours (h)",
    "apparent_temperature_mean (°C)",
    "relative_humidity_2m_mean (%)",
    "pressure_msl_mean (hPa)",
    "cloud_cover_mean (%)",
]

# Add calendar and past-rainfall features.
df["month"] = df["time"].dt.month
df["day_of_year"] = df["time"].dt.dayofyear
feature_cols += ["month", "day_of_year"]

for lag in [1, 2, 3, 7]:
    col = f"rain_lag_{lag}"
    df[col] = df[rain].shift(lag)
    feature_cols.append(col)

df = df.dropna(subset=feature_cols + ["target_tomorrow_mm"]).copy()

# Chronological 80/20 split — never shuffle time-series data.
split = int(len(df) * 0.8)
train = df.iloc[:split]
test = df.iloc[split:]

X_train = train[feature_cols]
y_train = train["target_tomorrow_mm"]
X_test = test[feature_cols]
y_test = test["target_tomorrow_mm"]

# Baseline: always predict average rainfall from training data.
baseline = DummyRegressor(strategy="mean")
baseline.fit(X_train, y_train)
baseline_pred = baseline.predict(X_test)

# Random Forest model.
model = RandomForestRegressor(
    n_estimators=200,
    max_depth=12,
    min_samples_leaf=3,
    random_state=42,
    n_jobs=-1,
)
model.fit(X_train, y_train)
predictions = np.maximum(model.predict(X_test), 0)

def report(name, actual, predicted):
    print(f"\n{name}")
    print("MAE (mm):", round(mean_absolute_error(actual, predicted), 3))
    print("RMSE (mm):", round(np.sqrt(mean_squared_error(actual, predicted)), 3))
    print("R²:", round(r2_score(actual, predicted), 3))

print("Training period:", train["time"].min().date(), "to",
      train["time"].max().date())
print("Testing period:", test["time"].min().date(), "to",
      test["time"].max().date())
print("Training rows:", len(train))
print("Testing rows:", len(test))

report("BASELINE MODEL", y_test, baseline_pred)
report("RANDOM FOREST MODEL", y_test, predictions)

# Save test predictions for dashboard development.
results = pd.DataFrame({
    "date": test["time"].values + pd.Timedelta(days=1),
    "actual_rainfall_mm": y_test.values,
    "predicted_rainfall_mm": predictions,
})

results.to_csv(OUTPUT_DIR / "rainfall_predictions.csv", index=False)

# Save feature importance for interpretation.
importance = pd.DataFrame({
    "feature": feature_cols,
    "importance": model.feature_importances_,
}).sort_values("importance", ascending=False)

importance.to_csv(OUTPUT_DIR / "feature_importance.csv", index=False)

print("\nTop 5 features:")
print(importance.head().to_string(index=False))
print("\nSaved prediction results to:", OUTPUT_DIR)


# ==========================================
# FINAL MODEL: PREDICT RAINFALL FOR 2026-01-01
# ==========================================

# Rebuild the dataset with all available historical features.
# The final row has no next-day target, so exclude it from training.
full_df = pd.read_csv(DATA_PATH, parse_dates=["time"])
full_df = full_df.sort_values("time").reset_index(drop=True)

full_df["month"] = full_df["time"].dt.month
full_df["day_of_year"] = full_df["time"].dt.dayofyear

for lag in [1, 2, 3, 7]:
    full_df[f"rain_lag_{lag}"] = full_df[rain].shift(lag)

full_df["target_tomorrow_mm"] = full_df[rain].shift(-1)

# Train on every historical row with a known next-day rainfall target.
final_train = full_df.dropna(
    subset=feature_cols + ["target_tomorrow_mm"]
)

final_model = RandomForestRegressor(
    n_estimators=200,
    max_depth=12,
    min_samples_leaf=3,
    random_state=42,
    n_jobs=-1,
)

final_model.fit(
    final_train[feature_cols],
    final_train["target_tomorrow_mm"],
)

# Use weather observations from the final available date.
latest_row = full_df.iloc[[-1]]
latest_features = latest_row[feature_cols]

if latest_features.isna().any().any():
    raise ValueError("The latest day's forecast features contain missing values.")

forecast = max(0, final_model.predict(latest_features)[0])
latest_date = latest_row["time"].iloc[0]
forecast_date = latest_date + pd.Timedelta(days=1)

print("\nFINAL RAINFALL FORECAST")
print("Last observed date:", latest_date.date())
print("Forecast date:", forecast_date.date())
print(f"Predicted rainfall: {forecast:.2f} mm")

forecast_result = pd.DataFrame({
    "forecast_date": [forecast_date],
    "predicted_rainfall_mm": [forecast],
})

forecast_result.to_csv(
    OUTPUT_DIR / "january_2026_forecast.csv",
    index=False,
)

print(
    "Forecast saved to:",
    OUTPUT_DIR / "january_2026_forecast.csv",
)

