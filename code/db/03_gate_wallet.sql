-- P0 Gate + Wallet tables
CREATE TABLE IF NOT EXISTS gate_instance (
  gate_instance_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  theatre_id UUID NOT NULL REFERENCES theatre(theatre_id) ON DELETE CASCADE,
  slot_id TEXT NOT NULL REFERENCES hour_plan(slot_id) ON DELETE CASCADE,
  gate_template_id TEXT NOT NULL,
  type TEXT NOT NULL, -- Public/Fate/FateMajor/Council
  status TEXT NOT NULL DEFAULT 'SCHEDULED',
  title TEXT NOT NULL,
  open_at TIMESTAMPTZ NOT NULL,
  close_at TIMESTAMPTZ NOT NULL,
  resolve_at TIMESTAMPTZ NOT NULL,
  options_jsonb JSONB NOT NULL,
  base_prob_jsonb JSONB,
  random_seed BIGINT,
  winner_option_id TEXT,
  explain_card_jsonb JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_gate_slot ON gate_instance(slot_id);

CREATE TABLE IF NOT EXISTS gate_vote (
  gate_instance_id UUID NOT NULL REFERENCES gate_instance(gate_instance_id) ON DELETE CASCADE,
  user_id TEXT NOT NULL,
  option_id TEXT NOT NULL,
  ring_level TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  idempotency_key TEXT NOT NULL,
  PRIMARY KEY (gate_instance_id, user_id)
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_gate_vote_idem ON gate_vote(gate_instance_id, user_id, idempotency_key);

CREATE TABLE IF NOT EXISTS wallet_balance (
  user_id TEXT NOT NULL,
  currency TEXT NOT NULL, -- TICKET/SHARD
  balance NUMERIC(18,4) NOT NULL DEFAULT 0,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (user_id, currency)
);

CREATE TABLE IF NOT EXISTS wallet_ledger (
  tx_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id TEXT NOT NULL,
  currency TEXT NOT NULL,
  delta NUMERIC(18,4) NOT NULL,
  reason TEXT NOT NULL, -- STAKE_LOCK/STAKE_PAYOUT/STAKE_BURN/...
  ref_type TEXT,
  ref_id TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_ledger_user_time ON wallet_ledger(user_id, created_at);

CREATE TABLE IF NOT EXISTS gate_stake (
  gate_instance_id UUID NOT NULL REFERENCES gate_instance(gate_instance_id) ON DELETE CASCADE,
  user_id TEXT NOT NULL,
  currency TEXT NOT NULL,
  option_id TEXT NOT NULL,
  amount_locked NUMERIC(18,4) NOT NULL DEFAULT 0,
  amount_final NUMERIC(18,4),
  ring_level TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  idempotency_key TEXT NOT NULL,
  PRIMARY KEY (gate_instance_id, user_id, currency)
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_gate_stake_idem ON gate_stake(gate_instance_id, user_id, currency, idempotency_key);

CREATE TABLE IF NOT EXISTS gate_evidence_submission (
  submission_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  gate_instance_id UUID NOT NULL REFERENCES gate_instance(gate_instance_id) ON DELETE CASCADE,
  user_id TEXT NOT NULL,
  evidence_instance_id TEXT NOT NULL,
  tier TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  idempotency_key TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_gate_evidence_idem ON gate_evidence_submission(gate_instance_id, user_id, evidence_instance_id, idempotency_key);

CREATE TABLE IF NOT EXISTS gate_settlement (
  gate_instance_id UUID NOT NULL REFERENCES gate_instance(gate_instance_id) ON DELETE CASCADE,
  user_id TEXT NOT NULL,
  currency TEXT NOT NULL,
  stake NUMERIC(18,4) NOT NULL,
  payout NUMERIC(18,4) NOT NULL DEFAULT 0,
  fee_burn NUMERIC(18,4) NOT NULL DEFAULT 0,
  net_delta NUMERIC(18,4) NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (gate_instance_id, user_id, currency)
);
