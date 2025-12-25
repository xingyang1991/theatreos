"""
转换原始数据文件为标准主题包格式
"""
import json
import os
from pathlib import Path

PACK_DIR = Path("/home/ubuntu/theatreos/theme_pack/packs/hp_shanghai_s1")


def convert_threads():
    """转换故事线数据"""
    with open(PACK_DIR / "threads_raw.json", 'r', encoding='utf-8') as f:
        raw = json.load(f)
    
    threads = []
    for t in raw.get("threads", []):
        threads.append({
            "thread_id": t["thread_id"],
            "name": t["name"],
            "logline": t.get("logline", ""),
            "key_objects": t.get("key_objects", []),
            "key_stages": t.get("key_stages", []),
            "world_vars": t.get("world_vars", []),
            "phases": [
                {
                    "phase": p["phase"],
                    "name_cn": p.get("cn", ""),
                    "goal": p.get("goal", ""),
                    "allowed_beat_types": p.get("allowed_beat_types", [])
                }
                for p in t.get("phases", [])
            ],
            "crosslinks": t.get("crosslinks", [])
        })
    
    output = {"threads": threads}
    with open(PACK_DIR / "threads.json", 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print(f"Converted {len(threads)} threads")
    return threads


def convert_world_variables():
    """从threads_raw提取世界变量"""
    with open(PACK_DIR / "threads_raw.json", 'r', encoding='utf-8') as f:
        raw = json.load(f)
    
    world_vars = []
    for w in raw.get("world_vars", []):
        world_vars.append({
            "id": w["id"],
            "name_cn": w.get("cn", ""),
            "description": w.get("desc", ""),
            "default_value": 0.5,
            "min_value": 0.0,
            "max_value": 1.0,
            "max_change_per_hour": 0.15
        })
    
    output = {"world_vars": world_vars}
    with open(PACK_DIR / "world_variables.json", 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print(f"Converted {len(world_vars)} world variables")
    return world_vars


def convert_objects():
    """从threads_raw提取关键物品"""
    with open(PACK_DIR / "threads_raw.json", 'r', encoding='utf-8') as f:
        raw = json.load(f)
    
    objects = []
    for o in raw.get("objects", []):
        objects.append({
            "object_id": o["object_id"],
            "name": o["name"],
            "description": o.get("desc", ""),
            "related_threads": []
        })
    
    output = {"objects": objects}
    with open(PACK_DIR / "objects.json", 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print(f"Converted {len(objects)} objects")
    return objects


def convert_factions():
    """从threads_raw提取阵营"""
    with open(PACK_DIR / "threads_raw.json", 'r', encoding='utf-8') as f:
        raw = json.load(f)
    
    factions = []
    for f_data in raw.get("factions", []):
        factions.append({
            "faction_id": f_data["faction_id"],
            "name": f_data["name"],
            "style": f_data.get("style", ""),
            "related_characters": []
        })
    
    output = {"factions": factions}
    with open(PACK_DIR / "factions.json", 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print(f"Converted {len(factions)} factions")
    return factions


def convert_beats():
    """转换拍子模板"""
    with open(PACK_DIR / "beats_raw.json", 'r', encoding='utf-8') as f:
        raw = json.load(f)
    
    beats = raw.get("beat_templates", [])
    
    output = {"beat_templates": beats}
    with open(PACK_DIR / "beats.json", 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print(f"Converted {len(beats)} beat templates")
    return beats


def convert_gates():
    """转换门模板"""
    with open(PACK_DIR / "gates_raw.json", 'r', encoding='utf-8') as f:
        raw = json.load(f)
    
    gates = raw.get("gate_templates", [])
    
    output = {"gate_templates": gates}
    with open(PACK_DIR / "gates.json", 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print(f"Converted {len(gates)} gate templates")
    return gates


def convert_evidence():
    """转换证物类型"""
    with open(PACK_DIR / "evidence_raw.json", 'r', encoding='utf-8') as f:
        raw = json.load(f)
    
    evidence_types = raw.get("evidence_types", [])
    
    output = {"evidence_types": evidence_types}
    with open(PACK_DIR / "evidence.json", 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print(f"Converted {len(evidence_types)} evidence types")
    return evidence_types


def convert_rescue_beats():
    """转换救援拍子"""
    with open(PACK_DIR / "rescue_beats_raw.json", 'r', encoding='utf-8') as f:
        raw = json.load(f)
    
    rescue_beats = raw.get("rescue_beats", [])
    
    output = {"rescue_beats": rescue_beats}
    with open(PACK_DIR / "rescue_beats.json", 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print(f"Converted {len(rescue_beats)} rescue beats")
    return rescue_beats


def main():
    print("Converting raw data to theme pack format...")
    print("=" * 50)
    
    convert_threads()
    convert_world_variables()
    convert_objects()
    convert_factions()
    convert_beats()
    convert_gates()
    convert_evidence()
    convert_rescue_beats()
    
    print("=" * 50)
    print("Conversion complete!")
    
    # 清理原始文件
    for f in PACK_DIR.glob("*_raw.json"):
        os.remove(f)
        print(f"Removed {f.name}")


if __name__ == "__main__":
    main()
