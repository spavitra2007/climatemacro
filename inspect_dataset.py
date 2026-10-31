
import pandas as pd
from pathlib import Path

file_path = Path("data/weather_dataset.xlsx")

# Read the spreadsheet as raw data
raw = pd.read_excel(file_path, header=None)

print("DATASET SHAPE:", raw.shape)

print("\nFIRST 12 ROWS:")
print(raw.head(12).to_string(index=False, header=False))

print("\nLAST 5 ROWS:")
print(raw.tail(5).to_string(index=False, header=False))

print("\nFIRST ROW VALUES:")
print(raw.iloc[0].tolist())

print("\nSECOND ROW VALUES:")
print(raw.iloc[1].tolist())

print("\nROWS WITH MISSING VALUES IN LAST COLUMN:")
print(raw[raw.iloc[:, -1].isna()].head(5).to_string(index=False, header=False))
