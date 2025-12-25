"""
TheatreOS Data Pack API Routes
提供数据包查询和管理的API端点
"""
import sys
import os
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# 尝试导入数据包
try:
    from data_packs.hp_shanghai_200 import (
        get_stages, get_stage_meta, get_clusters, 
        get_tag_lexicon, get_summary, data_pack
    )
    DATA_PACK_AVAILABLE = True
except ImportError:
    DATA_PACK_AVAILABLE = False
    # 提供空实现
    def get_stages(): return []
    def get_stage_meta(): return []
    def get_clusters(): return []
    def get_tag_lexicon(): return {}
    def get_summary(): return {"total_stages": 0, "total_clusters": 0, "total_tags": 0}


router = APIRouter(prefix="/v1/datapacks", tags=["Data Packs"])


# =============================================================================
# Response Models
# =============================================================================

class StageBasic(BaseModel):
    stage_id: str
    name: str
    lat: float
    lng: float
    tags: List[str] = []
    safe_only: bool = True


class StageFull(StageBasic):
    ringc_m: int = 1200
    ringb_m: int = 500
    ringa_m: int = 80
    district: Optional[str] = None
    wizarding_zone: Optional[str] = None
    canon_ref: Optional[str] = None
    story_hook: Optional[str] = None
    npc_hint: Optional[str] = None
    recommended_threads: List[str] = []


class ClusterInfo(BaseModel):
    cluster_code: str
    district: str
    real_area: str
    wizarding_zone: str
    canon_ref: str
    center_lat: float
    center_lng: float
    base_tags: List[str] = []
    stage_ids: List[str] = []
    recommended_threads: List[str] = []


class DataPackSummary(BaseModel):
    pack_id: str = "hp_shanghai_200"
    version: str = "1.0.0"
    total_stages: int
    total_clusters: int
    total_tags: int
    districts: List[str] = []
    wizarding_zones: List[str] = []
    available: bool = True


class TagInfo(BaseModel):
    tag: str
    cn: str
    hp_mapping: str
    prompt_cues: List[str] = []
    camera_styles: List[str] = []
    moods: List[str] = []


# =============================================================================
# API Endpoints
# =============================================================================

@router.get("/hp_shanghai_200/summary", response_model=DataPackSummary)
async def get_datapack_summary():
    """获取HP上海200数据包摘要"""
    if not DATA_PACK_AVAILABLE:
        raise HTTPException(status_code=404, detail="Data pack not available")
    
    summary = get_summary()
    return DataPackSummary(
        total_stages=summary.get("total_stages", 0),
        total_clusters=summary.get("total_clusters", 0),
        total_tags=summary.get("total_tags", 0),
        districts=summary.get("districts", []),
        wizarding_zones=summary.get("wizarding_zones", []),
        available=DATA_PACK_AVAILABLE,
    )


@router.get("/hp_shanghai_200/stages", response_model=List[StageBasic])
async def list_stages(
    district: Optional[str] = Query(None, description="按行政区筛选"),
    cluster: Optional[str] = Query(None, description="按簇代码筛选"),
    limit: int = Query(50, ge=1, le=200, description="返回数量限制"),
    offset: int = Query(0, ge=0, description="偏移量"),
):
    """获取舞台列表"""
    if not DATA_PACK_AVAILABLE:
        raise HTTPException(status_code=404, detail="Data pack not available")
    
    stages = get_stages()
    meta_list = get_stage_meta()
    meta_dict = {m["stage_id"]: m for m in meta_list}
    
    # 筛选
    if district:
        stage_ids = {m["stage_id"] for m in meta_list if m.get("district") == district}
        stages = [s for s in stages if s["stage_id"] in stage_ids]
    
    if cluster:
        clusters = get_clusters()
        cluster_stage_ids = set()
        for c in clusters:
            if c["cluster_code"] == cluster:
                cluster_stage_ids = set(c.get("stage_ids", []))
                break
        stages = [s for s in stages if s["stage_id"] in cluster_stage_ids]
    
    # 分页
    total = len(stages)
    stages = stages[offset:offset + limit]
    
    return [StageBasic(**s) for s in stages]


