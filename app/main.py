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

"county_name","fips","centroid_lat","centroid_lon","pop_density_per_sqmi"
St. Johns,"12109",29.8976,-81.381,375.4
Miami-Dade,"12086",25.7617,-80.1918,1430.0
Hillsborough,"12057",27.9904,-82.3018,1634.0
Orange,"12095",28.5383,-81.3792,1556.0
Alachua,"12001",29.6516,-82.3248,309.0
Baker,"12003",30.3931,-82.3018,48.0
Bay,"12005",30.1805,-85.6846,356.0
Bradford,"12007",29.9494,-82.1714,82.0
Brevard,"12009",28.2639,-80.7214,572.0
Calhoun,"12013",30.3475,-85.1894,39.0
Charlotte,"12015",26.8946,-81.9098,238.0
Citrus,"12017",28.8483,-82.52,281.0
Clay,"12019",29.9941,-81.7787,314.0
Collier,"12021",26.0693,-81.4279,194.0
Columbia,"12023",30.1897,-82.6393,88.0
DeSoto,"12027",27.1895,-81.809,70.0
Dixie,"12029",29.5806,-83.186,24.0
Escambia,"12033",30.6389,-87.3415,666.0
Flagler,"12035",29.4086,-81.2519,300.0
Franklin,"12037",29.7354,-84.8008,14.0
Gadsden,"12039",30.5793,-84.6133,90.0
Gilchrist,"12041",29.7241,-82.8206,49.0
Glades,"12043",26.9615,-81.1086,13.0
Gulf,"12045",29.9496,-85.175,28.0
Hamilton,"12047",30.5223,-82.95,21.0
Hardee,"12049",27.4989,-81.81,74.0
Hendry,"12051",26.5534,-81.4356,46.0
Hernando,"12053",28.5636,-82.475,356.0
Highlands,"12055",27.343,-81.341,100.0
Holmes,"12059",30.867,-85.815,44.0
Indian River,"12061",27.6936,-80.384,305.0
Jackson,"12063",30.774,-85.2269,51.0
Jefferson,"12065",30.548,-83.912,30.0
Lafayette,"12067",29.99,-83.18,21.0
Lake,"12069",28.7615,-81.7129,360.0
Lee,"12071",26.663,-81.84,1000.0
Leon,"12073",30.4383,-84.2807,400.0
Levy,"12075",29.3177,-82.8126,36.0
Liberty,"12077",30.2376,-84.882,9.0
Madison,"12079",30.4693,-83.412,31.0
Manatee,"12081",27.4989,-82.5748,1100.0
Marion,"12083",29.2108,-82.056,300.0
Martin,"12085",27.0805,-80.41,350.0
Monroe,"12087",24.5551,-81.78,80.0
Nassau,"12089",30.61,-81.822,160.0
Okaloosa,"12091",30.5772,-86.66,220.0
Okeechobee,"12093",27.2439,-80.8298,73.0
Osceola,"12097",28.2919,-81.4076,350.0
Pasco,"12101",28.3232,-82.4319,800.0
Pinellas,"12103",27.8764,-82.7779,3500.0
Polk,"12105",27.9963,-81.6924,370.0
Putnam,"12107",29.626,-81.65,100.0
St. Lucie,"12111",27.273,-80.3582,500.0
Santa Rosa,"12113",30.7038,-87.009,180.0
Sarasota,"12115",27.3364,-82.5307,1000.0
Seminole,"12117",28.7097,-81.2081,1400.0
Sumter,"12119",28.7167,-82.0833,250.0
Suwannee,"12121",30.396,-82.95,46.0
Taylor,"12123",30.101,-83.58,40.0
Union,"12125",30.0691,-82.333,60.0
Volusia,"12127",29.028,-81.075,500.0
Wakulla,"12129",30.19,-84.375,70.0
Walton,"12131",30.6,-86.1,100.0
Washington,"12133",30.6,-85.6,45.0
Duval,"12031",30.3322,-81.6557,1298.0
Broward,"12011",26.1224,-80.1373,1600.0
Palm Beach,"12099",26.7153,-80.0534,774.0


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
async def compute_insurer_fl_county(county: str) -> dict:

    county_meta = FL_COUNTY_META.get(county)
    county_fips = county_meta["fips"] if county_meta else None
    
    inputs_today = FloridaInputs(
        month=datetime.utcnow().month,
        heat_index_f=92,
        rain_24h_in=0.2,
        wind_sust_mph=18,
        tropical_flag=False,
        pop_density=1200
    )

    heat = heat_score_fl(inputs_today.month, inputs_today.heat_index_f)
    rain = rain_score_fl(inputs_today.rain_24h_in, inputs_today.tropical_flag)
    wind = wind_score_fl(inputs_today.wind_sust_mph, inputs_today.tropical_flag)

    wps = compute_wps_fl(heat, rain, wind)

    persistence = 40
    iss = compute_iss_fl(heat, inputs_today.pop_density, persistence)

    das = 10
    cai = compute_cai_fl(wps, iss, das)

    cai_history_5d = [45, 47, 50, 54, cai]
    delta_3d = cai - cai_history_5d[-4]
    sts = sts_from_delta_cai(delta_3d)

    range_5d = max(cai_history_5d) - min(cai_history_5d)
    vex = vex_from_range(range_5d)

    forecast_wps_3d_avg = wps
    wind_score_max_3d = wind
    fpc = fpc_from_forecast(forecast_wps_3d_avg, wind_score_max_3d, inputs_today.tropical_flag)

    wind_48h_ago_score = 30
    sts = apply_florida_wind_nuance(
        sts,
        wind,
        wind_48h_ago_score,
        forecast_wps_3d_avg,
        inputs_today.tropical_flag
    )

    av = compute_av(sts, vex, fpc)
    state_label = label_state(cai, av)

    scores = {
        "HeatScore": heat,
        "RainScore": rain,
        "WindScore": wind,
        "WPS": wps,
        "ISS": iss,
        "DAS": das,
        "CAI": cai,
        "STS": sts,
        "VEX": vex,
        "FPC": fpc,
        "AV": av,
    }

    return {
        "county": county,
        "county_fips": county_fips,
        "scores": scores,
        "state": state_label
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
        payload = await compute_insurer_fl_county(county)
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

            county_meta = FL_COUNTY_META.get(county)
            county_fips = payload.get("county_fips")

            if county_meta and county_fips:
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
