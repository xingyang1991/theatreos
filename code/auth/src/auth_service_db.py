"""
TheatreOS Auth Service (Database Version)
用户认证服务 - 数据库持久化版本
"""

import uuid
import hashlib
import hmac
import base64
import json
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from enum import Enum
from sqlalchemy.orm import Session

from kernel.src.models import UserModel, TokenBlacklistModel, UserRoleEnum


class UserRole(str, Enum):
    GUEST = "guest"
    PLAYER = "player"
    CREW_LEADER = "crew_leader"
    MODERATOR = "moderator"
    OPERATOR = "operator"
    ADMIN = "admin"


# 配置
AUTH_CONFIG = {
    "jwt_secret": os.environ.get("JWT_SECRET", "theatreos_secret_key_change_in_production"),
    "token_expire_hours": 24,
    "password_min_length": 8,
}


class AuthServiceDB:
    """用户认证服务（数据库版本）"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def _hash_password(self, password: str, salt: str) -> str:
        """哈希密码"""
        return hashlib.pbkdf2_hmac(
            'sha256',
            password.encode(),
            salt.encode(),
            100000
        ).hex()
    
    def _generate_salt(self) -> str:
        """生成盐值"""
        return uuid.uuid4().hex
    
    def _generate_token(self, user: UserModel) -> str:
        """生成JWT Token"""
        header = {"alg": "HS256", "typ": "JWT"}
        payload = {
            "user_id": user.user_id,
            "username": user.username,
            "role": user.role.value,
            "exp": int((datetime.utcnow() + timedelta(hours=AUTH_CONFIG["token_expire_hours"])).timestamp()),
            "iat": int(datetime.utcnow().timestamp()),
            "jti": uuid.uuid4().hex
        }
        
        header_b64 = base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip("=")
        payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
        
        signature = hmac.new(
            AUTH_CONFIG["jwt_secret"].encode(),
            f"{header_b64}.{payload_b64}".encode(),
            hashlib.sha256
        ).digest()
        signature_b64 = base64.urlsafe_b64encode(signature).decode().rstrip("=")
        
        return f"{header_b64}.{payload_b64}.{signature_b64}"
    
    def _verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """验证JWT Token"""
        try:
            parts = token.split(".")
            if len(parts) != 3:
                return None
            
            header_b64, payload_b64, signature_b64 = parts
            
            # 验证签名
            expected_signature = hmac.new(
                AUTH_CONFIG["jwt_secret"].encode(),
                f"{header_b64}.{payload_b64}".encode(),
                hashlib.sha256
            ).digest()
            expected_signature_b64 = base64.urlsafe_b64encode(expected_signature).decode().rstrip("=")
            
            if signature_b64 != expected_signature_b64:
                return None
            
            # 解码payload
            padding = 4 - len(payload_b64) % 4
            if padding != 4:
                payload_b64 += "=" * padding
            
            payload = json.loads(base64.urlsafe_b64decode(payload_b64))
            
            # 检查过期
            if payload.get("exp", 0) < datetime.utcnow().timestamp():
                return None
            
            # 检查黑名单
            jti = payload.get("jti")
            if jti:
                blacklisted = self.db.query(TokenBlacklistModel).filter(
                    TokenBlacklistModel.jti == jti
                ).first()
                if blacklisted:
                    return None
            
            return payload
            
        except Exception:
            return None
    
    def register(
        self,
        username: str,
        email: str,
        password: str,
        role: UserRole = UserRole.PLAYER
    ) -> Dict[str, Any]:
        """用户注册"""
        # 验证密码长度
        if len(password) < AUTH_CONFIG["password_min_length"]:
            return {"success": False, "error": f"Password must be at least {AUTH_CONFIG['password_min_length']} characters"}
        
        # 检查用户名是否已存在
        existing_username = self.db.query(UserModel).filter(
            UserModel.username == username
        ).first()
        if existing_username:
            return {"success": False, "error": "Username already exists"}
        
        # 检查邮箱是否已存在
        existing_email = self.db.query(UserModel).filter(
            UserModel.email == email
        ).first()
        if existing_email:
            return {"success": False, "error": "Email already exists"}
        
        # 创建用户
        user_id = f"user_{uuid.uuid4().hex[:16]}"
        salt = self._generate_salt()
        password_hash = self._hash_password(password, salt)
        
        user = UserModel(
            user_id=user_id,
            username=username,
            email=email,
            password_hash=password_hash,
            salt=salt,
            role=UserRoleEnum(role.value),
            created_at=datetime.utcnow(),
            is_active=True,
            profile={}
        )
        
        self.db.add(user)
        self.db.commit()
        
        return {"success": True, "user_id": user_id}
    
    def login(self, username_or_email: str, password: str) -> Dict[str, Any]:
        """用户登录"""
        # 查找用户
        user = self.db.query(UserModel).filter(
            (UserModel.username == username_or_email) | (UserModel.email == username_or_email)
        ).first()
        
        if not user:
            return {"success": False, "error": "User not found"}
        
        if not user.is_active:
            return {"success": False, "error": "Account is disabled"}
        
        # 验证密码
        password_hash = self._hash_password(password, user.salt)
        if password_hash != user.password_hash:
            return {"success": False, "error": "Invalid password"}
        
        # 更新最后登录时间
        user.last_login = datetime.utcnow()
        self.db.commit()
        
        # 生成Token
        token = self._generate_token(user)
        
        return {
            "success": True,
            "token": token,
            "user": {
                "user_id": user.user_id,
                "username": user.username,
                "email": user.email,
                "role": user.role.value
            }
        }
    
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """验证Token"""
        return self._verify_token(token)
    
    def revoke_token(self, token: str) -> bool:
        """撤销Token"""
        payload = self._verify_token(token)
        if not payload:
            return False
        
        jti = payload.get("jti")
        exp = payload.get("exp")
        
        if not jti or not exp:
            return False
        
        # 添加到黑名单
        blacklist_entry = TokenBlacklistModel(
            jti=jti,
            revoked_at=datetime.utcnow(),
            expires_at=datetime.fromtimestamp(exp)
        )
        
        self.db.add(blacklist_entry)
        self.db.commit()
        
        return True
    
    def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """获取用户信息"""
        user = self.db.query(UserModel).filter(
            UserModel.user_id == user_id
        ).first()
        
        if not user:
            return None
        
        return {
            "user_id": user.user_id,
            "username": user.username,
            "email": user.email,
            "role": user.role.value,
            "created_at": user.created_at.isoformat(),
            "last_login": user.last_login.isoformat() if user.last_login else None,
            "is_active": user.is_active,
            "profile": user.profile or {}
        }
    
    def update_role(self, user_id: str, new_role: UserRole, admin_token: str) -> Dict[str, Any]:
        """更新用户角色（需要管理员权限）"""
        # 验证管理员Token
        admin_payload = self._verify_token(admin_token)
        if not admin_payload or admin_payload.get("role") != UserRole.ADMIN.value:
            return {"success": False, "error": "Admin permission required"}
        
        user = self.db.query(UserModel).filter(
            UserModel.user_id == user_id
        ).first()
        
        if not user:
            return {"success": False, "error": "User not found"}
        
        user.role = UserRoleEnum(new_role.value)
        self.db.commit()
        
        return {"success": True, "user_id": user_id, "new_role": new_role.value}
    
    def deactivate_user(self, user_id: str, admin_token: str) -> Dict[str, Any]:
        """禁用用户（需要管理员权限）"""
        # 验证管理员Token
        admin_payload = self._verify_token(admin_token)
        if not admin_payload or admin_payload.get("role") != UserRole.ADMIN.value:
            return {"success": False, "error": "Admin permission required"}
        
        user = self.db.query(UserModel).filter(
            UserModel.user_id == user_id
        ).first()
        
        if not user:
            return {"success": False, "error": "User not found"}
        
        user.is_active = False
        self.db.commit()
        
        return {"success": True, "user_id": user_id, "message": "User deactivated"}
    
    def cleanup_expired_tokens(self) -> int:
        """清理过期的Token黑名单记录"""
        deleted = self.db.query(TokenBlacklistModel).filter(
            TokenBlacklistModel.expires_at < datetime.utcnow()
        ).delete()
        self.db.commit()
        return deleted


# 全局单例（用于兼容现有代码）
_auth_service_db_instance = None

def get_auth_service_db(db: Session) -> AuthServiceDB:
    """获取Auth服务实例"""
    return AuthServiceDB(db)
