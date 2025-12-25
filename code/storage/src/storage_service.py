"""
TheatreOS Object Storage Service
对象存储服务 - 支持本地存储和云存储（S3兼容）
"""

import os
import uuid
import hashlib
import mimetypes
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, BinaryIO, Union
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
import shutil

# 尝试导入boto3（AWS S3 SDK）
try:
    import boto3
    from botocore.exceptions import ClientError
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False
    boto3 = None


class StorageBackend(str, Enum):
    """存储后端类型"""
    LOCAL = "local"
    S3 = "s3"
    MINIO = "minio"


class AssetType(str, Enum):
    """资产类型"""
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    DOCUMENT = "document"
    EVIDENCE_CARD = "evidence_card"
    SCENE_MEDIA = "scene_media"
    USER_AVATAR = "user_avatar"
    UGC = "ugc"
    OTHER = "other"


@dataclass
class StorageConfig:
    """存储配置"""
    backend: StorageBackend = StorageBackend.LOCAL
    
    # 本地存储配置
    local_base_path: str = "/home/ubuntu/theatreos/storage/data"
    
    # S3/MinIO配置
    s3_bucket: str = ""
    s3_region: str = "us-east-1"
    s3_endpoint: Optional[str] = None  # MinIO需要指定endpoint
    s3_access_key: Optional[str] = None
    s3_secret_key: Optional[str] = None
    
    # CDN配置
    cdn_base_url: Optional[str] = None
    
    # 限制
    max_file_size_mb: int = 100
    allowed_extensions: List[str] = None
    
    @classmethod
    def from_env(cls) -> "StorageConfig":
        """从环境变量加载配置"""
        backend = os.environ.get("STORAGE_BACKEND", "local")
        
        return cls(
            backend=StorageBackend(backend),
            local_base_path=os.environ.get("STORAGE_LOCAL_PATH", "/home/ubuntu/theatreos/storage/data"),
            s3_bucket=os.environ.get("S3_BUCKET", ""),
            s3_region=os.environ.get("S3_REGION", "us-east-1"),
            s3_endpoint=os.environ.get("S3_ENDPOINT"),
            s3_access_key=os.environ.get("AWS_ACCESS_KEY_ID"),
            s3_secret_key=os.environ.get("AWS_SECRET_ACCESS_KEY"),
            cdn_base_url=os.environ.get("CDN_BASE_URL"),
            max_file_size_mb=int(os.environ.get("MAX_FILE_SIZE_MB", "100"))
        )


@dataclass
class StoredAsset:
    """存储的资产"""
    asset_id: str
    asset_type: AssetType
    filename: str
    content_type: str
    size_bytes: int
    storage_path: str
    public_url: str
    checksum: str
    metadata: Dict[str, Any]
    created_at: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "asset_id": self.asset_id,
            "asset_type": self.asset_type.value,
            "filename": self.filename,
            "content_type": self.content_type,
            "size_bytes": self.size_bytes,
            "public_url": self.public_url,
            "checksum": self.checksum,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat()
        }


class LocalStorageBackend:
    """本地文件存储后端"""
    
    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
    
    def _get_path(self, storage_path: str) -> Path:
        """获取完整路径"""
        return self.base_path / storage_path
    
    def upload(
        self,
        file_data: Union[bytes, BinaryIO],
        storage_path: str,
        content_type: str = None
    ) -> bool:
        """上传文件"""
        full_path = self._get_path(storage_path)
        full_path.parent.mkdir(parents=True, exist_ok=True)
        
        if isinstance(file_data, bytes):
            full_path.write_bytes(file_data)
        else:
            with open(full_path, 'wb') as f:
                shutil.copyfileobj(file_data, f)
        
        return True
    
    def download(self, storage_path: str) -> Optional[bytes]:
        """下载文件"""
        full_path = self._get_path(storage_path)
        if full_path.exists():
            return full_path.read_bytes()
        return None
    
    def delete(self, storage_path: str) -> bool:
        """删除文件"""
        full_path = self._get_path(storage_path)
        if full_path.exists():
            full_path.unlink()
            return True
        return False
    
    def exists(self, storage_path: str) -> bool:
        """检查文件是否存在"""
        return self._get_path(storage_path).exists()
    
    def get_url(self, storage_path: str, base_url: str = None) -> str:
        """获取访问URL"""
        if base_url:
            return f"{base_url.rstrip('/')}/storage/{storage_path}"
        return f"/storage/{storage_path}"
    
    def list_files(self, prefix: str = "") -> List[str]:
        """列出文件"""
        search_path = self._get_path(prefix)
        if not search_path.exists():
            return []
        
        files = []
        for path in search_path.rglob("*"):
            if path.is_file():
                files.append(str(path.relative_to(self.base_path)))
        return files


