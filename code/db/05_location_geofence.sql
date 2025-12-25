-- P0 Location/Geofence tables
CREATE TABLE IF NOT EXISTS stage (
  theatre_id UUID NOT NULL REFERENCES theatre(theatre_id) ON DELETE CASCADE,
  stage_id TEXT NOT NULL,
  name TEXT NOT NULL,
  tags_jsonb JSONB NOT NULL DEFAULT '[]'::jsonb,
  location_geog GEOGRAPHY(Point, 4326) NOT NULL,
  geohash6 TEXT,
  ringc_m INTEGER NOT NULL,
  ringb_m INTEGER NOT NULL,
  ringa_m INTEGER NOT NULL,
  safe_only BOOLEAN NOT NULL DEFAULT TRUE,
  open_hours TEXT,
  status TEXT NOT NULL DEFAULT 'OPEN',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (theatre_id, stage_id)
);
CREATE INDEX IF NOT EXISTS idx_stage_geog ON stage USING GIST(location_geog);
CREATE INDEX IF NOT EXISTS idx_stage_geohash6 ON stage(geohash6);

CREATE TABLE IF NOT EXISTS stage_safety_override (
  override_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  theatre_id UUID NOT NULL REFERENCES theatre(theatre_id) ON DELETE CASCADE,
  stage_id TEXT NOT NULL,
  ringa_enabled BOOLEAN NOT NULL,
  reason TEXT,
  operator TEXT NOT NULL,
  expires_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS user_location_sample (
  sample_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id TEXT NOT NULL,
  theatre_id UUID NOT NULL REFERENCES theatre(theatre_id) ON DELETE CASCADE,
  geohash6 TEXT NOT NULL,
  accuracy_m INTEGER NOT NULL,
  speed_mps DOUBLE PRECISION NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  ttl_expires_at TIMESTAMPTZ NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_user_loc_user_time ON user_location_sample(user_id, created_at);

CREATE TABLE IF NOT EXISTS location_risk_flag (
  user_id TEXT NOT NULL,
  theatre_id UUID NOT NULL REFERENCES theatre(theatre_id) ON DELETE CASCADE,
  risk_level TEXT NOT NULL,
  reason TEXT,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (user_id, theatre_id)
);

CREATE TABLE IF NOT EXISTS ring_attestation (
  attest_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id TEXT NOT NULL,
  theatre_id UUID NOT NULL REFERENCES theatre(theatre_id) ON DELETE CASCADE,
  slot_id TEXT,
  stage_id TEXT NOT NULL,
  ring_level TEXT NOT NULL,
  issued_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  expires_at TIMESTAMPTZ NOT NULL,
  risk_score DOUBLE PRECISION NOT NULL DEFAULT 0
);
