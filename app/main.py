from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse
import os
import json
import uuid
import httpx
import asyncpg
from datetime import datetime, timezone

from fastapi import Header, HTTPException

COLLECTOR_TOKEN = os.getenv("COLLECTOR_TOKEN")

def require_collector_token(token: str | None):
    if not COLLECTOR_TOKEN:
        return  # allows local dev if unset
    if token != COLLECTOR_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")

from fastapi import FastAPI

from routers.counties import router as counties_router
from routers.trends import trend_router

app = FastAPI()

app.include_router(counties_router)
app.include_router(trend_router)


AIRNOW_API_KEY = os.getenv("AIRNOW_API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")

from app.florida_scoring import (
    FloridaInputs,
    heat_score_fl, rain_score_fl, wind_score_fl,
    compute_wps_fl, compute_iss_fl, compute_cai_fl,
    sts_from_delta_cai, vex_from_range, fpc_from_forecast,
    apply_florida_wind_nuance, compute_av, label_state
)


# -----------------------------
# Config
# -----------------------------
AIRNOW_BASE = "https://www.airnowapi.org/aq/observation/latLong/current"
NWS_BASE = "https://api.weather.gov"

STARTER_FL_COUNTIES = [
    "Alachua",
    "Baker",
    "Bay",
    "Bradford",
    "Brevard",
    "Broward",
    "Calhoun",
    "Charlotte",
    "Citrus",
    "Clay",
    "Collier",
    "Columbia",
    "DeSoto",
    "Dixie",
    "Duval",
    "Escambia",
    "Flagler",
    "Franklin",
    "Gadsden",
    "Gilchrist",
    "Glades",
    "Gulf",
    "Hamilton",
    "Hardee",
    "Hendry",
    "Hernando",
    "Highlands",
    "Hillsborough",
    "Holmes",
    "Indian River",
    "Jackson",
    "Jefferson",
    "Lafayette",
    "Lake",
    "Lee",
    "Leon",
    "Levy",
    "Liberty",
    "Madison",
    "Manatee",
    "Marion",
    "Martin",
    "Miami-Dade",
    "Monroe",
    "Nassau",
    "Okaloosa",
    "Okeechobee",
    "Orange",
    "Osceola",
    "Palm Beach",
    "Pasco",
    "Pinellas",
    "Polk",
    "Putnam",
    "St. Johns",
    "St. Lucie",
    "Santa Rosa",
    "Sarasota",
    "Seminole",
    "Sumter",
    "Suwannee",
    "Taylor",
    "Union",
    "Volusia",
    "Wakulla",
    "Walton",
    "Washington",
]