class S3StorageBackend:
    """S3/MinIO存储后端"""
    
    def __init__(self, config: StorageConfig):
        if not BOTO3_AVAILABLE:
            raise RuntimeError("boto3 is required for S3 storage backend")
        
        self.bucket = config.s3_bucket
        self.cdn_base_url = config.cdn_base_url
        
        # 创建S3客户端
        client_kwargs = {
            "region_name": config.s3_region
        }
        
        if config.s3_endpoint:
            client_kwargs["endpoint_url"] = config.s3_endpoint
        
        if config.s3_access_key and config.s3_secret_key:
            client_kwargs["aws_access_key_id"] = config.s3_access_key
            client_kwargs["aws_secret_access_key"] = config.s3_secret_key
        
        self.client = boto3.client("s3", **client_kwargs)
    
    def upload(
        self,
        file_data: Union[bytes, BinaryIO],
        storage_path: str,
        content_type: str = None
    ) -> bool:
        """上传文件到S3"""
        try:
            extra_args = {}
            if content_type:
                extra_args["ContentType"] = content_type
            
            if isinstance(file_data, bytes):
                self.client.put_object(
                    Bucket=self.bucket,
                    Key=storage_path,
                    Body=file_data,
                    **extra_args
                )
            else:
                self.client.upload_fileobj(
                    file_data,
                    self.bucket,
                    storage_path,
                    ExtraArgs=extra_args
                )
            return True
        except ClientError as e:
            print(f"S3 upload error: {e}")
            return False
    
    def download(self, storage_path: str) -> Optional[bytes]:
        """从S3下载文件"""
        try:
            response = self.client.get_object(Bucket=self.bucket, Key=storage_path)
            return response["Body"].read()
        except ClientError:
            return None
    
    def delete(self, storage_path: str) -> bool:
        """从S3删除文件"""
        try:
            self.client.delete_object(Bucket=self.bucket, Key=storage_path)
            return True
        except ClientError:
            return False
    
    def exists(self, storage_path: str) -> bool:
        """检查文件是否存在"""
        try:
            self.client.head_object(Bucket=self.bucket, Key=storage_path)
            return True
        except ClientError:
            return False
    
    def get_url(self, storage_path: str, expires_in: int = 3600) -> str:
        """获取预签名URL"""
        if self.cdn_base_url:
            return f"{self.cdn_base_url.rstrip('/')}/{storage_path}"
        
        return self.client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": storage_path},
            ExpiresIn=expires_in
        )
    
    def list_files(self, prefix: str = "") -> List[str]:
        """列出文件"""
        try:
            response = self.client.list_objects_v2(Bucket=self.bucket, Prefix=prefix)
            return [obj["Key"] for obj in response.get("Contents", [])]
        except ClientError:
            return []


