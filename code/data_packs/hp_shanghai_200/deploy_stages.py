#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TheatreOS HP Shanghai 200 Stages 部署脚本
将200个舞台数据部署到后端系统

用法:
  python deploy_stages.py --base-url http://localhost:8000 --theatre-id <THEATRE_ID>
  python deploy_stages.py --base-url http://120.55.162.182 --theatre-id hp_shanghai_theatre
"""
import argparse
import json
import sys
import time
from pathlib import Path
from typing import List, Dict, Any

try:
    import requests
except ImportError:
    print("请安装 requests: pip install requests")
    sys.exit(1)

# 数据包根目录
DATA_PACK_ROOT = Path(__file__).parent


def load_stages() -> List[Dict]:
    """加载舞台数据"""
    stages_file = DATA_PACK_ROOT / "stages" / "shanghai_hp_stages_200.json"
    if not stages_file.exists():
        print(f"[ERR] 舞台数据文件不存在: {stages_file}")
        sys.exit(1)
    return json.loads(stages_file.read_text(encoding="utf-8"))


def load_stage_meta() -> Dict[str, Dict]:
    """加载舞台元数据，返回以stage_id为key的字典"""
    meta_file = DATA_PACK_ROOT / "stages" / "shanghai_hp_stage_meta_200.json"
    if not meta_file.exists():
        return {}
    meta_list = json.loads(meta_file.read_text(encoding="utf-8"))
    return {m["stage_id"]: m for m in meta_list}


def create_theatre(base_url: str, theatre_id: str, headers: Dict) -> bool:
    """创建剧场（如果不存在）"""
    url = f"{base_url}/v1/theatres"
    payload = {
        "theatre_id": theatre_id,
        "name": "HP上海魔法世界",
        "description": "哈利波特主题上海城市剧场 - 200个魔法舞台",
        "theme_pack_id": "hp_shanghai_s1",
        "timezone": "Asia/Shanghai",
    }
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=30)
        if r.status_code in (200, 201):
            print(f"[OK] 剧场创建成功: {theatre_id}")
            return True
        elif r.status_code == 409:  # 已存在
            print(f"[INFO] 剧场已存在: {theatre_id}")
            return True
        else:
            print(f"[WARN] 剧场创建失败: {r.status_code} - {r.text[:200]}")
            return True  # 继续尝试创建舞台
    except Exception as e:
        print(f"[WARN] 剧场创建异常: {e}")
        return True  # 继续尝试


def create_stage(base_url: str, theatre_id: str, stage: Dict, meta: Dict, headers: Dict) -> bool:
    """创建单个舞台"""
    url = f"{base_url}/v1/theatres/{theatre_id}/stages"
    
    # 合并基础数据和元数据
    payload = {
        "stage_id": stage["stage_id"],
        "name": stage["name"],
        "lat": stage["lat"],
        "lng": stage["lng"],
        "ringc_m": stage.get("ringc_m", 1200),
        "ringb_m": stage.get("ringb_m", 500),
        "ringa_m": stage.get("ringa_m", 80),
        "tags": stage.get("tags", []),
        "safe_only": stage.get("safe_only", True),
    }
    
    # 添加元数据（如果有）
    if meta:
        payload["meta"] = {
            "district": meta.get("district"),
            "real_spot": meta.get("real_spot"),
            "wizarding_alias": meta.get("wizarding_alias"),
            "wizarding_zone": meta.get("wizarding_zone"),
            "canon_ref": meta.get("canon_ref"),
            "recommended_threads": meta.get("recommended_threads", []),
            "prompt_seed": meta.get("prompt_seed"),
            "story_hook": meta.get("story_hook"),
            "npc_hint": meta.get("npc_hint"),
        }
    
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=30)
        if r.status_code in (200, 201):
            return True
        elif r.status_code == 409:  # 已存在
            return True
        else:
            print(f"[FAIL] {stage['stage_id']}: {r.status_code} - {r.text[:100]}")
            return False
    except Exception as e:
        print(f"[ERR] {stage['stage_id']}: {e}")
        return False


def deploy_stages(base_url: str, theatre_id: str, token: str = "", 
                  batch_size: int = 10, dry_run: bool = False) -> Dict[str, int]:
    """批量部署舞台"""
    stages = load_stages()
    meta_dict = load_stage_meta()
    
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    
    print(f"\n=== HP Shanghai 200 Stages 部署 ===")
    print(f"目标: {base_url}")
    print(f"剧场: {theatre_id}")
    print(f"舞台数: {len(stages)}")
    print(f"批次大小: {batch_size}")
    print()
    
    if dry_run:
        print("[DRY RUN] 仅打印，不实际创建")
        for s in stages:
            print(f"  {s['stage_id']}: {s['name']}")
        return {"ok": len(stages), "fail": 0, "total": len(stages)}
    
    # 创建剧场
    create_theatre(base_url, theatre_id, headers)
    
    # 批量创建舞台
    ok = 0
    fail = 0
    
    for i, stage in enumerate(stages):
        meta = meta_dict.get(stage["stage_id"], {})
        if create_stage(base_url, theatre_id, stage, meta, headers):
            ok += 1
        else:
            fail += 1
        
        # 进度显示
        if (i + 1) % batch_size == 0:
            print(f"[进度] {i + 1}/{len(stages)} (成功: {ok}, 失败: {fail})")
            time.sleep(0.1)  # 避免请求过快
    
    print()
    print(f"=== 部署完成 ===")
    print(f"成功: {ok}")
    print(f"失败: {fail}")
    print(f"总计: {len(stages)}")
    
    return {"ok": ok, "fail": fail, "total": len(stages)}


def main():
    parser = argparse.ArgumentParser(description="部署HP上海200舞台数据")
    parser.add_argument("--base-url", required=True, help="后端API地址")
    parser.add_argument("--theatre-id", default="hp_shanghai_theatre", help="剧场ID")
    parser.add_argument("--token", default="", help="认证Token")
    parser.add_argument("--batch-size", type=int, default=10, help="批次大小")
    parser.add_argument("--dry-run", action="store_true", help="仅打印不执行")
    
    args = parser.parse_args()
    
    result = deploy_stages(
        base_url=args.base_url.rstrip("/"),
        theatre_id=args.theatre_id,
        token=args.token,
        batch_size=args.batch_size,
        dry_run=args.dry_run,
    )
    
    if result["fail"] > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
