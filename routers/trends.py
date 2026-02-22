from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Any, Dict, List
from datetime import datetime, timedelta, timezone

from db import get_conn  # <-- change this line to match your project

trend_router = APIRouter(prefix="/api/trends", tags=["trends"])

class SnapshotOut(BaseModel):
    snapshot_ts: datetime
    risk_score: Optional[float] = None
    grid_stress_score: Optional[float] = None
    weather_stress_score: Optional[float] = None
    payload: Optional[Dict[str, Any]] = None

class TrendLatestOut(BaseModel):
    county_fips: str
    latest: Optional[SnapshotOut] = None

class TrendLast7Out(BaseModel):
    county_fips: str
    points: List[SnapshotOut]

@trend_router.get("/county/{fips}/latest", response_model=TrendLatestOut)
async def trend_latest(fips: str):
    if len(fips) != 5:
        raise HTTPException(status_code=400, detail="FIPS must be 5 chars")

    async with get_conn() as conn:
        row = await conn.fetchrow("""
            SELECT snapshot_ts, risk_score, grid_stress_score, weather_stress_score, payload
            FROM county_snapshots
            WHERE county_fips = $1
            ORDER BY snapshot_ts DESC
            LIMIT 1
        """, fips)

    return {"county_fips": fips, "latest": dict(row) if row else None}

@trend_router.get("/county/{fips}/last7", response_model=TrendLast7Out)
async def trend_last7(fips: str):
    if len(fips) != 5:
        raise HTTPException(status_code=400, detail="FIPS must be 5 chars")

    now = datetime.now(timezone.utc)
    start = now - timedelta(days=7)

    async with get_conn() as conn:
        rows = await conn.fetch("""
            SELECT snapshot_ts, risk_score, grid_stress_score, weather_stress_score, payload
            FROM county_snapshots
            WHERE county_fips = $1
              AND snapshot_ts >= $2
              AND snapshot_ts <= $3
            ORDER BY snapshot_ts ASC
        """, fips, start, now)

    return {"county_fips": fips, "points": [dict(r) for r in rows]}
