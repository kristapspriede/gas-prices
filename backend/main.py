from fastapi import FastAPI, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime, timezone, timedelta

from database import get_db, init_db
from models import PriceSnapshot
from scraper import scrape_all, STATIONS

app = FastAPI(title="Gas Prices API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/")
def health():
    return {"status": "ok"}


@app.post("/api/scrape")
def scrape(db: Session = Depends(get_db)):
    """Trigger a scrape and save results to the database."""
    results = scrape_all()
    now = datetime.now(timezone.utc)
    inserted = 0
    for station in results:
        for fuel, price in station["prices"].items():
            db.add(PriceSnapshot(
                scraped_at=now,
                station=station["name"],
                fuel_type=fuel,
                price=price,
                is_fallback=False,
            ))
            inserted += 1
    db.commit()
    return {"scraped_at": now.isoformat(), "rows_inserted": inserted}


@app.get("/api/prices")
def get_prices(db: Session = Depends(get_db)):
    """Return the latest scraped prices for all stations with change vs previous scrape."""

    # Get the two most recent distinct scrape timestamps
    timestamps = db.execute(
        text("SELECT DISTINCT scraped_at FROM price_snapshots ORDER BY scraped_at DESC LIMIT 2")
    ).fetchall()

    if not timestamps:
        return {"scraped_at": None, "stations": []}

    latest_ts = timestamps[0][0]
    prev_ts = timestamps[1][0] if len(timestamps) > 1 else None

    # Fetch latest rows
    latest_rows = db.query(PriceSnapshot).filter(
        PriceSnapshot.scraped_at == latest_ts
    ).all()

    # Fetch previous rows into a lookup dict
    prev_lookup = {}
    if prev_ts:
        for row in db.query(PriceSnapshot).filter(PriceSnapshot.scraped_at == prev_ts).all():
            prev_lookup[(row.station, row.fuel_type)] = float(row.price)

    # Group by station
    station_map = {s["name"]: {"name": s["name"], "color": s["color"], "prices": []} for s in STATIONS}

    fuel_priority = ["95", "98", "Diesel", "LPG"]

    for row in latest_rows:
        price = float(row.price)
        prev = prev_lookup.get((row.station, row.fuel_type))
        change = round(price - prev, 3) if prev is not None else None
        if row.station in station_map:
            station_map[row.station]["prices"].append({
                "fuel": row.fuel_type,
                "price": price,
                "change": change,
            })

    # Sort prices by fuel priority within each station
    for s in station_map.values():
        s["prices"].sort(key=lambda x: (
            fuel_priority.index(x["fuel"]) if x["fuel"] in fuel_priority else 99,
            x["fuel"]
        ))

    return {
        "scraped_at": latest_ts.isoformat() if hasattr(latest_ts, "isoformat") else str(latest_ts),
        "stations": list(station_map.values()),
    }


@app.get("/api/history")
def get_history(
    fuel: str = Query(..., description="Fuel type, e.g. '95', 'Diesel'"),
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
):
    """Return time-series price data for a given fuel type across all stations."""
    since = datetime.now(timezone.utc) - timedelta(days=days)

    rows = db.query(PriceSnapshot).filter(
        PriceSnapshot.fuel_type == fuel,
        PriceSnapshot.scraped_at >= since,
    ).order_by(PriceSnapshot.scraped_at).all()

    # Group by station
    series_map: dict[str, list] = {}
    for row in rows:
        series_map.setdefault(row.station, []).append({
            "t": row.scraped_at.isoformat() if hasattr(row.scraped_at, "isoformat") else str(row.scraped_at),
            "price": float(row.price),
        })

    # Preserve station order
    station_order = [s["name"] for s in STATIONS]
    series = [
        {"station": name, "data": series_map[name]}
        for name in station_order
        if name in series_map
    ]

    return {"fuel": fuel, "days": days, "series": series}
