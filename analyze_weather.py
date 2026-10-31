
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

data_path = Path("data/processed/weather_daily.csv")
output_dir = Path("outputs/eda")
output_dir.mkdir(parents=True, exist_ok=True)

df = pd.read_csv(data_path, parse_dates=["time"])
df = df.sort_values("time").reset_index(drop=True)

rain_col = "precipitation_sum (mm)"
temp_col = "temperature_2m_mean (°C)"

# Basic quality checks
print("===== DATA QUALITY =====")
print("Rows:", len(df))
print("Date range:", df["time"].min(), "to", df["time"].max())
print("Duplicate dates:", df["time"].duplicated().sum())
print("Missing values:", int(df.isna().sum().sum()))
print("Negative rainfall records:", int((df[rain_col] < 0).sum()))

# Rainfall statistics
print("\n===== RAINFALL STATISTICS =====")
print(df[rain_col].describe())
print("Days with rainfall:", int((df[rain_col] > 0).sum()))
print("Rainfall total (mm):", round(df[rain_col].sum(), 2))

# Monthly and annual summaries
df["year"] = df["time"].dt.year
df["month"] = df["time"].dt.month

monthly = df.groupby("month")[rain_col].mean()
annual = df.groupby("year")[rain_col].sum()

print("\n===== AVERAGE DAILY RAINFALL BY MONTH =====")
print(monthly.round(2))

print("\n===== ANNUAL RAINFALL TOTALS =====")
print(annual.round(2))

# Plot 1: Average daily rainfall by month
plt.figure(figsize=(10, 5))
monthly.plot(kind="bar")
plt.title("Pune: Average Daily Rainfall by Month (2010–2025)")
plt.xlabel("Month")
plt.ylabel("Average rainfall (mm/day)")
plt.tight_layout()
plt.savefig(output_dir / "monthly_rainfall.png", dpi=150)
plt.close()

# Plot 2: Annual rainfall totals
plt.figure(figsize=(12, 5))
annual.plot(kind="line", marker="o")
plt.title("Pune: Annual Rainfall Totals (2010–2025)")
plt.xlabel("Year")
plt.ylabel("Total rainfall (mm)")
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig(output_dir / "annual_rainfall.png", dpi=150)
plt.close()

# Plot 3: Daily rainfall distribution
plt.figure(figsize=(10, 5))
df[rain_col].clip(upper=df[rain_col].quantile(0.99)).hist(bins=40)
plt.title("Daily Rainfall Distribution (values capped at 99th percentile)")
plt.xlabel("Rainfall (mm/day)")
plt.ylabel("Number of days")
plt.tight_layout()
plt.savefig(output_dir / "rainfall_distribution.png", dpi=150)
plt.close()

# Export summaries
monthly.rename("average_daily_rainfall_mm").to_csv(
    output_dir / "monthly_rainfall_summary.csv"
)
annual.rename("annual_rainfall_mm").to_csv(
    output_dir / "annual_rainfall_summary.csv"
)

print("\nEDA complete. Reports saved in:", output_dir)
