"""
TheatreOS Auth Service
用户认证与授权服务，基于JWT实现
"""

import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from dataclasses import dataclass, field
from enum import Enum
import json
import base64
import hmac


class UserRole(Enum):
    """用户角色"""
    GUEST = "guest"           # 游客（未登录）
    PLAYER = "player"         # 普通玩家
    CREW_LEADER = "crew_leader"  # 剧团团长
    MODERATOR = "moderator"   # 版主/审核员
    OPERATOR = "operator"     # 运营人员
    ADMIN = "admin"           # 管理员


@dataclass
class User:
    """用户实体"""
    user_id: str
    username: str
    email: str
    password_hash: str
    salt: str
    role: UserRole = UserRole.PLAYER
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = None
    is_active: bool = True
    profile: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TokenPayload:
    """JWT Token载荷"""
    user_id: str
    username: str
    role: str
    exp: int  # 过期时间戳
    iat: int  # 签发时间戳
    jti: str  # Token唯一ID


class AuthService:
    """
    认证服务
    
    功能：
    1. 用户注册与密码加密
    2. 用户登录与Token签发
    3. Token验证与刷新
    4. 权限检查
    """
    
    def __init__(self, secret_key: str = None, token_expire_hours: int = 24):
        self.secret_key = secret_key or secrets.token_hex(32)
        self.token_expire_hours = token_expire_hours
        
        # 内存存储（后续会改为数据库）
        self.users: Dict[str, User] = {}
        self.users_by_email: Dict[str, str] = {}  # email -> user_id
        self.users_by_username: Dict[str, str] = {}  # username -> user_id
        self.revoked_tokens: set = set()  # 已撤销的Token JTI
        
        # 创建默认管理员账户
        self._create_default_admin()
    
    def _create_default_admin(self):
        """创建默认管理员账户"""
        admin_result = self.register(
            username="admin",
            email="admin@theatreos.local",
            password="admin123456",  # 生产环境需要修改
            role=UserRole.ADMIN
        )
        if admin_result["success"]:
            print(f"[Auth] Default admin created: {admin_result['user_id']}")
    
    def _hash_password(self, password: str, salt: str = None) -> tuple:
        """密码哈希"""
        if salt is None:
            salt = secrets.token_hex(16)
        password_hash = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            100000
        ).hex()
        return password_hash, salt
    
    def _verify_password(self, password: str, password_hash: str, salt: str) -> bool:
        """验证密码"""
        computed_hash, _ = self._hash_password(password, salt)
        return hmac.compare_digest(computed_hash, password_hash)
    
    def _generate_token(self, user: User) -> str:
        """生成JWT Token"""
        now = datetime.utcnow()
        exp = now + timedelta(hours=self.token_expire_hours)
        
        payload = TokenPayload(
            user_id=user.user_id,
            username=user.username,
            role=user.role.value,
            exp=int(exp.timestamp()),
            iat=int(now.timestamp()),
            jti=secrets.token_hex(16)
        )
        
        # 构建JWT (简化版，生产环境建议使用PyJWT库)
        header = {"alg": "HS256", "typ": "JWT"}
        header_b64 = base64.urlsafe_b64encode(
            json.dumps(header).encode()
        ).decode().rstrip('=')
        
        payload_dict = {
            "user_id": payload.user_id,
            "username": payload.username,
            "role": payload.role,
            "exp": payload.exp,
            "iat": payload.iat,
            "jti": payload.jti
        }
        payload_b64 = base64.urlsafe_b64encode(
            json.dumps(payload_dict).encode()
        ).decode().rstrip('=')
        
        # 签名
        message = f"{header_b64}.{payload_b64}"
        signature = hmac.new(
            self.secret_key.encode(),
            message.encode(),
            hashlib.sha256
        ).digest()
        signature_b64 = base64.urlsafe_b64encode(signature).decode().rstrip('=')
        
        return f"{header_b64}.{payload_b64}.{signature_b64}"
    
    def _decode_token(self, token: str) -> Optional[Dict[str, Any]]:
        """解码并验证JWT Token"""
        try:
            parts = token.split('.')
            if len(parts) != 3:
                return None
            
            header_b64, payload_b64, signature_b64 = parts
            
            # 验证签名
            message = f"{header_b64}.{payload_b64}"
            expected_signature = hmac.new(
                self.secret_key.encode(),
                message.encode(),
                hashlib.sha256
            ).digest()
            expected_signature_b64 = base64.urlsafe_b64encode(
                expected_signature
            ).decode().rstrip('=')
            
            if not hmac.compare_digest(signature_b64, expected_signature_b64):
                return None
            
            # 解码payload
            # 补齐padding
            padding = 4 - len(payload_b64) % 4
            if padding != 4:
                payload_b64 += '=' * padding
            
            payload = json.loads(base64.urlsafe_b64decode(payload_b64))
            
            # 检查是否过期
            if payload.get('exp', 0) < datetime.utcnow().timestamp():
                return None
            
            # 检查是否已撤销
            if payload.get('jti') in self.revoked_tokens:
                return None
            
            return payload
            
        except Exception as e:
            print(f"[Auth] Token decode error: {e}")
            return None
    
    # ==================== 公开API ====================
    
    def register(self, username: str, email: str, password: str, 
                 role: UserRole = UserRole.PLAYER) -> Dict[str, Any]:
        """
        用户注册
        
        Returns:
            {
                "success": bool,
                "user_id": str (if success),
                "error": str (if failed)
            }
        """
        # 验证用户名
        if len(username) < 3 or len(username) > 32:
            return {"success": False, "error": "用户名长度需要在3-32个字符之间"}
        
        if username in self.users_by_username:
            return {"success": False, "error": "用户名已存在"}
        
        # 验证邮箱
        if '@' not in email:
            return {"success": False, "error": "邮箱格式不正确"}
        
        if email in self.users_by_email:
            return {"success": False, "error": "邮箱已被注册"}
        
        # 验证密码
        if len(password) < 8:
            return {"success": False, "error": "密码长度至少8个字符"}
        
        # 创建用户
        user_id = f"user_{secrets.token_hex(8)}"
        password_hash, salt = self._hash_password(password)
        
        user = User(
            user_id=user_id,
            username=username,
            email=email,
            password_hash=password_hash,
            salt=salt,
            role=role
        )
        
        self.users[user_id] = user
        self.users_by_email[email] = user_id
        self.users_by_username[username] = user_id
        
        return {"success": True, "user_id": user_id}
    
    def login(self, username_or_email: str, password: str) -> Dict[str, Any]:
        """
        用户登录
        
        Returns:
            {
                "success": bool,
                "token": str (if success),
                "user": {...} (if success),
                "error": str (if failed)
            }
        """
        # 查找用户
        user_id = self.users_by_username.get(username_or_email) or \
                  self.users_by_email.get(username_or_email)
        
        if not user_id:
            return {"success": False, "error": "用户不存在"}
        
        user = self.users.get(user_id)
        if not user:
            return {"success": False, "error": "用户不存在"}
        
        if not user.is_active:
            return {"success": False, "error": "账户已被禁用"}
        
        # 验证密码
        if not self._verify_password(password, user.password_hash, user.salt):
            return {"success": False, "error": "密码错误"}
        
        # 更新最后登录时间
        user.last_login = datetime.utcnow()
        
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
    
    def verify_token(self, token: str) -> Dict[str, Any]:
        """
        验证Token
        
        Returns:
            {
                "valid": bool,
                "user_id": str (if valid),
                "username": str (if valid),
                "role": str (if valid),
                "error": str (if invalid)
            }
        """
        payload = self._decode_token(token)
        
        if not payload:
            return {"valid": False, "error": "Token无效或已过期"}
        
        return {
            "valid": True,
            "user_id": payload["user_id"],
            "username": payload["username"],
            "role": payload["role"]
        }
    
    def refresh_token(self, token: str) -> Dict[str, Any]:
        """
        刷新Token
        
        Returns:
            {
                "success": bool,
                "token": str (if success),
                "error": str (if failed)
            }
        """
        payload = self._decode_token(token)
        
        if not payload:
            return {"success": False, "error": "Token无效或已过期"}
        
        user = self.users.get(payload["user_id"])
        if not user:
            return {"success": False, "error": "用户不存在"}
        
        # 撤销旧Token
        self.revoked_tokens.add(payload["jti"])
        
        # 生成新Token
        new_token = self._generate_token(user)
        
        return {"success": True, "token": new_token}
    
    def logout(self, token: str) -> Dict[str, Any]:
        """
        登出（撤销Token）
        
        Returns:
            {"success": bool}
        """
        payload = self._decode_token(token)
        
        if payload:
            self.revoked_tokens.add(payload["jti"])
        
        return {"success": True}
    
    def check_permission(self, token: str, required_role: UserRole) -> Dict[str, Any]:
        """
        检查权限
        
        Returns:
            {
                "allowed": bool,
                "user_id": str (if allowed),
                "error": str (if not allowed)
            }
        """
        verify_result = self.verify_token(token)
        
        if not verify_result["valid"]:
            return {"allowed": False, "error": verify_result.get("error", "Token无效")}
        
        # 角色权限层级
        role_hierarchy = {
            UserRole.GUEST.value: 0,
            UserRole.PLAYER.value: 1,
            UserRole.CREW_LEADER.value: 2,
            UserRole.MODERATOR.value: 3,
            UserRole.OPERATOR.value: 4,
            UserRole.ADMIN.value: 5
        }
        
        user_role_level = role_hierarchy.get(verify_result["role"], 0)
        required_role_level = role_hierarchy.get(required_role.value, 0)
        
        if user_role_level < required_role_level:
            return {"allowed": False, "error": f"权限不足，需要 {required_role.value} 角色"}
        
        return {
            "allowed": True,
            "user_id": verify_result["user_id"],
            "username": verify_result["username"],
            "role": verify_result["role"]
        }
    
    def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """获取用户信息"""
        user = self.users.get(user_id)
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
            "profile": user.profile
        }
    
    def update_user_role(self, admin_token: str, target_user_id: str, 
                         new_role: UserRole) -> Dict[str, Any]:
        """
        更新用户角色（需要管理员权限）
        
        Returns:
            {
                "success": bool,
                "error": str (if failed)
            }
        """
        # 验证管理员权限
        perm_check = self.check_permission(admin_token, UserRole.ADMIN)
        if not perm_check["allowed"]:
            return {"success": False, "error": perm_check.get("error", "权限不足")}
        
        # 更新目标用户角色
        user = self.users.get(target_user_id)
        if not user:
            return {"success": False, "error": "目标用户不存在"}
        
        user.role = new_role
        return {"success": True}
    
    def deactivate_user(self, admin_token: str, target_user_id: str) -> Dict[str, Any]:
        """
        禁用用户（需要管理员权限）
        """
        perm_check = self.check_permission(admin_token, UserRole.ADMIN)
        if not perm_check["allowed"]:
            return {"success": False, "error": perm_check.get("error", "权限不足")}
        
        user = self.users.get(target_user_id)
        if not user:
            return {"success": False, "error": "目标用户不存在"}
        
        user.is_active = False
        return {"success": True}


# 全局单例
_auth_service_instance = None

def get_auth_service() -> AuthService:
    """获取Auth服务单例"""
    global _auth_service_instance
    if _auth_service_instance is None:
        # 从环境变量获取密钥，如果没有则使用默认值
        import os
        secret_key = os.environ.get('JWT_SECRET_KEY', 'theatreos_dev_secret_key_change_in_production')
        _auth_service_instance = AuthService(secret_key=secret_key)
    return _auth_service_instance
