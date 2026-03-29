from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Any, Dict, List
from datetime import datetime, timedelta, timezone
import json

from app.db import get_conn

trend_router = APIRouter(prefix="/api/trends", tags=["trends"])


class SnapshotOut(BaseModel):
    snapshot_ts: datetime
    risk_score: Optional[float] = None
    grid_stress_score: Optional[float] = None
    weather_stress_score: Optional[float] = None
    payload: Optional[Dict[str, Any]] = None


class TrendMeta(BaseModel):
    direction: str
    strength: int
    arrow: str
    label: str
    delta_7d: float
    confirmed: bool


class TrendLatestOut(BaseModel):
    county_fips: str
    latest: Optional[SnapshotOut] = None
    trend: Optional[TrendMeta] = None


class TrendLast7Out(BaseModel):
    county_fips: str
    points: List[SnapshotOut]


def normalize_snapshot_row(row):
    if not row:
        return None

    data = dict(row)

    payload = data.get("payload")
    if isinstance(payload, str):
        try:
            data["payload"] = json.loads(payload)
        except json.JSONDecodeError:
            data["payload"] = {"raw": payload}

    return data


def compute_trend_from_scores(scores: List[float]) -> Dict[str, Any]:
    """
    scores must be ordered oldest -> newest
    """

    if len(scores) < 7:
        return {
            "direction": "flat",
            "strength": 0,
            "arrow": "→",
            "label": "Insufficient Data",
            "delta_7d": 0.0,
            "confirmed": False,
        }

    latest = scores[-1]
    last_7 = scores[-7:]
    avg_7 = sum(last_7) / len(last_7)

    delta_7d = latest - avg_7
    abs_delta = abs(delta_7d)

    if abs_delta < 2:
        return {
            "direction": "flat",
            "strength": 0,
            "arrow": "→",
            "label": "Stable",
            "delta_7d": round(delta_7d, 2),
            "confirmed": True,
        }

    direction = "up" if delta_7d > 0 else "down"

    if abs_delta < 5:
        strength = 1
    elif abs_delta < 10:
        strength = 2
    else:
        strength = 3

    # Consistency check using last 3 moves
    if len(scores) >= 4:
        d1 = scores[-1] - scores[-2]
        d2 = scores[-2] - scores[-3]
        d3 = scores[-3] - scores[-4]

        positives = sum(d > 0 for d in [d1, d2, d3])
        negatives = sum(d < 0 for d in [d1, d2, d3])

        confirmed = (
            (direction == "up" and positives >= 2) or
            (direction == "down" and negatives >= 2)
        )
    else:
        confirmed = False

    if not confirmed:
        strength = max(strength - 1, 0)

    if strength == 0:
        return {
            "direction": "flat",
            "strength": 0,
            "arrow": "→",
            "label": "Stable",
            "delta_7d": round(delta_7d, 2),
            "confirmed": False,
        }

    arrows = {
        ("up", 1): "↑",
        ("up", 2): "↑↑",
        ("up", 3): "↑↑↑",
        ("down", 1): "↓",
        ("down", 2): "↓↓",
        ("down", 3): "↓↓↓",
    }

    labels = {
        ("up", 1): "Rising",
        ("up", 2): "Rising Fast",
        ("up", 3): "Surging Risk",
        ("down", 1): "Improving",
        ("down", 2): "Improving Fast",
        ("down", 3): "Rapid Improvement",
    }

    return {
        "direction": direction,
        "strength": strength,
        "arrow": arrows[(direction, strength)],
        "label": labels[(direction, strength)],
        "delta_7d": round(delta_7d, 2),
        "confirmed": confirmed,
    }


@trend_router.get("/county/{fips}/latest", response_model=TrendLatestOut)
async def trend_latest(fips: str):
    if len(fips) != 5:
        raise HTTPException(status_code=400, detail="FIPS must be 5 chars")

    async with get_conn() as conn:
        rows = await conn.fetch(
            """
            SELECT snapshot_ts, risk_score, grid_stress_score, weather_stress_score, payload
            FROM county_snapshots
            WHERE county_fips = $1
            ORDER BY snapshot_ts DESC
            LIMIT 10
            """,
            fips,
        )

    if not rows:
        return {
            "county_fips": fips,
            "latest": None,
            "trend": None,
        }

    latest_row = rows[0]
    ordered_rows = list(reversed(rows))

    scores = [
        float(r["risk_score"])
        for r in ordered_rows
        if r["risk_score"] is not None
    ]

    trend = compute_trend_from_scores(scores)

    return {
        "county_fips": fips,
        "latest": normalize_snapshot_row(latest_row),
        "trend": trend,
    }


@trend_router.get("/county/{fips}/last7", response_model=TrendLast7Out)
async def trend_last7(fips: str):
    if len(fips) != 5:
        raise HTTPException(status_code=400, detail="FIPS must be 5 chars")

    now = datetime.now(timezone.utc)
    start = now - timedelta(days=7)

    async with get_conn() as conn:
        rows = await conn.fetch(
            """
            SELECT snapshot_ts, risk_score, grid_stress_score, weather_stress_score, payload
            FROM county_snapshots
            WHERE county_fips = $1
              AND snapshot_ts >= $2
              AND snapshot_ts <= $3
            ORDER BY snapshot_ts ASC
            """,
            fips,
            start,
            now,
        )
