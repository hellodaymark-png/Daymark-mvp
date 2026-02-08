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
    alert_count = await get_nws_alert_count(lat, lon)

    if alert_count == 0:
        status = "GREEN"
        score = 0
        drivers = ["No active weather alerts"]
        add_items = []
    elif alert_count == 1:
        status = "YELLOW"
        score = 20
        drivers = ["1 active weather alert"]
        add_items = ["rain shell", "phone waterproof pouch", "small flashlight"]
    else:
        status = "ORANGE"
        score = 35
        drivers = [f"{alert_count} active weather alerts"]
        add_items = ["rain shell", "phone waterproof pouch", "small flashlight", "power bank"]

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
        <p><b>Status:</b> GREEN</p>
        <p style="color:#666;">(Next: live signals)</p>
      </body>
    </html>
    """
