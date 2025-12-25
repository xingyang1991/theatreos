#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TheatreOS HP Shanghai 200 Nodes Data Pack Loader
提供数据包的加载和访问接口
"""
import json
from pathlib import Path
from typing import List, Dict, Any, Optional

# 数据包根目录
DATA_PACK_ROOT = Path(__file__).parent

class HPShanghai200DataPack:
    """HP上海200节点数据包加载器"""
    
    def __init__(self):
        self._stages: List[Dict] = []
        self._stage_meta: List[Dict] = []
        self._clusters: List[Dict] = []
        self._tag_lexicon: Dict[str, Dict] = {}
        self._loaded = False
    
    def load(self) -> None:
        """加载所有数据"""
        if self._loaded:
            return
        
        # 加载舞台数据
        stages_file = DATA_PACK_ROOT / "stages" / "shanghai_hp_stages_200.json"
        if stages_file.exists():
            self._stages = json.loads(stages_file.read_text(encoding="utf-8"))
        
        # 加载舞台元数据
        meta_file = DATA_PACK_ROOT / "stages" / "shanghai_hp_stage_meta_200.json"
        if meta_file.exists():
            self._stage_meta = json.loads(meta_file.read_text(encoding="utf-8"))
        
        # 加载区域簇
        clusters_file = DATA_PACK_ROOT / "lexicon" / "shanghai_hp_stage_clusters.json"
        if clusters_file.exists():
            self._clusters = json.loads(clusters_file.read_text(encoding="utf-8"))
        
        # 加载标签词典
        lexicon_file = DATA_PACK_ROOT / "lexicon" / "shanghai_hp_stage_tag_lexicon.json"
        if lexicon_file.exists():
            self._tag_lexicon = json.loads(lexicon_file.read_text(encoding="utf-8"))
        
        self._loaded = True
    
    @property
    def stages(self) -> List[Dict]:
        """获取所有舞台数据（200个）"""
        self.load()
        return self._stages
    
    @property
    def stage_meta(self) -> List[Dict]:
        """获取舞台元数据"""
        self.load()
        return self._stage_meta
    
    @property
    def clusters(self) -> List[Dict]:
        """获取区域簇（20个）"""
        self.load()
        return self._clusters
    
    @property
    def tag_lexicon(self) -> Dict[str, Dict]:
        """获取标签语义词典"""
        self.load()
        return self._tag_lexicon
    
    def get_stage_by_id(self, stage_id: str) -> Optional[Dict]:
        """根据ID获取舞台"""
        self.load()
        for stage in self._stages:
            if stage.get("stage_id") == stage_id:
                return stage
        return None
    
    def get_stage_meta_by_id(self, stage_id: str) -> Optional[Dict]:
        """根据ID获取舞台元数据"""
        self.load()
        for meta in self._stage_meta:
            if meta.get("stage_id") == stage_id:
                return meta
        return None
    
    def get_stages_by_cluster(self, cluster_code: str) -> List[Dict]:
        """根据簇代码获取舞台列表"""
        self.load()
        cluster = self.get_cluster_by_code(cluster_code)
        if not cluster:
            return []
        stage_ids = cluster.get("stage_ids", [])
        return [s for s in self._stages if s.get("stage_id") in stage_ids]
    
    def get_cluster_by_code(self, cluster_code: str) -> Optional[Dict]:
        """根据代码获取簇"""
        self.load()
        for cluster in self._clusters:
            if cluster.get("cluster_code") == cluster_code:
                return cluster
        return None
    
    def get_stages_by_district(self, district: str) -> List[Dict]:
        """根据行政区获取舞台"""
        self.load()
        stage_ids = set()
        for meta in self._stage_meta:
            if meta.get("district") == district:
                stage_ids.add(meta.get("stage_id"))
        return [s for s in self._stages if s.get("stage_id") in stage_ids]
    
    def get_tag_info(self, tag: str) -> Optional[Dict]:
        """获取标签的语义信息"""
        self.load()
        return self._tag_lexicon.get(tag)
    
    def get_all_districts(self) -> List[str]:
        """获取所有行政区"""
        self.load()
        districts = set()
        for meta in self._stage_meta:
            if meta.get("district"):
                districts.add(meta["district"])
        return sorted(list(districts))
    
    def get_all_wizarding_zones(self) -> List[str]:
        """获取所有魔法区域"""
        self.load()
        zones = set()
        for cluster in self._clusters:
            if cluster.get("wizarding_zone"):
                zones.add(cluster["wizarding_zone"])
        return sorted(list(zones))
    
    def summary(self) -> Dict[str, Any]:
        """获取数据包摘要"""
        self.load()
        return {
            "total_stages": len(self._stages),
            "total_clusters": len(self._clusters),
            "total_tags": len(self._tag_lexicon),
            "districts": self.get_all_districts(),
            "wizarding_zones": self.get_all_wizarding_zones(),
        }


# 单例实例
data_pack = HPShanghai200DataPack()


def get_stages() -> List[Dict]:
    """获取所有舞台"""
    return data_pack.stages


def get_stage_meta() -> List[Dict]:
    """获取所有舞台元数据"""
    return data_pack.stage_meta


def get_clusters() -> List[Dict]:
    """获取所有区域簇"""
    return data_pack.clusters


def get_tag_lexicon() -> Dict[str, Dict]:
    """获取标签词典"""
    return data_pack.tag_lexicon


def get_summary() -> Dict[str, Any]:
    """获取数据包摘要"""
    return data_pack.summary()


if __name__ == "__main__":
    # 测试加载
    print("=== HP Shanghai 200 Data Pack ===")
    summary = get_summary()
    print(f"舞台数量: {summary['total_stages']}")
    print(f"区域簇数量: {summary['total_clusters']}")
    print(f"标签数量: {summary['total_tags']}")
    print(f"行政区: {', '.join(summary['districts'])}")
    print(f"魔法区域: {', '.join(summary['wizarding_zones'])}")
