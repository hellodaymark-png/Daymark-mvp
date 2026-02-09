from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse
import httpx

app = FastAPI()

NWS_BASE = "https://api.weather.gov"

@app.get("/health")
def health():
    return {"status": "ok"}

async def get_nws_alert_count(lat: float, lon: float) -> int:
    # Alerts are returned by "zone". Easiest v1 query: alerts active for the point
    url = f"{NWS_BASE}/alerts/active"
    params = {"point": f"{lat},{lon}"}
    headers = {"User-Agent": "Daymark (hello.daymark@gmail.com)"}

    async with httpx.AsyncClient(timeout=15.0) as client:
        r = await client.get(url, params=params, headers=headers)
        r.raise_for_status()
        data = r.json()

    return len(data.get("features", []))

@app.get("/api/daymark")
async def daymark(lat: float = Query(...), lon: float = Query(...)):
    score = 0
    drivers = []
    add_items = []

    # ---- Weather alerts (NWS) ----
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

    # ---- Air quality (OpenAQ → PM2.5 → AQI estimate) ----
    pm25 = await get_openaq_pm25(lat, lon)
    if pm25 is None:
        drivers.append("Air quality: unavailable")
    else:
        aqi = pm25_to_aqi(pm25)
        cat = aqi_category(aqi)
        drivers.append(f"Air quality: AQI ~ {aqi} ({cat})")

        if 51 <= aqi <= 100:
            score += 10
            add_items += ["extra water"]
        elif aqi >= 101:
            score += 25
            add_items += ["KN95/N95 mask", "eye drops", "extra water"]

    # ---- Overall status from score ----
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
    }

@app.get("/", response_class=HTMLResponse)
def home():
    return """
    <html>
      <head>
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <title>Daymark</title>
      </head>
      <body style="font-family: system-ui; padding: 24px;">
        <h1>Daymark</h1>
        <p>A calm reference point for today.</p>

        <p id="status">Loading status…</p>
        <p id="drivers" style="color:#555;"></p>

        <script>
          fetch("/api/daymark?lat=30.0922&lon=-81.5723")
            .then(r => r.json())
            .then(data => {
              document.getElementById("status").innerHTML =
                "<b>Status:</b> " + data.status;
              document.getElementById("drivers").innerText =
                data.drivers.join(" • ");
            })
            .catch(() => {
              document.getElementById("status").innerText =
                "Status unavailable";
            });
        </script>
      </body>
    </html>
    """