class StorageService:
    """对象存储服务"""
    
    def __init__(self, config: StorageConfig = None):
        self.config = config or StorageConfig.from_env()
        
        # 初始化后端
        if self.config.backend == StorageBackend.LOCAL:
            self.backend = LocalStorageBackend(self.config.local_base_path)
        elif self.config.backend in (StorageBackend.S3, StorageBackend.MINIO):
            self.backend = S3StorageBackend(self.config)
        else:
            raise ValueError(f"Unsupported storage backend: {self.config.backend}")
        
        # 资产索引（内存缓存，生产环境应使用数据库）
        self._asset_index: Dict[str, StoredAsset] = {}
    
    def _generate_asset_id(self) -> str:
        """生成资产ID"""
        return f"asset_{uuid.uuid4().hex[:16]}"
    
    def _generate_storage_path(
        self,
        asset_type: AssetType,
        filename: str,
        theatre_id: str = None
    ) -> str:
        """生成存储路径"""
        # 按类型和日期组织目录
        date_prefix = datetime.utcnow().strftime("%Y/%m/%d")
        
        # 生成唯一文件名
        ext = Path(filename).suffix.lower()
        unique_name = f"{uuid.uuid4().hex[:12]}{ext}"
        
        if theatre_id:
            return f"{asset_type.value}/{theatre_id}/{date_prefix}/{unique_name}"
        return f"{asset_type.value}/{date_prefix}/{unique_name}"
    
    def _calculate_checksum(self, data: bytes) -> str:
        """计算文件校验和"""
        return hashlib.md5(data).hexdigest()
    
    def _detect_content_type(self, filename: str) -> str:
        """检测内容类型"""
        content_type, _ = mimetypes.guess_type(filename)
        return content_type or "application/octet-stream"
    
    def upload(
        self,
        file_data: Union[bytes, BinaryIO],
        filename: str,
        asset_type: AssetType = AssetType.OTHER,
        theatre_id: str = None,
        metadata: Dict[str, Any] = None
    ) -> StoredAsset:
        """上传文件"""
        # 读取数据
        if isinstance(file_data, bytes):
            data = file_data
        else:
            data = file_data.read()
        
        # 检查文件大小
        size_bytes = len(data)
        max_size = self.config.max_file_size_mb * 1024 * 1024
        if size_bytes > max_size:
            raise ValueError(f"File size exceeds limit: {size_bytes} > {max_size}")
        
        # 生成路径和ID
        asset_id = self._generate_asset_id()
        storage_path = self._generate_storage_path(asset_type, filename, theatre_id)
        content_type = self._detect_content_type(filename)
        checksum = self._calculate_checksum(data)
        
        # 上传
        success = self.backend.upload(data, storage_path, content_type)
        if not success:
            raise RuntimeError("Failed to upload file")
        
        # 获取URL
        if isinstance(self.backend, LocalStorageBackend):
            public_url = self.backend.get_url(storage_path, self.config.cdn_base_url)
        else:
            public_url = self.backend.get_url(storage_path)
        
        # 创建资产记录
        asset = StoredAsset(
            asset_id=asset_id,
            asset_type=asset_type,
            filename=filename,
            content_type=content_type,
            size_bytes=size_bytes,
            storage_path=storage_path,
            public_url=public_url,
            checksum=checksum,
            metadata=metadata or {},
            created_at=datetime.utcnow()
        )
        
        # 缓存索引
        self._asset_index[asset_id] = asset
        
        return asset
    
    def download(self, asset_id: str) -> Optional[bytes]:
        """下载文件"""
        asset = self._asset_index.get(asset_id)
        if not asset:
            return None
        return self.backend.download(asset.storage_path)
    
    def delete(self, asset_id: str) -> bool:
        """删除文件"""
        asset = self._asset_index.get(asset_id)
        if not asset:
            return False
        
        success = self.backend.delete(asset.storage_path)
        if success:
            del self._asset_index[asset_id]
        return success
    
    def get_asset(self, asset_id: str) -> Optional[StoredAsset]:
        """获取资产信息"""
        return self._asset_index.get(asset_id)
    
    def get_url(self, asset_id: str) -> Optional[str]:
        """获取资产URL"""
        asset = self._asset_index.get(asset_id)
        if asset:
            return asset.public_url
        return None
    
    def list_assets(
        self,
        asset_type: AssetType = None,
        theatre_id: str = None,
        limit: int = 100
    ) -> List[StoredAsset]:
        """列出资产"""
        assets = list(self._asset_index.values())
        
        if asset_type:
            assets = [a for a in assets if a.asset_type == asset_type]
        
        if theatre_id:
            assets = [a for a in assets if theatre_id in a.storage_path]
        
        # 按创建时间倒序
        assets.sort(key=lambda x: x.created_at, reverse=True)
        
        return assets[:limit]
    
    def get_stats(self) -> Dict[str, Any]:
        """获取存储统计"""
        assets = list(self._asset_index.values())
        
        total_size = sum(a.size_bytes for a in assets)
        by_type = {}
        for asset in assets:
            t = asset.asset_type.value
            if t not in by_type:
                by_type[t] = {"count": 0, "size_bytes": 0}
            by_type[t]["count"] += 1
            by_type[t]["size_bytes"] += asset.size_bytes
        
        return {
            "backend": self.config.backend.value,
            "total_assets": len(assets),
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / 1024 / 1024, 2),
            "by_type": by_type
        }


# 全局单例
_storage_service_instance = None

def get_storage_service() -> StorageService:
    """获取存储服务单例"""
    global _storage_service_instance
    if _storage_service_instance is None:
        _storage_service_instance = StorageService()
    return _storage_service_instance
