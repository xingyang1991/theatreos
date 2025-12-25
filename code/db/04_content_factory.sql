-- P0 Content Factory tables
CREATE TABLE IF NOT EXISTS generation_job (
  job_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  theatre_id UUID NOT NULL REFERENCES theatre(theatre_id) ON DELETE CASCADE,
  slot_id TEXT NOT NULL REFERENCES hour_plan(slot_id) ON DELETE CASCADE,
  status TEXT NOT NULL, -- CREATED/RUNNING/FAILED/PUBLISHED
  deadline_at TIMESTAMPTZ NOT NULL,
  attempt INTEGER NOT NULL DEFAULT 0,
  plan_hash TEXT NOT NULL,
  fail_reason TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(theatre_id, slot_id, plan_hash)
);

CREATE TABLE IF NOT EXISTS generation_step_log (
  log_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  job_id UUID NOT NULL REFERENCES generation_job(job_id) ON DELETE CASCADE,
  step_name TEXT NOT NULL,
  status TEXT NOT NULL,
  started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  ended_at TIMESTAMPTZ,
  error TEXT
);

CREATE TABLE IF NOT EXISTS scene_draft (
  scene_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  job_id UUID NOT NULL REFERENCES generation_job(job_id) ON DELETE CASCADE,
  theatre_id UUID NOT NULL REFERENCES theatre(theatre_id) ON DELETE CASCADE,
  slot_id TEXT NOT NULL REFERENCES hour_plan(slot_id) ON DELETE CASCADE,
  stage_id TEXT NOT NULL,
  thread_id TEXT NOT NULL,
  beat_id TEXT NOT NULL,
  ring_min TEXT NOT NULL DEFAULT 'C',
  draft_jsonb JSONB NOT NULL,
  compiler_status TEXT NOT NULL DEFAULT 'PENDING',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS render_asset (
  asset_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  scene_id UUID NOT NULL REFERENCES scene_draft(scene_id) ON DELETE CASCADE,
  type TEXT NOT NULL, -- IMAGE/AUDIO/VIDEO
  provider TEXT NOT NULL,
  url TEXT NOT NULL,
  status TEXT NOT NULL,
  hash TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS moderation_ticket (
  ticket_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  target_type TEXT NOT NULL, -- SCENE/ASSET
  target_id UUID NOT NULL,
  status TEXT NOT NULL,
  reason TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS published_slot (
  theatre_id UUID NOT NULL REFERENCES theatre(theatre_id) ON DELETE CASCADE,
  slot_id TEXT NOT NULL REFERENCES hour_plan(slot_id) ON DELETE CASCADE,
  publish_version INTEGER NOT NULL,
  payload_jsonb JSONB NOT NULL,
  published_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  source_job_id UUID,
  PRIMARY KEY (theatre_id, slot_id, publish_version)
);

CREATE TABLE IF NOT EXISTS rescue_bundle (
  rescue_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  theatre_id UUID NOT NULL REFERENCES theatre(theatre_id) ON DELETE CASCADE,
  type TEXT NOT NULL, -- SILENCE/AFTERMATH/BROADCAST
  payload_jsonb JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
