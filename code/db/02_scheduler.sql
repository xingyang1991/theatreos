-- P0 Scheduler tables
CREATE TABLE IF NOT EXISTS hour_plan (
  slot_id TEXT PRIMARY KEY,
  theatre_id UUID NOT NULL REFERENCES theatre(theatre_id) ON DELETE CASCADE,
  start_at TIMESTAMPTZ NOT NULL,
  end_at TIMESTAMPTZ NOT NULL,
  scenes_parallel INTEGER NOT NULL DEFAULT 8,
  primary_thread TEXT NOT NULL,
  support_threads_jsonb JSONB NOT NULL DEFAULT '[]'::jsonb,
  target_beat_mix_jsonb JSONB NOT NULL DEFAULT '{}'::jsonb,
  hour_gate_jsonb JSONB NOT NULL DEFAULT '{}'::jsonb,
  must_drop_jsonb JSONB NOT NULL DEFAULT '[]'::jsonb,
  status TEXT NOT NULL DEFAULT 'CREATED',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_hour_plan_theatre_start ON hour_plan(theatre_id, start_at);

CREATE TABLE IF NOT EXISTS hour_plan_override (
  override_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  slot_id TEXT NOT NULL REFERENCES hour_plan(slot_id) ON DELETE CASCADE,
  theatre_id UUID NOT NULL REFERENCES theatre(theatre_id) ON DELETE CASCADE,
  override_jsonb JSONB NOT NULL,
  reason TEXT,
  operator TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_hour_override_slot ON hour_plan_override(slot_id);

CREATE TABLE IF NOT EXISTS schedule_publication (
  theatre_id UUID NOT NULL REFERENCES theatre(theatre_id) ON DELETE CASCADE,
  slot_id TEXT NOT NULL REFERENCES hour_plan(slot_id) ON DELETE CASCADE,
  publish_version INTEGER NOT NULL,
  published_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  notes TEXT,
  PRIMARY KEY (theatre_id, slot_id, publish_version)
);