FL_COUNTY_META = {
    "St. Johns": {"fips": "12109", "centroid_lat": 29.8976, "centroid_lon": -81.381, "pop_density_per_sqmi": 375.4},
    "Miami-Dade": {"fips": "12086", "centroid_lat": 25.7617, "centroid_lon": -80.1918, "pop_density_per_sqmi": 1430.0},
    "Hillsborough": {"fips": "12057", "centroid_lat": 27.9904, "centroid_lon": -82.3018, "pop_density_per_sqmi": 1634.0},
    "Orange": {"fips": "12095", "centroid_lat": 28.5383, "centroid_lon": -81.3792, "pop_density_per_sqmi": 1556.0},
    "Alachua": {"fips": "12001", "centroid_lat": 29.6516, "centroid_lon": -82.3248, "pop_density_per_sqmi": 309.0},
    "Baker": {"fips": "12003", "centroid_lat": 30.3931, "centroid_lon": -82.3018, "pop_density_per_sqmi": 48.0},
    "Bay": {"fips": "12005", "centroid_lat": 30.1805, "centroid_lon": -85.6846, "pop_density_per_sqmi": 356.0},
    "Bradford": {"fips": "12007", "centroid_lat": 29.9494, "centroid_lon": -82.1714, "pop_density_per_sqmi": 82.0},
    "Brevard": {"fips": "12009", "centroid_lat": 28.2639, "centroid_lon": -80.7214, "pop_density_per_sqmi": 572.0},
    "Calhoun": {"fips": "12013", "centroid_lat": 30.3475, "centroid_lon": -85.1894, "pop_density_per_sqmi": 39.0},
    "Charlotte": {"fips": "12015", "centroid_lat": 26.8946, "centroid_lon": -81.9098, "pop_density_per_sqmi": 238.0},
    "Citrus": {"fips": "12017", "centroid_lat": 28.8483, "centroid_lon": -82.52, "pop_density_per_sqmi": 281.0},
    "Clay": {"fips": "12019", "centroid_lat": 29.9941, "centroid_lon": -81.7787, "pop_density_per_sqmi": 314.0},
    "Collier": {"fips": "12021", "centroid_lat": 26.0693, "centroid_lon": -81.4279, "pop_density_per_sqmi": 194.0},
    "Columbia": {"fips": "12023", "centroid_lat": 30.1897, "centroid_lon": -82.6393, "pop_density_per_sqmi": 88.0},
    "DeSoto": {"fips": "12027", "centroid_lat": 27.1895, "centroid_lon": -81.809, "pop_density_per_sqmi": 70.0},
    "Dixie": {"fips": "12029", "centroid_lat": 29.5806, "centroid_lon": -83.186, "pop_density_per_sqmi": 24.0},
    "Escambia": {"fips": "12033", "centroid_lat": 30.6389, "centroid_lon": -87.3415, "pop_density_per_sqmi": 666.0},
    "Flagler": {"fips": "12035", "centroid_lat": 29.4086, "centroid_lon": -81.2519, "pop_density_per_sqmi": 300.0},
    "Franklin": {"fips": "12037", "centroid_lat": 29.7354, "centroid_lon": -84.8008, "pop_density_per_sqmi": 14.0},
    "Gadsden": {"fips": "12039", "centroid_lat": 30.5793, "centroid_lon": -84.6133, "pop_density_per_sqmi": 90.0},
    "Gilchrist": {"fips": "12041", "centroid_lat": 29.7241, "centroid_lon": -82.8206, "pop_density_per_sqmi": 49.0},
    "Glades": {"fips": "12043", "centroid_lat": 26.9615, "centroid_lon": -81.1086, "pop_density_per_sqmi": 13.0},
    "Gulf": {"fips": "12045", "centroid_lat": 29.9496, "centroid_lon": -85.175, "pop_density_per_sqmi": 28.0},
    "Hamilton": {"fips": "12047", "centroid_lat": 30.5223, "centroid_lon": -82.95, "pop_density_per_sqmi": 21.0},
    "Hardee": {"fips": "12049", "centroid_lat": 27.4989, "centroid_lon": -81.81, "pop_density_per_sqmi": 74.0},
    "Hendry": {"fips": "12051", "centroid_lat": 26.5534, "centroid_lon": -81.4356, "pop_density_per_sqmi": 46.0},
    "Hernando": {"fips": "12053", "centroid_lat": 28.5636, "centroid_lon": -82.475, "pop_density_per_sqmi": 356.0},
    "Highlands": {"fips": "12055", "centroid_lat": 27.343, "centroid_lon": -81.341, "pop_density_per_sqmi": 100.0},
    "Holmes": {"fips": "12059", "centroid_lat": 30.867, "centroid_lon": -85.815, "pop_density_per_sqmi": 44.0},
    "Indian River": {"fips": "12061", "centroid_lat": 27.6936, "centroid_lon": -80.384, "pop_density_per_sqmi": 305.0},
    "Jackson": {"fips": "12063", "centroid_lat": 30.774, "centroid_lon": -85.2269, "pop_density_per_sqmi": 51.0},
    "Jefferson": {"fips": "12065", "centroid_lat": 30.548, "centroid_lon": -83.912, "pop_density_per_sqmi": 30.0},
    "Lafayette": {"fips": "12067", "centroid_lat": 29.99, "centroid_lon": -83.18, "pop_density_per_sqmi": 21.0},
    "Lake": {"fips": "12069", "centroid_lat": 28.7615, "centroid_lon": -81.7129, "pop_density_per_sqmi": 360.0},
    "Lee": {"fips": "12071", "centroid_lat": 26.663, "centroid_lon": -81.84, "pop_density_per_sqmi": 1000.0},
    "Leon": {"fips": "12073", "centroid_lat": 30.4383, "centroid_lon": -84.2807, "pop_density_per_sqmi": 400.0},
    "Levy": {"fips": "12075", "centroid_lat": 29.3177, "centroid_lon": -82.8126, "pop_density_per_sqmi": 36.0},
    "Liberty": {"fips": "12077", "centroid_lat": 30.2376, "centroid_lon": -84.882, "pop_density_per_sqmi": 9.0},
    "Madison": {"fips": "12079", "centroid_lat": 30.4693, "centroid_lon": -83.412, "pop_density_per_sqmi": 31.0},
    "Manatee": {"fips": "12081", "centroid_lat": 27.4989, "centroid_lon": -82.5748, "pop_density_per_sqmi": 1100.0},
    "Marion": {"fips": "12083", "centroid_lat": 29.2108, "centroid_lon": -82.056, "pop_density_per_sqmi": 300.0},
    "Martin": {"fips": "12085", "centroid_lat": 27.0805, "centroid_lon": -80.41, "pop_density_per_sqmi": 350.0},
    "Monroe": {"fips": "12087", "centroid_lat": 24.5551, "centroid_lon": -81.78, "pop_density_per_sqmi": 80.0},
    "Nassau": {"fips": "12089", "centroid_lat": 30.61, "centroid_lon": -81.822, "pop_density_per_sqmi": 160.0},
    "Okaloosa": {"fips": "12091", "centroid_lat": 30.5772, "centroid_lon": -86.66, "pop_density_per_sqmi": 220.0},
    "Okeechobee": {"fips": "12093", "centroid_lat": 27.2439, "centroid_lon": -80.8298, "pop_density_per_sqmi": 73.0},
    "Osceola": {"fips": "12097", "centroid_lat": 28.2919, "centroid_lon": -81.4076, "pop_density_per_sqmi": 350.0},
    "Pasco": {"fips": "12101", "centroid_lat": 28.3232, "centroid_lon": -82.4319, "pop_density_per_sqmi": 800.0},
    "Pinellas": {"fips": "12103", "centroid_lat": 27.8764, "centroid_lon": -82.7779, "pop_density_per_sqmi": 3500.0},
    "Polk": {"fips": "12105", "centroid_lat": 27.9963, "centroid_lon": -81.6924, "pop_density_per_sqmi": 370.0},
    "Putnam": {"fips": "12107", "centroid_lat": 29.626, "centroid_lon": -81.65, "pop_density_per_sqmi": 100.0},
    "St. Lucie": {"fips": "12111", "centroid_lat": 27.273, "centroid_lon": -80.3582, "pop_density_per_sqmi": 500.0},
    "Santa Rosa": {"fips": "12113", "centroid_lat": 30.7038, "centroid_lon": -87.009, "pop_density_per_sqmi": 180.0},
    "Sarasota": {"fips": "12115", "centroid_lat": 27.3364, "centroid_lon": -82.5307, "pop_density_per_sqmi": 1000.0},
    "Seminole": {"fips": "12117", "centroid_lat": 28.7097, "centroid_lon": -81.2081, "pop_density_per_sqmi": 1400.0},
    "Sumter": {"fips": "12119", "centroid_lat": 28.7167, "centroid_lon": -82.0833, "pop_density_per_sqmi": 250.0},
    "Suwannee": {"fips": "12121", "centroid_lat": 30.396, "centroid_lon": -82.95, "pop_density_per_sqmi": 46.0},
    "Taylor": {"fips": "12123", "centroid_lat": 30.101, "centroid_lon": -83.58, "pop_density_per_sqmi": 40.0},
    "Union": {"fips": "12125", "centroid_lat": 30.0691, "centroid_lon": -82.333, "pop_density_per_sqmi": 60.0},
    "Volusia": {"fips": "12127", "centroid_lat": 29.028, "centroid_lon": -81.075, "pop_density_per_sqmi": 500.0},
    "Wakulla": {"fips": "12129", "centroid_lat": 30.19, "centroid_lon": -84.375, "pop_density_per_sqmi": 70.0},
    "Walton": {"fips": "12131", "centroid_lat": 30.6, "centroid_lon": -86.1, "pop_density_per_sqmi": 100.0},
    "Washington": {"fips": "12133", "centroid_lat": 30.6, "centroid_lon": -85.6, "pop_density_per_sqmi": 45.0},
    "Duval": {"fips": "12031", "centroid_lat": 30.3322, "centroid_lon": -81.6557, "pop_density_per_sqmi": 1298.0},
    "Broward": {"fips": "12011", "centroid_lat": 26.1224, "centroid_lon": -80.1373, "pop_density_per_sqmi": 1600.0},
    "Palm Beach": {"fips": "12099", "centroid_lat": 26.7153, "centroid_lon": -80.0534, "pop_density_per_sqmi": 774.0},
}

