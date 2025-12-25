"""
TheatreOS Storage API Routes
对象存储API路由
"""

from typing import Optional
from fastapi import APIRouter, UploadFile, File, Form, Query, HTTPException
from fastapi.responses import Response

from storage.src.storage_service import (
    get_storage_service,
    StorageService,
    AssetType,
    StoredAsset
)

router = APIRouter(prefix="/v1/storage", tags=["Storage"])


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(..., description="要上传的文件"),
    asset_type: str = Form("other", description="资产类型"),
    theatre_id: Optional[str] = Form(None, description="关联的剧场ID")
):
    """
    上传文件
    
    支持的资产类型:
    - image: 图片
    - audio: 音频
    - video: 视频
    - document: 文档
    - evidence_card: 证物卡
    - scene_media: 场景媒体
    - user_avatar: 用户头像
    - ugc: 用户生成内容
    - other: 其他
    """
    storage = get_storage_service()
    
    try:
        asset_type_enum = AssetType(asset_type)
    except ValueError:
        asset_type_enum = AssetType.OTHER
    
    try:
        content = await file.read()
        asset = storage.upload(
            file_data=content,
            filename=file.filename,
            asset_type=asset_type_enum,
            theatre_id=theatre_id,
            metadata={
                "original_filename": file.filename,
                "content_type": file.content_type
            }
        )
        
        return {
            "status": "ok",
            "asset": asset.to_dict()
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.get("/assets/{asset_id}")
async def get_asset(asset_id: str):
    """获取资产信息"""
    storage = get_storage_service()
    asset = storage.get_asset(asset_id)
    
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    
    return {
        "status": "ok",
        "asset": asset.to_dict()
    }


@router.get("/assets/{asset_id}/download")
async def download_asset(asset_id: str):
    """下载资产文件"""
    storage = get_storage_service()
    asset = storage.get_asset(asset_id)
    
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    
    data = storage.download(asset_id)
    if not data:
        raise HTTPException(status_code=404, detail="File not found")
    
    return Response(
        content=data,
        media_type=asset.content_type,
        headers={
            "Content-Disposition": f'attachment; filename="{asset.filename}"'
        }
    )


@router.delete("/assets/{asset_id}")
async def delete_asset(asset_id: str):
    """删除资产"""
    storage = get_storage_service()
    
    if not storage.get_asset(asset_id):
        raise HTTPException(status_code=404, detail="Asset not found")
    
    success = storage.delete(asset_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete asset")
    
    return {"status": "ok", "message": "Asset deleted"}


@router.get("/assets")
async def list_assets(
    asset_type: Optional[str] = Query(None, description="资产类型过滤"),
    theatre_id: Optional[str] = Query(None, description="剧场ID过滤"),
    limit: int = Query(100, ge=1, le=1000, description="返回数量限制")
):
    """列出资产"""
    storage = get_storage_service()
    
    asset_type_enum = None
    if asset_type:
        try:
            asset_type_enum = AssetType(asset_type)
        except ValueError:
            pass
    
    assets = storage.list_assets(
        asset_type=asset_type_enum,
        theatre_id=theatre_id,
        limit=limit
    )
    
    return {
        "status": "ok",
        "count": len(assets),
        "assets": [a.to_dict() for a in assets]
    }


@router.get("/stats")
async def get_storage_stats():
    """获取存储统计信息"""
    storage = get_storage_service()
    return {
        "status": "ok",
        "stats": storage.get_stats()
    }
