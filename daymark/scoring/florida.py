from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse
import os
import httpx

from datetime import datetime
from florida_scoring import (   
    FloridaInputs,
    heat_score_fl, rain_score_fl, wind_score_fl,
    compute_wps_fl, compute_iss_fl, compute_cai_fl,
    sts_from_delta_cai, vex_from_range, fpc_from_forecast,
    apply_florida_wind_nuance, compute_av, label_state
)

router = APIRouter()

@router.get("/api/insurer/florida")
def insurer_florida_example(county: str = "Duval"):
    # TODO: replace these with real pulls (weather feed + county metadata)
    inputs_today = FloridaInputs(
        month=2,
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
    persistence = 40  # TODO: compute from last 10 days heat score
    iss = compute_iss_fl(heat, inputs_today.pop_density, persistence)
    das = 10          # v1 default
    cai = compute_cai_fl(wps, iss, das)

    # TODO: replace with actual CAI history from store/DB
    cai_history_5d = [45, 47, 50, 54, cai]
    delta_3d = cai - cai_history_5d[-4]
    sts = sts_from_delta_cai(delta_3d)

    range_5d = max(cai_history_5d) - min(cai_history_5d)
    vex = vex_from_range(range_5d)

    forecast_wps_3d_avg = wps  # TODO: compute from forecast days
    wind_score_max_3d = wind   # TODO: compute from forecast days
    fpc = fpc_from_forecast(forecast_wps_3d_avg, wind_score_max_3d, inputs_today.tropical_flag)

    # Florida wind nuance needs wind scores (today vs 48h)
    wind_48h_ago = 30  # TODO from history
    sts = apply_florida_wind_nuance(sts, wind, wind_48h_ago, forecast_wps_3d_avg, inputs_today.tropical_flag)

    av = compute_av(sts, vex, fpc)
    state = label_state(cai, av)

    return {
        "county": county,
        "WPS": wps, "ISS": iss, "DAS": das,
        "CAI": cai,
        "STS": sts, "VEX": vex, "FPC": fpc,
        "AV": av,
        "state": state
    }