@router.get("/hp_shanghai_200/stages/{stage_id}", response_model=StageFull)
async def get_stage_detail(stage_id: str):
    """获取舞台详情"""
    if not DATA_PACK_AVAILABLE:
        raise HTTPException(status_code=404, detail="Data pack not available")
    
    stages = get_stages()
    meta_list = get_stage_meta()
    
    stage = None
    for s in stages:
        if s["stage_id"] == stage_id:
            stage = s
            break
    
    if not stage:
        raise HTTPException(status_code=404, detail=f"Stage not found: {stage_id}")
    
    meta = None
    for m in meta_list:
        if m["stage_id"] == stage_id:
            meta = m
            break
    
    result = {**stage}
    if meta:
        result.update({
            "district": meta.get("district"),
            "wizarding_zone": meta.get("wizarding_zone"),
            "canon_ref": meta.get("canon_ref"),
            "story_hook": meta.get("story_hook"),
            "npc_hint": meta.get("npc_hint"),
            "recommended_threads": meta.get("recommended_threads", []),
        })
    
    return StageFull(**result)


@router.get("/hp_shanghai_200/clusters", response_model=List[ClusterInfo])
async def list_clusters():
    """获取所有区域簇"""
    if not DATA_PACK_AVAILABLE:
        raise HTTPException(status_code=404, detail="Data pack not available")
    
    clusters = get_clusters()
    return [ClusterInfo(**c) for c in clusters]


@router.get("/hp_shanghai_200/clusters/{cluster_code}", response_model=ClusterInfo)
async def get_cluster_detail(cluster_code: str):
    """获取簇详情"""
    if not DATA_PACK_AVAILABLE:
        raise HTTPException(status_code=404, detail="Data pack not available")
    
    clusters = get_clusters()
    for c in clusters:
        if c["cluster_code"] == cluster_code:
            return ClusterInfo(**c)
    
    raise HTTPException(status_code=404, detail=f"Cluster not found: {cluster_code}")


@router.get("/hp_shanghai_200/tags", response_model=List[TagInfo])
async def list_tags():
    """获取所有标签及其语义信息"""
    if not DATA_PACK_AVAILABLE:
        raise HTTPException(status_code=404, detail="Data pack not available")
    
    lexicon = get_tag_lexicon()
    result = []
    for tag, info in lexicon.items():
        result.append(TagInfo(
            tag=tag,
            cn=info.get("cn", ""),
            hp_mapping=info.get("hp_mapping", ""),
            prompt_cues=info.get("prompt_cues", []),
            camera_styles=info.get("camera_styles", []),
            moods=info.get("moods", []),
        ))
    return result


@router.get("/hp_shanghai_200/tags/{tag}", response_model=TagInfo)
async def get_tag_detail(tag: str):
    """获取标签详情"""
    if not DATA_PACK_AVAILABLE:
        raise HTTPException(status_code=404, detail="Data pack not available")
    
    lexicon = get_tag_lexicon()
    if tag not in lexicon:
        raise HTTPException(status_code=404, detail=f"Tag not found: {tag}")
    
    info = lexicon[tag]
    return TagInfo(
        tag=tag,
        cn=info.get("cn", ""),
        hp_mapping=info.get("hp_mapping", ""),
        prompt_cues=info.get("prompt_cues", []),
        camera_styles=info.get("camera_styles", []),
        moods=info.get("moods", []),
    )


@router.get("/hp_shanghai_200/districts")
async def list_districts():
    """获取所有行政区"""
    if not DATA_PACK_AVAILABLE:
        raise HTTPException(status_code=404, detail="Data pack not available")
    
    summary = get_summary()
    return {"districts": summary.get("districts", [])}


@router.get("/hp_shanghai_200/wizarding_zones")
async def list_wizarding_zones():
    """获取所有魔法区域"""
    if not DATA_PACK_AVAILABLE:
        raise HTTPException(status_code=404, detail="Data pack not available")
    
    summary = get_summary()
    return {"wizarding_zones": summary.get("wizarding_zones", [])}