_db_pool: asyncpg.Pool | None = None


# -----------------------------
# DB setup + snapshot recording
# -----------------------------
async def get_db_pool() -> asyncpg.Pool:
    global _db_pool
    if _db_pool is None:
        if not DATABASE_URL:
            raise RuntimeError("DATABASE_URL is not set")
        _db_pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=5)
    return _db_pool


async def ensure_tables() -> None:
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            create table if not exists insurer_snapshots (
              id bigserial primary key,
              run_id uuid not null,
              snapshot_at timestamptz not null default now(),
              state text not null,
              county text not null,
              scores jsonb not null,
              state_label text null,
              model_version text null
            );

            create index if not exists insurer_snapshots_state_county_time
              on insurer_snapshots (state, county, snapshot_at desc);

            create index if not exists insurer_snapshots_scores_gin
              on insurer_snapshots using gin (scores);
            """
        )


async def record_snapshot(
    *,
    run_id: uuid.UUID,
    snapshot_at: datetime,
    state: str,
    county: str,
    scores: dict,
    state_label: str | None = None,
    model_version: str | None = "v1",
) -> None:
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            insert into insurer_snapshots
              (run_id, snapshot_at, state, county, scores, state_label, model_version)
            values
              ($1, $2, $3, $4, $5::jsonb, $6, $7)
            """,
            run_id,
            snapshot_at,
            state,
            county,
            json.dumps(scores),
            state_label,
            model_version,
        )

