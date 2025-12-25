"""
TheatreOS Theme Pack API Routes
主题包API路由 - 提供主题包管理的REST API接口
"""

from fastapi import APIRouter, HTTPException, Path, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

from .manager import get_theme_pack_manager

router = APIRouter(tags=["Theme Packs"])


# =============================================================================
# Request/Response Models
# =============================================================================

class ThemePackInfo(BaseModel):
    """主题包信息"""
    pack_id: str
    name: str
    version: str
    description: str
    season_id: str
    city: str
    stats: Dict[str, int]


class ThemePackListResponse(BaseModel):
    """主题包列表响应"""
    packs: List[Dict]
    total: int


class BindTheatreRequest(BaseModel):
    """绑定剧场请求"""
    theatre_id: str = Field(..., description="剧场ID")
    pack_id: Optional[str] = Field(None, description="主题包ID，为空时使用默认主题包")


class SwitchPackRequest(BaseModel):
    """切换主题包请求"""
    new_pack_id: str = Field(..., description="新主题包ID")


class ValidationResult(BaseModel):
    """验证结果"""
    valid: bool
    pack_id: str
    errors: List[str]
    warnings: List[str]
    stats: Dict[str, int]


# =============================================================================
# API Routes - 主题包管理
# =============================================================================

@router.get("", response_model=ThemePackListResponse)
async def list_theme_packs():
    """
    列出所有可用的主题包
    """
    manager = get_theme_pack_manager()
    packs = manager.list_available_packs()
    return ThemePackListResponse(packs=packs, total=len(packs))


@router.get("/{pack_id}")
async def get_theme_pack(
    pack_id: str = Path(..., description="主题包ID")
):
    """
    获取主题包详细信息
    """
    manager = get_theme_pack_manager()
    try:
        pack = manager.load_pack(pack_id)
        return pack.to_dict()
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Theme pack not found: {pack_id}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{pack_id}/validate", response_model=ValidationResult)
async def validate_theme_pack(
    pack_id: str = Path(..., description="主题包ID")
):
    """
    验证主题包完整性
    """
    manager = get_theme_pack_manager()
    result = manager.validate_pack(pack_id)
    return ValidationResult(**result)


@router.post("/reload/{pack_id}")
async def reload_theme_pack(
    pack_id: str = Path(..., description="主题包ID")
):
    """
    重新加载主题包（清除缓存并重新加载）
    """
    manager = get_theme_pack_manager()
    try:
        pack = manager.load_pack(pack_id, force_reload=True)
        return {
            "success": True,
            "pack_id": pack_id,
            "version": pack.metadata.version,
            "message": "Theme pack reloaded successfully"
        }
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Theme pack not found: {pack_id}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# API Routes - 剧场绑定
# =============================================================================

