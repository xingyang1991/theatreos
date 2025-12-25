"""
TheatreOS 200节点舞台配置
从HP Shanghai 200数据包加载完整的舞台数据
"""
import json
import sys
from pathlib import Path

# 添加数据包路径
DATA_PACK_PATH = Path(__file__).parent.parent / "data_packs" / "hp_shanghai_200"
sys.path.insert(0, str(DATA_PACK_PATH.parent))

try:
    from hp_shanghai_200 import get_stages, get_stage_meta, get_clusters, get_summary
except ImportError:
    # 直接从JSON加载
    def get_stages():
        stages_file = DATA_PACK_PATH / "stages" / "shanghai_hp_stages_200.json"
        return json.loads(stages_file.read_text(encoding="utf-8"))
    
    def get_stage_meta():
        meta_file = DATA_PACK_PATH / "stages" / "shanghai_hp_stage_meta_200.json"
        return json.loads(meta_file.read_text(encoding="utf-8"))
    
    def get_clusters():
        clusters_file = DATA_PACK_PATH / "lexicon" / "shanghai_hp_stage_clusters.json"
        return json.loads(clusters_file.read_text(encoding="utf-8"))
    
    def get_summary():
        return {
            "total_stages": 200,
            "total_clusters": 20,
        }


def get_shanghai_stages_200():
    """获取200个上海舞台配置（兼容旧格式）"""
    stages = get_stages()
    meta_list = get_stage_meta()
    meta_dict = {m["stage_id"]: m for m in meta_list}
    
    result = []
    for stage in stages:
        meta = meta_dict.get(stage["stage_id"], {})
        
        # 转换为兼容旧格式的结构
        stage_config = {
            "stage_id": stage["stage_id"],
            "name": stage["name"],
            "lat": stage["lat"],
            "lng": stage["lng"],
            "location_desc": meta.get("real_spot", ""),
            "hp_mapping": meta.get("wizarding_alias", ""),
            "wizarding_zone": meta.get("wizarding_zone", ""),
            "district": meta.get("district", ""),
            "tags": stage.get("tags", []),
            "ringc_m": stage.get("ringc_m", 1200),
            "ringb_m": stage.get("ringb_m", 500),
            "ringa_m": stage.get("ringa_m", 80),
            "safe_only": stage.get("safe_only", True),
            # 扩展元数据
            "canon_ref": meta.get("canon_ref", ""),
            "recommended_threads": meta.get("recommended_threads", []),
            "prompt_seed": meta.get("prompt_seed", ""),
            "story_hook": meta.get("story_hook", ""),
            "npc_hint": meta.get("npc_hint", ""),
            # 场景占位（需要内容生成填充）
            "scene": {
                "title": f"{meta.get('wizarding_alias', stage['name'])}的秘密",
                "description": meta.get("story_hook", f"在{stage['name']}发生的神秘事件"),
                "scene_text": meta.get("prompt_seed", ""),
                "npc": meta.get("npc_hint", "神秘人物").split("/")[0] if meta.get("npc_hint") else "神秘人物",
                "thread": meta.get("recommended_threads", ["main_thread"])[0] if meta.get("recommended_threads") else "main_thread",
                "evidence": f"{stage['name']}的线索"
            }
        }
        result.append(stage_config)
    
    return result


def get_cluster_info():
    """获取区域簇信息"""
    return get_clusters()


def get_stages_by_cluster_code(cluster_code: str):
    """根据簇代码获取舞台"""
    all_stages = get_shanghai_stages_200()
    clusters = get_clusters()
    
    for cluster in clusters:
        if cluster["cluster_code"] == cluster_code:
            stage_ids = set(cluster.get("stage_ids", []))
            return [s for s in all_stages if s["stage_id"] in stage_ids]
    
    return []


def get_stages_by_district(district: str):
    """根据行政区获取舞台"""
    all_stages = get_shanghai_stages_200()
    return [s for s in all_stages if s.get("district") == district]


# 导出兼容旧代码的变量
SHANGHAI_STAGES_200 = None  # 延迟加载

def get_all_stages():
    """获取所有舞台（延迟加载）"""
    global SHANGHAI_STAGES_200
    if SHANGHAI_STAGES_200 is None:
        SHANGHAI_STAGES_200 = get_shanghai_stages_200()
    return SHANGHAI_STAGES_200


# 为了兼容性，提供一个15舞台的子集
def get_core_stages_15():
    """获取15个核心舞台（兼容旧测试）"""
    all_stages = get_all_stages()
    # 从每个主要区域选取代表性舞台
    core_clusters = ["psq", "njd", "bund", "yuyuan", "xintiandi", 
                     "huaihai", "tianzifang", "jingan", "lujiazui",
                     "xujiahui", "wukang", "centurypark", "fudan", 
                     "hongkou", "northbund"]
    
    core_stages = []
    for cluster_code in core_clusters:
        stages = get_stages_by_cluster_code(cluster_code)
        if stages:
            core_stages.append(stages[0])  # 每个簇取第一个
        if len(core_stages) >= 15:
            break
    
    return core_stages


if __name__ == "__main__":
    print("=== HP Shanghai 200 Stages Config ===")
    summary = get_summary()
    print(f"总舞台数: {summary['total_stages']}")
    print(f"区域簇数: {summary['total_clusters']}")
    
    print("\n=== 核心15舞台 ===")
    for s in get_core_stages_15():
        print(f"  {s['stage_id']}: {s['name']} ({s['district']})")