async def record_county_snapshot(
    *,
    county_fips: str,
    snapshot_ts: datetime,
    risk_score: float | None,
    grid_stress_score: float | None,
    weather_stress_score: float | None,
    payload: dict | None = None,
) -> None:
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            insert into county_snapshots
              (county_fips, snapshot_ts, risk_score, grid_stress_score, weather_stress_score, payload)
            values
              ($1, $2, $3, $4, $5, $6::jsonb)
            """,
            county_fips,
            snapshot_ts,
            risk_score,
            grid_stress_score,
            weather_stress_score,
            json.dumps(payload or {}),
        )


@app.on_event("startup")
async def _startup():
    # Only attempt DB init if DATABASE_URL exists
    if DATABASE_URL:
        await ensure_tables()


# -----------------------------
# External data helpers
# -----------------------------
async def upsert_county_input(
    *,
    fips: str,
    state: str,
    county_name: str,
    centroid_lat: float,
    centroid_lon: float,
    pop_density_per_sqmi: float | None = None,
) -> None:
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            insert into counties
              (fips, state, county_name, centroid_lat, centroid_lon, pop_density_per_sqmi)
            values
              ($1, $2, $3, $4, $5, $6)
            on conflict (fips) do update set
              state = excluded.state,
              county_name = excluded.county_name,
              centroid_lat = excluded.centroid_lat,
              centroid_lon = excluded.centroid_lon,
              pop_density_per_sqmi = excluded.pop_density_per_sqmi,
              updated_at = now()
            """,
            fips,
            state,
            county_name,
            centroid_lat,
            centroid_lon,
            pop_density_per_sqmi,
        )


async def get_airnow_aqi(lat: float, lon: float):
    if not AIRNOW_API_KEY:
        return None

    params = {
        "format": "application/json",
        "latitude": lat,
        "longitude": lon,
        "distance": 100,
        "API_KEY": AIRNOW_API_KEY,
    }

    async with httpx.AsyncClient(timeout=15.0) as client:
        r = await client.get(AIRNOW_BASE, params=params)
        r.raise_for_status()
        data = r.json()

    if not data:
        return None

    for obs in data:
        if obs.get("ParameterName") == "PM2.5":
            return obs.get("AQI")

    return data[0].get("AQI")

async def get_weather(lat: float, lon: float):
    headers = {"User-Agent": "Daymark (hello.daymark@gmail.com)"}

    default_weather = {
        "temp_f": 75,
        "wind_mph": 10,
        "rain_chance_pct": 0,
        "rain_24h_in": 0.0,
    }

    async with httpx.AsyncClient(timeout=20.0) as client:
        r = await client.get(f"{NWS_BASE}/points/{lat},{lon}", headers=headers)
        r.raise_for_status()
        props = r.json()["properties"]

        forecast_urls = [
            props.get("forecastHourly"),
            props.get("forecast"),
        ]

        for forecast_url in forecast_urls:
            if not forecast_url:
                continue

            try:
                r2 = await client.get(forecast_url, headers=headers)
                r2.raise_for_status()
                forecast = r2.json()

                periods = forecast.get("properties", {}).get("periods", [])
                if not periods:
                    continue

                first_period = periods[0]
                temp_f = first_period.get("temperature", 75)

                wind_raw = first_period.get("windSpeed", "10 mph")
                wind_mph = 10
                if isinstance(wind_raw, str):
                    first_part = wind_raw.split()[0]
                    if "-" in first_part:
                        first_part = first_part.split("-")[0]
                    try:
                        wind_mph = int(first_part)
                    except ValueError:
                        wind_mph = 10

                # Look ahead across the next forecast periods
                # forecastHourly: about next 12 hours
                # forecast: about next several half-days
                lookahead_periods = periods[:12] if "forecastHourly" in forecast_url else periods[:4]

                rain_values = []
                for p in lookahead_periods:
                    precip = p.get("probabilityOfPrecipitation")
                    if isinstance(precip, dict):
                        value = precip.get("value")
                        if value is not None:
                            try:
                                rain_values.append(int(value))
                            except (ValueError, TypeError):
                                pass

                rain_chance_pct = max(rain_values) if rain_values else 0

                if rain_chance_pct >= 80:
                    rain_24h_in = 1.0
                elif rain_chance_pct >= 60:
                    rain_24h_in = 0.5
                elif rain_chance_pct >= 40:
                    rain_24h_in = 0.2
                elif rain_chance_pct >= 20:
                    rain_24h_in = 0.05
                else:
                    rain_24h_in = 0.0

                return {
                    "temp_f": temp_f,
                    "wind_mph": wind_mph,
                    "rain_chance_pct": rain_chance_pct,
                    "rain_24h_in": rain_24h_in,
                }

            except httpx.HTTPStatusError:
                continue
            except Exception:
                continue

    return default_weather

