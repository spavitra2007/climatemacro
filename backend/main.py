
import os
from pathlib import Path

import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from backend.rag import index_pdfs, ask_climate_question

# Project paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = PROJECT_ROOT / "data" / "processed" / "weather_daily.csv"
FORECAST_PATH = (
    PROJECT_ROOT
    / "outputs"
    / "models"
    / "january_2026_forecast.csv"
)

app = FastAPI(
    title="Climate Intelligence API",
    description="Weather analytics and rainfall forecast API",
    version="1.0.0",
)

frontend_origins = [
    origin.strip()
    for origin in os.getenv("FRONTEND_ORIGINS", "").split(",")
    if origin.strip()
]

# Keep local development working while allowing the deployed frontend origin.
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(dict.fromkeys([
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        *frontend_origins,
    ])),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def load_weather_data():
    if not DATA_PATH.exists():
        raise HTTPException(
            status_code=500,
            detail=f"Weather dataset not found: {DATA_PATH}",
        )

    df = pd.read_csv(DATA_PATH, parse_dates=["time"])
    return df.sort_values("time").reset_index(drop=True)


@app.get("/")
def home():
    return {
        "message": "Climate Intelligence API is running!",
        "docs": "/docs",
        "endpoints": [
            "/health",
            "/weather/summary",
            "/weather/monthly-rainfall",
            "/weather/recent",
            "/forecast/latest",
        ],
    }


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.get("/weather/summary")
def weather_summary():
    df = load_weather_data()
    rain_col = "precipitation_sum (mm)"

    return {
        "location": "Pune, Maharashtra",
        "records": int(len(df)),
        "start_date": str(df["time"].min().date()),
        "end_date": str(df["time"].max().date()),
        "missing_values": int(df.isna().sum().sum()),
        "total_rainfall_mm": round(float(df[rain_col].sum()), 2),
        "average_daily_rainfall_mm": round(float(df[rain_col].mean()), 3),
        "rainy_days": int((df[rain_col] > 0).sum()),
    }


@app.get("/weather/monthly-rainfall")
def monthly_rainfall():
    df = load_weather_data()
    rain_col = "precipitation_sum (mm)"

    result = (
        df.assign(month=df["time"].dt.month)
        .groupby("month")[rain_col]
        .mean()
        .round(2)
    )

    return [
        {"month": int(month), "average_rainfall_mm": float(value)}
        for month, value in result.items()
    ]


@app.get("/weather/recent")
def recent_weather(limit: int = 7):
    if limit < 1 or limit > 365:
        raise HTTPException(
            status_code=400,
            detail="limit must be between 1 and 365",
        )

    df = load_weather_data()
    records = df.tail(limit).copy()
    records["time"] = records["time"].dt.strftime("%Y-%m-%d")

    return records.to_dict(orient="records")


@app.get("/forecast/latest")
def latest_forecast():
    if not FORECAST_PATH.exists():
        raise HTTPException(
            status_code=404,
            detail="Forecast file not found. Run train_model.py first.",
        )

    df = pd.read_csv(FORECAST_PATH, parse_dates=["forecast_date"])

    if df.empty:
        raise HTTPException(
            status_code=404,
            detail="The forecast file is empty.",
        )

    row = df.iloc[-1]

    return {
        "forecast_date": str(row["forecast_date"].date()),
        "predicted_rainfall_mm": round(
            float(row["predicted_rainfall_mm"]), 4
        ),
        "unit": "mm",
        "note": (
            "This is a saved historical model forecast, "
            "not a live weather forecast."
        ),
    }
class ChatRequest(BaseModel):
    question: str


@app.post("/rag/index")
def index_climate_documents():
    return index_pdfs()


@app.post("/chat")
def chat_with_climate_assistant(request: ChatRequest):
    try:
        return ask_climate_question(request.question)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))