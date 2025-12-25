-- P0 Kernel tables
CREATE TABLE IF NOT EXISTS theatre (
  theatre_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  city TEXT NOT NULL,
  timezone TEXT NOT NULL DEFAULT 'Asia/Shanghai',
  theme_id TEXT NOT NULL,
  theme_version TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'ACTIVE',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS world_var_current (
  theatre_id UUID NOT NULL REFERENCES theatre(theatre_id) ON DELETE CASCADE,
  var_id TEXT NOT NULL,
  value DOUBLE PRECISION NOT NULL CHECK (value >= 0 AND value <= 1),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (theatre_id, var_id)
);

CREATE TABLE IF NOT EXISTS thread_state_current (
  theatre_id UUID NOT NULL REFERENCES theatre(theatre_id) ON DELETE CASCADE,
  thread_id TEXT NOT NULL,
  phase_id TEXT NOT NULL,
  progress INTEGER NOT NULL DEFAULT 0,
  branch_bucket TEXT NOT NULL,
  locks_jsonb JSONB NOT NULL DEFAULT '{}'::jsonb,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (theatre_id, thread_id)
);

CREATE TABLE IF NOT EXISTS object_holder_current (
  theatre_id UUID NOT NULL REFERENCES theatre(theatre_id) ON DELETE CASCADE,
  object_id TEXT NOT NULL,
  holder_type TEXT NOT NULL,
  holder_id TEXT NOT NULL,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (theatre_id, object_id)
);

CREATE TABLE IF NOT EXISTS world_state_snapshot (
  theatre_id UUID NOT NULL REFERENCES theatre(theatre_id) ON DELETE CASCADE,
  tick_id BIGINT NOT NULL,
  version BIGINT NOT NULL,
  state_jsonb JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (theatre_id, tick_id)
);

CREATE TABLE IF NOT EXISTS world_event_log (
  event_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  theatre_id UUID NOT NULL REFERENCES theatre(theatre_id) ON DELETE CASCADE,
  tick_id BIGINT NOT NULL,
  type TEXT NOT NULL,
  payload_jsonb JSONB NOT NULL,
  delta_id TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_world_event_theatre_tick ON world_event_log(theatre_id, tick_id);
CREATE INDEX IF NOT EXISTS idx_world_event_type ON world_event_log(type);

CREATE TABLE IF NOT EXISTS world_delta_idempotency (
  delta_id TEXT PRIMARY KEY,
  theatre_id UUID NOT NULL REFERENCES theatre(theatre_id) ON DELETE CASCADE,
  applied_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  result_hash TEXT NOT NULL
);