async def get_nws_alert_count(lat: float, lon: float) -> int:
    url = f"{NWS_BASE}/alerts/active"
    params = {"point": f"{lat},{lon}"}
    headers = {"User-Agent": "Daymark (hello.daymark@gmail.com)"}

    async with httpx.AsyncClient(timeout=15.0) as client:
        r = await client.get(url, params=params, headers=headers)
        r.raise_for_status()
        data = r.json()

    return len(data.get("features", []))


# -----------------------------
# Core insurer compute function
# -----------------------------
async def compute_insurer_fl_county(
    county: str,
    county_meta: dict,
    weather: dict,
    alert_count: int = 0,
) -> dict:
    county_fips = county_meta["fips"]

    temp_f = weather.get("temp_f", 75)
    wind_mph = weather.get("wind_mph", 10)
    rain_24h_in = weather.get("rain_24h_in", 0.0)
    rain_chance_pct = weather.get("rain_chance_pct", 0)
    pop_density = county_meta["pop_density_per_sqmi"]

    inputs_today = FloridaInputs(
        month=datetime.utcnow().month,
        heat_index_f=temp_f,
        rain_24h_in=rain_24h_in,
        wind_sust_mph=wind_mph,
        tropical_flag=False,
        pop_density=pop_density,
    )

    heat = heat_score_fl(inputs_today.month, inputs_today.heat_index_f)
    rain = rain_score_fl(inputs_today.rain_24h_in, inputs_today.tropical_flag)
    wind = wind_score_fl(inputs_today.wind_sust_mph, inputs_today.tropical_flag)

    temp_boost = max(0, (temp_f - 70) * 0.5)
    wind_boost = wind_mph * 1.5
    rain_boost = min(20, rain_chance_pct * 0.2)
    alert_boost = min(25, alert_count * 8)

    wps_raw = compute_wps_fl(heat, rain, wind)
    wps = min(
        100,
        round(
            (wps_raw * 0.3)
            + (temp_boost * 0.2)
            + (wind_boost * 0.2)
            + (rain_boost * 0.15)
            + (alert_boost * 0.15),
            1,
        ),
    )

    persistence = 40
    iss = round(compute_iss_fl(heat, inputs_today.pop_density, persistence), 1)

    das = 10
    cai_raw = compute_cai_fl(wps, iss, das)
    cai = round(min(100, cai_raw * 3.0), 1)

    cai_history_5d = [45, 47, 50, 54, cai]
    delta_3d = cai - cai_history_5d[-4]
    sts = sts_from_delta_cai(delta_3d)

    range_5d = max(cai_history_5d) - min(cai_history_5d)
    vex = vex_from_range(range_5d)

    forecast_wps_3d_avg = wps
    wind_score_max_3d = wind
    fpc = fpc_from_forecast(
        forecast_wps_3d_avg,
        wind_score_max_3d,
        inputs_today.tropical_flag,
    )

    wind_48h_ago_score = 30
    sts = apply_florida_wind_nuance(
        sts,
        wind,
        wind_48h_ago_score,
        forecast_wps_3d_avg,
        inputs_today.tropical_flag,
    )

    av = compute_av(sts, vex, fpc)
    state_label = label_state(cai, av)

    scores = {
        "HeatScore": round(heat, 1),
        "RainScore": round(rain, 1),
        "WindScore": round(wind, 1),
        "AlertCount": alert_count,
        "WPS": round(wps, 1),
        "ISS": round(iss, 1),
        "DAS": das,
        "CAI": round(cai, 1),
        "STS": round(sts, 1) if isinstance(sts, (int, float)) else sts,
        "VEX": round(vex, 1) if isinstance(vex, (int, float)) else vex,
        "FPC": round(fpc, 1) if isinstance(fpc, (int, float)) else fpc,
        "AV": round(av, 1) if isinstance(av, (int, float)) else av,
        "temp_f": temp_f,
        "wind_mph": wind_mph,
        "rain_chance_pct": rain_chance_pct,
        "rain_24h_in": rain_24h_in,
        "pop_density_per_sqmi": pop_density,
    }

    return {
        "county": county,
        "county_fips": county_fips,
        "scores": scores,
        "state": state_label,
    }
