CREATE TABLE IF NOT EXISTS counties (
  id BIGSERIAL PRIMARY KEY,
  state CHAR(2) NOT NULL,
  county_name TEXT NOT NULL,
  fips CHAR(5) NOT NULL UNIQUE,
  centroid_lat DOUBLE PRECISION NOT NULL,
  centroid_lon DOUBLE PRECISION NOT NULL,
  pop_density_per_sqmi DOUBLE PRECISION,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_counties_state_name ON counties(state, county_name);

CREATE TABLE IF NOT EXISTS county_snapshots (
  id BIGSERIAL PRIMARY KEY,
  county_fips CHAR(5) NOT NULL REFERENCES counties(fips) ON DELETE CASCADE,
  snapshot_ts TIMESTAMPTZ NOT NULL,
  risk_score DOUBLE PRECISION,
  grid_stress_score DOUBLE PRECISION,
  weather_stress_score DOUBLE PRECISION,
  payload JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_snapshots_fips_ts_desc
  ON county_snapshots(county_fips, snapshot_ts DESC);