@router.post("/bind")
async def bind_theatre_to_pack(request: BindTheatreRequest):
    """
    为剧场绑定主题包
    """
    manager = get_theme_pack_manager()
    try:
        pack = manager.bind_theatre(request.theatre_id, request.pack_id)
        return {
            "success": True,
            "theatre_id": request.theatre_id,
            "pack_id": pack.metadata.pack_id,
            "pack_name": pack.metadata.name,
            "pack_version": pack.metadata.version
        }
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Theme pack not found: {request.pack_id}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/theatres/{theatre_id}/switch")
async def switch_theatre_pack(
    theatre_id: str = Path(..., description="剧场ID"),
    request: SwitchPackRequest = None
):
    """
    切换剧场的主题包
    """
    manager = get_theme_pack_manager()
    try:
        pack = manager.switch_theatre_pack(theatre_id, request.new_pack_id)
        return {
            "success": True,
            "theatre_id": theatre_id,
            "new_pack_id": pack.metadata.pack_id,
            "new_pack_name": pack.metadata.name,
            "new_pack_version": pack.metadata.version,
            "message": "Theme pack switched successfully"
        }
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Theme pack not found: {request.new_pack_id}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/theatres/{theatre_id}/pack")
async def get_theatre_pack(
    theatre_id: str = Path(..., description="剧场ID")
):
    """
    获取剧场当前绑定的主题包
    """
    manager = get_theme_pack_manager()
    try:
        pack = manager.get_theatre_pack(theatre_id)
        return {
            "theatre_id": theatre_id,
            "pack_id": pack.metadata.pack_id,
            "pack_name": pack.metadata.name,
            "pack_version": pack.metadata.version,
            "stats": manager.get_pack_stats(theatre_id)["stats"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# API Routes - 内容查询
# =============================================================================

@router.get("/theatres/{theatre_id}/characters")
async def list_theatre_characters(
    theatre_id: str = Path(..., description="剧场ID"),
    faction: Optional[str] = Query(None, description="按阵营筛选")
):
    """
    列出剧场主题包中的所有角色
    """
    manager = get_theme_pack_manager()
    try:
        if faction:
            characters = manager.get_characters_by_faction(theatre_id, faction)
            return {"characters": [c.to_dict() for c in characters], "total": len(characters)}
        else:
            characters = manager.list_characters(theatre_id)
            return {"characters": characters, "total": len(characters)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/theatres/{theatre_id}/characters/{character_id}")
async def get_theatre_character(
    theatre_id: str = Path(..., description="剧场ID"),
    character_id: str = Path(..., description="角色ID")
):
    """
    获取角色详细信息
    """
    manager = get_theme_pack_manager()
    character = manager.get_character(theatre_id, character_id)
    if not character:
        raise HTTPException(status_code=404, detail=f"Character not found: {character_id}")
    return character.to_dict()


@router.get("/theatres/{theatre_id}/threads")
async def list_theatre_threads(
    theatre_id: str = Path(..., description="剧场ID")
):
    """
    列出剧场主题包中的所有故事线
    """
    manager = get_theme_pack_manager()
    threads = manager.list_threads(theatre_id)
    return {"threads": threads, "total": len(threads)}


@router.get("/theatres/{theatre_id}/threads/{thread_id}")
async def get_theatre_thread(
    theatre_id: str = Path(..., description="剧场ID"),
    thread_id: str = Path(..., description="故事线ID")
):
    """
    获取故事线详细信息
    """
    manager = get_theme_pack_manager()
    thread = manager.get_thread(theatre_id, thread_id)
    if not thread:
        raise HTTPException(status_code=404, detail=f"Thread not found: {thread_id}")
    return thread.to_dict()


@router.get("/theatres/{theatre_id}/beats")
async def list_theatre_beats(
    theatre_id: str = Path(..., description="剧场ID"),
    thread_id: Optional[str] = Query(None, description="按故事线筛选"),
    beat_type: Optional[str] = Query(None, description="按拍子类型筛选")
):
    """
    列出剧场主题包中的所有拍子模板
    """
    manager = get_theme_pack_manager()
    
    if thread_id:
        beats = manager.get_beats_by_thread(theatre_id, thread_id)
        return {"beats": [b.to_dict() for b in beats], "total": len(beats)}
    elif beat_type:
        beats = manager.get_beats_by_type(theatre_id, beat_type)
        return {"beats": [b.to_dict() for b in beats], "total": len(beats)}
    else:
        beats = manager.list_beat_templates(theatre_id)
        return {"beats": beats, "total": len(beats)}


@router.get("/theatres/{theatre_id}/gates")
async def list_theatre_gates(
    theatre_id: str = Path(..., description="剧场ID")
):
    """
    列出剧场主题包中的所有门模板
    """
    manager = get_theme_pack_manager()
    gates = manager.list_gate_templates(theatre_id)
    return {"gates": gates, "total": len(gates)}


@router.get("/theatres/{theatre_id}/evidence-types")
async def list_theatre_evidence_types(
    theatre_id: str = Path(..., description="剧场ID")
):
    """
    列出剧场主题包中的所有证物类型
    """
    manager = get_theme_pack_manager()
    evidence_types = manager.list_evidence_types(theatre_id)
    return {"evidence_types": evidence_types, "total": len(evidence_types)}


@router.get("/theatres/{theatre_id}/world-variables")
async def list_theatre_world_variables(
    theatre_id: str = Path(..., description="剧场ID")
):
    """
    列出剧场主题包中的所有世界变量
    """
    manager = get_theme_pack_manager()
    variables = manager.list_world_variables(theatre_id)
    return {"world_variables": variables, "total": len(variables)}


@router.get("/theatres/{theatre_id}/world-variables/defaults")
async def get_theatre_default_world_state(
    theatre_id: str = Path(..., description="剧场ID")
):
    """
    获取剧场主题包的默认世界状态
    """
    manager = get_theme_pack_manager()
    defaults = manager.get_default_world_state(theatre_id)
    return {"defaults": defaults}


@router.get("/theatres/{theatre_id}/objects")
async def list_theatre_objects(
    theatre_id: str = Path(..., description="剧场ID")
):
    """
    列出剧场主题包中的所有关键物品
    """
    manager = get_theme_pack_manager()
    objects = manager.list_key_objects(theatre_id)
    return {"objects": objects, "total": len(objects)}


@router.get("/theatres/{theatre_id}/factions")
async def list_theatre_factions(
    theatre_id: str = Path(..., description="剧场ID")
):
    """
    列出剧场主题包中的所有阵营
    """
    manager = get_theme_pack_manager()
    factions = manager.list_factions(theatre_id)
    return {"factions": factions, "total": len(factions)}


@router.get("/theatres/{theatre_id}/rescue-beats")
async def list_theatre_rescue_beats(
    theatre_id: str = Path(..., description="剧场ID")
):
    """
    列出剧场主题包中的所有救援拍子
    """
    manager = get_theme_pack_manager()
    rescue_beats = manager.get_rescue_beats(theatre_id)
    return {"rescue_beats": [b.to_dict() for b in rescue_beats], "total": len(rescue_beats)}


@router.get("/theatres/{theatre_id}/stats")
async def get_theatre_pack_stats(
    theatre_id: str = Path(..., description="剧场ID")
):
    """
    获取剧场主题包的统计信息
    """
    manager = get_theme_pack_manager()
    return manager.get_pack_stats(theatre_id)