# -----------------------------
# Routes
# -----------------------------
@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/debug/routes")
def debug_routes():
    return sorted([getattr(r, "path", "") for r in app.routes])

@app.get("/api/daymark")
async def daymark(lat: float = Query(...), lon: float = Query(...)):
    score = 0
    drivers: list[str] = []
    add_items: list[str] = []

    # Weather alerts (NWS)
    alert_count = await get_nws_alert_count(lat, lon)
    if alert_count == 0:
        drivers.append("No active weather alerts")
    elif alert_count == 1:
        score += 20
        drivers.append("1 active weather alert")
        add_items += ["rain shell", "phone waterproof pouch", "small flashlight"]
    else:
        score += 35
        drivers.append(f"{alert_count} active weather alerts")
        add_items += ["rain shell", "phone waterproof pouch", "small flashlight", "power bank"]

    # Air quality (AirNow)
    aqi = await get_airnow_aqi(lat, lon)
    fetched_at = datetime.now(timezone.utc).isoformat()

    if aqi is None:
        drivers.append("Air quality data unavailable")
    elif aqi <= 50:
        drivers.append(f"Air quality: Good (AQI {aqi})")
    elif aqi <= 100:
        drivers.append(f"Air quality: Moderate (AQI {aqi})")
    else:
        drivers.append(f"Air quality: Unhealthy (AQI {aqi})")
        add_items.append("N95 mask (air quality)")

    # Overall status from score
    if score <= 24:
        status = "GREEN"
    elif score <= 44:
        status = "YELLOW"
    elif score <= 64:
        status = "ORANGE"
    else:
        status = "RED"

    # de-dupe add_items while preserving order
    seen = set()
    add_items = [x for x in add_items if not (x in seen or seen.add(x))]

    return {
        "status": status,
        "score": score,
        "drivers": drivers,
        "add_items": add_items,
        "air_quality": {"aqi": aqi, "fetchedAt": fetched_at},
    }


# Single-county compute (no DB write)
@app.get("/api/insurer/florida")
async def insurer_florida(county: str = "Duval"):
    return await compute_insurer_fl_county(county)

# Collector route (writes snapshots): Duval + 5 counties
@app.post("/api/insurer/collect/florida")
async def collect_insurer_florida(
    x_collector_token: str | None = Header(default=None)
):
    require_collector_token(x_collector_token)

    run_id = uuid.uuid4()
    snapshot_at = datetime.now(timezone.utc)

    results = []

    for county in STARTER_FL_COUNTIES:
        county_meta = FL_COUNTY_META.get(county)
        if not county_meta:
            continue
            
        weather = await get_weather(
            county_meta["centroid_lat"],
            county_meta["centroid_lon"],
        )

        alert_count = await get_nws_alert_count(
            county_meta["centroid_lat"],
            county_meta["centroid_lon"],
        )

        payload = await compute_insurer_fl_county(
            county=county,
            county_meta=county_meta,
            weather=weather,
            alert_count=alert_count,
        )

        results.append(payload)

        if DATABASE_URL:
            await record_snapshot(
                run_id=run_id,
                snapshot_at=snapshot_at,
                state="Florida",
                county=county,
                scores=payload["scores"],
                state_label=payload.get("state"),
                model_version="v1",
            )

            county_fips = payload.get("county_fips")

            if county_fips:
                await upsert_county_input(
                    fips=county_fips,
                    state="FL",
                    county_name=county,
                    centroid_lat=county_meta["centroid_lat"],
                    centroid_lon=county_meta["centroid_lon"],
                    pop_density_per_sqmi=county_meta.get("pop_density_per_sqmi"),
                )
                await record_county_snapshot(
                    county_fips=county_fips,
                    snapshot_ts=snapshot_at,
                    risk_score=payload["scores"].get("CAI"),
                    grid_stress_score=payload["scores"].get("ISS"),
                    weather_stress_score=payload["scores"].get("WPS"),
                    payload={
                        "county": county,
                        "state": "Florida",
                        "state_label": payload.get("state"),
                        "model_version": "v1",
                        "scores": payload["scores"],
                        "weather": weather,
                        "alerts": {
                            "count": alert_count
                        },
                    },
                )

    return {
        "ok": True,
        "run_id": str(run_id),
        "snapshot_at": snapshot_at.isoformat(),
        "state": "Florida",
        "counties": results,
        "recorded": bool(DATABASE_URL),
    }
