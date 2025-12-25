#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Batch create stages from a JSON seed file.

Usage:
  python create_stages_batch.py \
    --base-url http://localhost:8000 \
    --theatre-id <THEATRE_ID> \
    --seed ./stages/shanghai_hp_stages_200.json \
    --token <OPTIONAL_BEARER_TOKEN>

Notes:
- The JSON schema of each item matches CreateStageRequest in backend/gateway:
  stage_id, name, lat, lng, ringc_m, ringb_m, ringa_m, tags, safe_only
"""
import argparse
import json
import sys
from pathlib import Path

import requests

def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--base-url", required=True, help="Gateway base url, e.g. http://127.0.0.1:8000")
    p.add_argument("--theatre-id", required=True, help="Target theatre_id")
    p.add_argument("--seed", required=True, help="Path to stage seed json")
    p.add_argument("--token", default="", help="Bearer token (optional)")
    p.add_argument("--dry-run", action="store_true", help="Only print what would be created")
    return p.parse_args()

def main():
    args = parse_args()
    seed_path = Path(args.seed)
    if not seed_path.exists():
        print(f"[ERR] Seed file not found: {seed_path}", file=sys.stderr)
        sys.exit(1)

    stages = json.loads(seed_path.read_text(encoding="utf-8"))
    if not isinstance(stages, list):
        print("[ERR] Seed must be a JSON array", file=sys.stderr)
        sys.exit(1)

    url = args.base_url.rstrip("/") + f"/v1/theatres/{args.theatre_id}/stages"
    headers = {"Content-Type":"application/json"}
    if args.token:
        headers["Authorization"] = f"Bearer {args.token}"

    ok = 0
    fail = 0
    for s in stages:
        if args.dry_run:
            print(f"[DRY] {s.get('stage_id')}  {s.get('name')}")
            continue
        r = requests.post(url, headers=headers, data=json.dumps(s, ensure_ascii=False).encode("utf-8"), timeout=20)
        if r.status_code in (200, 201):
            ok += 1
        else:
            fail += 1
            print(f"[FAIL] {s.get('stage_id')} {s.get('name')} -> {r.status_code}: {r.text[:500]}", file=sys.stderr)

    print(f"[DONE] ok={ok} fail={fail} total={len(stages)}")
    if fail > 0:
        sys.exit(2)

if __name__ == "__main__":
    main()
