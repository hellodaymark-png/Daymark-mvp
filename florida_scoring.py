# florida_scoring.py
from dataclasses import dataclass
from typing import Optional

def clamp(x: float, lo: float = 0, hi: float = 100) -> float:
    return max(lo, min(hi, x))

@dataclass
class FloridaInputs:
    month: int
    heat_index_f: float
    rain_24h_in: float
    wind_sust_mph: float
    tropical_flag: bool
    pop_density: float

def density_factor(pop_density: float) -> float:
    if pop_density < 200:
        return 0.8
    if pop_density < 800:
        return 1.0
    return 1.2

def heat_score_fl(month: int, heat_index_f: float) -> float:
    # Florida hot-humid bands (v1)
    if heat_index_f <= 100: return 10
    if heat_index_f <= 105: return 25
    if heat_index_f <= 110: return 45
    if heat_index_f <= 115: return 65
    if heat_index_f <= 120: return 80
    return 95

def _rain_score_basic(r: float) -> float:
    if r < 1: return 10
    if r < 2: return 30
    if r < 4: return 55
    if r < 6: return 75
    return 90

def rain_score_fl(rain_24h_in: float, tropical_flag: bool) -> float:
    if tropical_flag:
        return max(70, _rain_score_basic(rain_24h_in))
    return _rain_score_basic(rain_24h_in)

def _wind_score_basic(w: float) -> float:
    if w < 20: return 5
    if w < 36: return 30
    if w < 51: return 55
    if w < 71: return 75
    return 95

def wind_score_fl(wind_sust_mph: float, tropical_flag: bool) -> float:
    if tropical_flag and wind_sust_mph >= 35:
        return max(75, _wind_score_basic(wind_sust_mph))
    return _wind_score_basic(wind_sust_mph)

def compute_wps_fl(heat: float, rain: float, wind: float) -> float:
    # v1 Florida: Heat 50%, Rain 30%, Wind 20%
    return clamp(0.50*heat + 0.30*rain + 0.20*wind)

def compute_iss_fl(heat_score: float, pop_density: float, persistence_0_100: float) -> float:
    load_proxy = heat_score * density_factor(pop_density)
    return clamp(0.70*load_proxy + 0.30*persistence_0_100)

def compute_cai_fl(wps: float, iss: float, das: float) -> float:
    return clamp(0.40*wps + 0.45*iss + 0.15*das)

# --- AV pieces ---
def sts_from_delta_cai(delta_3d: float) -> float:
    if delta_3d <= 2: return 10
    if delta_3d <= 6: return 30
    if delta_3d <= 10: return 55
    if delta_3d <= 15: return 75
    if delta_3d <= 22: return 90
    return 100

def vex_from_range(range_5d: float) -> float:
    if range_5d <= 6: return 10
    if range_5d <= 12: return 35
    if range_5d <= 18: return 60
    if range_5d <= 26: return 80
    return 95

def fpc_from_forecast(forecast_wps_3d_avg: float, wind_score_max_3d: float, tropical_flag: bool) -> float:
    if tropical_flag:
        return 95
    if forecast_wps_3d_avg >= 65 or wind_score_max_3d >= 75:
        return 80
    if 55 <= forecast_wps_3d_avg <= 64:
        return 60
    if 45 <= forecast_wps_3d_avg <= 54:
        return 35
    return 15

def apply_florida_wind_nuance(
    sts: float,
    wind_today_score: float,
    wind_48h_ago_score: float,
    forecast_wps_3d_avg: float,
    tropical_flag: bool
) -> float:
    # Rapid Wind Escalation Adjustment (RWEA) – your Florida nuance
    if (wind_today_score - wind_48h_ago_score) >= 25 and wind_today_score >= 55 and (tropical_flag or forecast_wps_3d_avg >= 55):
        return min(sts + 10, 100)
    return sts

def compute_av(sts: float, vex: float, fpc: float) -> float:
    return clamp(0.50*sts + 0.30*vex + 0.20*fpc)

def label_state(cai: float, av: float) -> str:
    if cai >= 85: return "Surge Risk"
    if cai >= 70 and av >= 56: return "High Risk + Accelerating"
    if av >= 76: return "Momentum Surge"
    if cai >= 55 or av >= 56: return "Building"
    return "Stable"
