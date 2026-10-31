
from pathlib import Path
import pandas as pd

file_path = Path(
    r"C:\Users\csubb\Downloads\Climate_Macroedtech\data\weather_dataset.xlsx"
)

if not file_path.exists():
    print("Dataset not found:", file_path)
else:
    df = pd.read_excel(file_path)

    print("\n===== WEATHER DATASET REPORT =====")
    print("File:", file_path.name)
    print("Dataset shape:", df.shape)

    print("\n===== COLUMN NAMES =====")
    print(df.columns.tolist())

    print("\n===== FIRST 5 ROWS =====")
    print(df.head())

    print("\n===== DATA TYPES =====")
    print(df.dtypes)

    print("\n===== MISSING VALUES =====")
    print(df.isnull().sum())

    print("\n===== DUPLICATE ROWS =====")
    print(df.duplicated().sum())
