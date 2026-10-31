
from pathlib import Path
import pandas as pd

file_path = Path("data/weather_dataset.xlsx")
output_dir = Path("data/processed")
output_dir.mkdir(parents=True, exist_ok=True)

# Read every Excel cell without assuming a header
raw = pd.read_excel(file_path, header=None)

# Locate rows that contain the time column
header_rows = raw.index[
    raw.iloc[:, 0].astype(str).str.strip().str.lower().eq("time")
].tolist()

print("Detected header rows:", header_rows)

if len(header_rows) != 2:
    raise ValueError(
        "Expected separate hourly and daily header rows. "
        "Check the detected headers before cleaning."
    )

cleaned_sections = []

for index, header_row in enumerate(header_rows):
    headers = raw.iloc[header_row].tolist()

    # Extract data until the next section header
    start = header_row + 1
    end = header_rows[index + 1] if index + 1 < len(header_rows) else len(raw)

    section = raw.iloc[start:end].copy()
    section.columns = headers

    # Remove entirely empty columns and rows
    section = section.dropna(axis=1, how="all")
    section = section.dropna(how="all")

    # Parse timestamps and discard non-observation rows
    section["time"] = pd.to_datetime(section["time"], errors="coerce")
    section = section.dropna(subset=["time"])

    # Remove duplicate timestamps within this section
    section = section.drop_duplicates(subset=["time"])
    section = section.sort_values("time").reset_index(drop=True)

    label = "hourly" if index == 0 else "daily"
    output_path = output_dir / f"weather_{label}.csv"
    section.to_csv(output_path, index=False)

    cleaned_sections.append(section)

    print(f"\n{label.upper()} DATA")
    print("Shape:", section.shape)
    print("Date range:", section["time"].min(), "to", section["time"].max())
    print("Columns:", section.columns.tolist())
    print("Missing values:\n", section.isna().sum())
    print("Saved:", output_path)

print("\nCleaning inspection complete.")
print("The hourly and daily datasets remain separate.")
