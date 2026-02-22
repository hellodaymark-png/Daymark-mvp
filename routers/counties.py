from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional

# IMPORTANT: replace this import with YOUR db connector
# e.g. from db import get_conn OR from app.db import get_conn
from db import get_conn  # <-- change this line to match your project

router = APIRouter(prefix="/api/counties", tags=["counties"])

class CountyInputV1(BaseModel):
    fips: str = Field(..., min_length=5, max_length=5)
    state: str = Field(..., min_length=2, max_length=2)
    county_name: str
    centroid_lat: float
    centroid_lon: float
    pop_density_per_sqmi: Optional[float] = None

@router.get("/{fips}", response_model=CountyInputV1)
async def get_county(fips: str):
    if len(fips) != 5:
        raise HTTPException(status_code=400, detail="FIPS must be 5 chars")

    async with get_conn() as conn:
        row = await conn.fetchrow("""
            SELECT fips, state, county_name, centroid_lat, centroid_lon, pop_density_per_sqmi
            FROM counties
            WHERE fips = $1
        """, fips)

    if not row:
        raise HTTPException(status_code=404, detail="County not found")

    return dict(row)

@router.post("", response_model=CountyInputV1)
async def upsert_county(payload: CountyInputV1):
    async with get_conn() as conn:
        row = await conn.fetchrow("""
            INSERT INTO counties (fips, state, county_name, centroid_lat, centroid_lon, pop_density_per_sqmi)
            VALUES ($1,$2,$3,$4,$5,$6)
            ON CONFLICT (fips) DO UPDATE SET
              state = EXCLUDED.state,
              county_name = EXCLUDED.county_name,
              centroid_lat = EXCLUDED.centroid_lat,
              centroid_lon = EXCLUDED.centroid_lon,
              pop_density_per_sqmi = EXCLUDED.pop_density_per_sqmi,
              updated_at = NOW()
            RETURNING fips, state, county_name, centroid_lat, centroid_lon, pop_density_per_sqmi
        """, payload.fips, payload.state.upper(), payload.county_name,
             payload.centroid_lat, payload.centroid_lon, payload.pop_density_per_sqmi)

    return dict(row)