@app.get("/api/insurer/snapshots/latest")
async def latest_snapshots(state: str = "Florida", limit: int = 25):
    if not DATABASE_URL:
        return {"ok": False, "error": "DATABASE_URL not set"}

    pool = await get_db_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            select id, run_id, snapshot_at, state, county, state_label, scores
            from insurer_snapshots
            where state = $1
            order by snapshot_at desc
            limit $2
            """,
            state,
            limit,
        )

    return {
        "ok": True,
        "count": len(rows),
        "rows": [dict(r) for r in rows],
    }
    return {
        "ok": True,
        "run_id": str(run_id),
        "snapshot_at": snapshot_at.isoformat(),
        "state": "Florida",
        "counties": results,
        "recorded": bool(DATABASE_URL),
    }
@app.get("/api/insurer/snapshots/latest")
async def latest_snapshots(state: str = "Florida", limit: int = 25):
    if not DATABASE_URL:
        return {"ok": False, "error": "DATABASE_URL not set"}

    pool = await get_db_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            select id, run_id, snapshot_at, state, county, state_label, scores
            from insurer_snapshots
            where state = $1
            order by snapshot_at desc
            limit $2
            """,
            state,
            limit,
        )

    return {
        "ok": True,
        "count": len(rows),
        "rows": [dict(r) for r in rows],
    }
    return {
        "ok": True,
        "run_id": str(run_id),
        "snapshot_at": snapshot_at.isoformat(),
        "state": "Florida",
        "counties": results,
        "recorded": bool(DATABASE_URL),
    }
