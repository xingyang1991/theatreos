"""
TheatreOS Auth Middleware
FastAPI认证中间件，用于API请求的身份验证
"""

from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional, List
from functools import wraps

from .auth_service import get_auth_service, UserRole


# HTTP Bearer Token 安全方案
security = HTTPBearer(auto_error=False)


class AuthContext:
    """认证上下文，存储当前请求的用户信息"""
    
    def __init__(self, user_id: str = None, username: str = None, 
                 role: str = None, is_authenticated: bool = False):
        self.user_id = user_id
        self.username = username
        self.role = role
        self.is_authenticated = is_authenticated
    
    def __repr__(self):
        return f"AuthContext(user_id={self.user_id}, role={self.role}, authenticated={self.is_authenticated})"


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> AuthContext:
    """
    获取当前用户（可选认证）
    
    如果没有提供Token，返回未认证的AuthContext
    如果Token无效，返回未认证的AuthContext
    如果Token有效，返回包含用户信息的AuthContext
    """
    if not credentials:
        return AuthContext(is_authenticated=False)
    
    auth_service = get_auth_service()
    result = auth_service.verify_token(credentials.credentials)
    
    if not result.get("valid"):
        return AuthContext(is_authenticated=False)
    
    return AuthContext(
        user_id=result["user_id"],
        username=result["username"],
        role=result["role"],
        is_authenticated=True
    )


async def require_auth(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> AuthContext:
    """
    要求认证（必须登录）
    
    如果没有提供Token或Token无效，抛出401错误
    """
    if not credentials:
        raise HTTPException(
            status_code=401,
            detail="未提供认证Token",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    auth_service = get_auth_service()
    result = auth_service.verify_token(credentials.credentials)
    
    if not result.get("valid"):
        raise HTTPException(
            status_code=401,
            detail=result.get("error", "Token无效或已过期"),
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    return AuthContext(
        user_id=result["user_id"],
        username=result["username"],
        role=result["role"],
        is_authenticated=True
    )


def require_role(required_roles: List[UserRole]):
    """
    要求特定角色的装饰器工厂
    
    Usage:
        @app.get("/admin/users")
        async def list_users(auth: AuthContext = Depends(require_role([UserRole.ADMIN]))):
            ...
    """
    async def role_checker(
        credentials: HTTPAuthorizationCredentials = Depends(security)
    ) -> AuthContext:
        if not credentials:
            raise HTTPException(
                status_code=401,
                detail="未提供认证Token",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        auth_service = get_auth_service()
        
        # 验证Token
        result = auth_service.verify_token(credentials.credentials)
        if not result.get("valid"):
            raise HTTPException(
                status_code=401,
                detail=result.get("error", "Token无效或已过期"),
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        # 检查角色权限
        user_role = result["role"]
        role_hierarchy = {
            UserRole.GUEST.value: 0,
            UserRole.PLAYER.value: 1,
            UserRole.CREW_LEADER.value: 2,
            UserRole.MODERATOR.value: 3,
            UserRole.OPERATOR.value: 4,
            UserRole.ADMIN.value: 5
        }
        
        user_level = role_hierarchy.get(user_role, 0)
        required_level = min(role_hierarchy.get(r.value, 0) for r in required_roles)
        
        if user_level < required_level:
            raise HTTPException(
                status_code=403,
                detail=f"权限不足，需要以下角色之一: {[r.value for r in required_roles]}"
            )
        
        return AuthContext(
            user_id=result["user_id"],
            username=result["username"],
            role=result["role"],
            is_authenticated=True
        )
    
    return role_checker


# 预定义的角色检查器
require_player = require_role([UserRole.PLAYER, UserRole.CREW_LEADER, 
                               UserRole.MODERATOR, UserRole.OPERATOR, UserRole.ADMIN])
require_moderator = require_role([UserRole.MODERATOR, UserRole.OPERATOR, UserRole.ADMIN])
require_operator = require_role([UserRole.OPERATOR, UserRole.ADMIN])
require_admin = require_role([UserRole.ADMIN])


class AuthMiddleware:
    """
    认证中间件类
    
    可以作为FastAPI中间件使用，自动将用户信息注入到request.state
    """
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            # 从headers中提取Authorization
            headers = dict(scope.get("headers", []))
            auth_header = headers.get(b"authorization", b"").decode()
            
            if auth_header.startswith("Bearer "):
                token = auth_header[7:]
                auth_service = get_auth_service()
                result = auth_service.verify_token(token)
                
                if result.get("valid"):
                    # 将用户信息存入scope
                    scope["auth"] = AuthContext(
                        user_id=result["user_id"],
                        username=result["username"],
                        role=result["role"],
                        is_authenticated=True
                    )
                else:
                    scope["auth"] = AuthContext(is_authenticated=False)
            else:
                scope["auth"] = AuthContext(is_authenticated=False)
        
        await self.app(scope, receive, send)