@app.get("/api/insurer/snapshots/latest")
async def latest_snapshots(state: str = "Florida", limit: int = 25):
    if not DATABASE_URL:
        return {"ok": False, "error": "DATABASE_URL not set"}

    pool = await get_db_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            select id, run_id, snapshot_at, state, county, state_label, scores
            from insurer_snapshots
            where state = $1
            order by snapshot_at desc
            limit $2
            """,
            state,
            limit,
        )

    return {
        "ok": True,
        "count": len(rows),
        "rows": [dict(r) for r in rows],
    }
@app.get("/api/founder/florida/latest")
async def founder_florida_latest(limit: int = 20):
    if not DATABASE_URL:
        return {"rows": []}

    conn = await asyncpg.connect(DATABASE_URL)

rows = await conn.fetch(
    """
    SELECT
        c.county_name,
        s.county_fips,
        s.snapshot_ts,
        s.risk_score,
        s.grid_stress_score,
        s.weather_stress_score,
        s.payload
    FROM county_snapshots s
    JOIN counties c
      ON c.fips = s.county_fips
    JOIN (
        SELECT county_fips, MAX(snapshot_ts) AS max_snapshot_ts
        FROM county_snapshots
        GROUP BY county_fips
    ) latest
      ON s.county_fips = latest.county_fips
     AND s.snapshot_ts = latest.max_snapshot_ts
    ORDER BY s.risk_score DESC NULLS LAST
    LIMIT $1
    """,
    limit,
)

    await conn.close()

    result = []
    for r in rows:
        row = dict(r)

        payload = row.get("payload") or {}
        if isinstance(payload, str):
            try:
                payload = 
@app.get("/founder/florida", response_class=HTMLResponse)
def founder_florida_dashboard():
    return """
    <html>
      <head>
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <title>Daymark Founder Dashboard</title>
        <style>
          body {
            font-family: system-ui, sans-serif;
            background: #f7f7f8;
            margin: 0;
            padding: 24px;
            color: #111;
          }
          .wrap {
            max-width: 1100px;
            margin: 0 auto;
          }
          .card {
            background: white;
            border-radius: 16px;
            padding: 20px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.06);
            margin-bottom: 20px;
          }
          h1 {
            margin: 0 0 8px 0;
          }
          .sub {
            color: #666;
            margin-bottom: 16px;
          }
          table {
            width: 100%;
            border-collapse: collapse;
            font-size: 14px;
          }
          th, td {
            text-align: left;
            padding: 10px 8px;
            border-bottom: 1px solid #eee;
          }
          th {
            color: #555;
            font-weight: 600;
          }
          .risk-pill {
            display: inline-block;
            min-width: 58px;
            text-align: center;
            padding: 6px 10px;
            border-radius: 999px;
            font-weight: 700;
          }
          .green { background: #e7f6ec; color: #1f7a3d; }
          .yellow { background: #fff6db; color: #8a6a00; }
          .orange { background: #ffe8d9; color: #a24b00; }
          .red { background: #fde6e6; color: #b42318; }
          .muted {
            color: #666;
          }
        </style>
      </head>
      <body>
        <div class="wrap">
          <div class="card">
            <h1>Daymark Founder Dashboard</h1>
            <div class="sub">Florida latest county risk snapshot</div>
            <div id="meta" class="muted">Loading...</div>
          </div>

          <div class="card">
            <table>
              <thead>
                <tr>
                  <th>#</th>
                  <th>County</th>
                  <th>Risk</th>
                  <th>Temp °F</th>
                  <th>Wind mph</th>
                  <th>Rain %</th>
                  <th>Rain (in)</th>
                  <th>Alerts</th>
                  <th>Grid Stress</th>
                  <th>Weather Stress</th>
                </tr>
              </thead>
              <tbody id="rows"></tbody>
            </table>
          </div>
        </div>

        <script>
          function riskClass(score) {
            if (score == null) return "green";
            if (score < 40) return "green";
            if (score < 55) return "yellow";
            if (score < 70) return "orange";
            return "red";
          }

          fetch("/api/founder/florida/latest?limit=20")
            .then(r => r.json())
            .then(data => {
              const meta = document.getElementById("meta");
              const tbody = document.getElementById("rows");

              if (!data.ok) {
                meta.textContent = "Failed to load data";
                return;
              }

              meta.textContent = "Showing top " + data.count + " counties by latest risk score";

              tbody.innerHTML = data.rows.map((row, i) => `
                <tr>
                  <td>${i + 1}</td>
                  <td>${row.county_name}</td>
                  <td><span class="risk-pill ${riskClass(row.risk_score)}">${row.risk_score ?? "-"}</span></td>
                  <td>${row.temp_f ?? "-"}</td>
                  <td>${row.wind_mph ?? "-"}</td>
                  <td>${row.rain_chance_pct ?? "-"}</td>
                  <td>${row.rain_24h_in ?? "-"}</td>
                  <td>${row.alert_count ?? 0}</td>
                  <td>${row.grid_stress_score ?? "-"}</td>
                  <td>${row.weather_stress_score ?? "-"}</td>
                </tr>
              `).join("");
            })
            .catch(() => {
              document.getElementById("meta").textContent = "Error loading dashboard";
            });
        </script>
      </body>
    </html>
    """

@app.get("/", response_class=HTMLResponse)
def home():
    return """
    <html>
      <head>
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <title>Daymark</title>
        <style>
          body { background: #fafafa; max-width: 420px; margin: 0 auto; padding: 24px; }
          .card { background: white; border-radius: 14px; padding: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.06); }
          h1 { margin-bottom: 6px; }
          .status { font-size: 20px; font-weight: 600; margin-top: 12px; }
          .aqi { margin-top: 6px; font-size: 15px; }
          .drivers { margin-top: 14px; color: #666; font-size: 14px; line-height: 1.4; }
        </style>
      </head>
      <body style="font-family: system-ui; padding: 24px;">
        <div class="card">
          <h1>Daymark</h1>
          <p class="sub">A calm reference point for today.</p>
          <p id="status">Loading status…</p>
          <p id="aqi" style="margin-top:6px;"></p>
          <p id="drivers" style="color:#555; margin-top:8px;"></p>
        </div>

        <script>
          fetch("/api/daymark?lat=30.0922&lon=-81.5723")
            .then(r => r.json())
            .then(data => {
              const dot =
                data.status === "GREEN" ? "🟢" :
                data.status === "YELLOW" ? "🟡" :
                data.status === "ORANGE" ? "🟠" : "🔴";

              document.getElementById("status").innerHTML =
                "<b>Status:</b> " + dot + " " + data.status;

              const aqiLine = data.drivers.find(d => d.startsWith("Air quality"));
              if (aqiLine) document.getElementById("aqi").innerText = aqiLine;

              document.getElementById("drivers").innerText =
                data.drivers.filter(d => !d.startsWith("Air quality")).join(" • ");
            })
            .catch(() => {
              document.getElementById("status").innerText = "Status unavailable";
            });
        </script>
      </body>
    </html>
    """
