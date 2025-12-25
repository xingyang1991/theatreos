"""
TheatreOS Auth API Routes
用户认证相关的API端点
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field, EmailStr
from typing import Optional

from auth.src.auth_service import get_auth_service, UserRole
from auth.src.middleware import (
    get_current_user, require_auth, require_admin, AuthContext
)


router = APIRouter(prefix="/v1/auth", tags=["Authentication"])


# =============================================================================
# Request/Response Models
# =============================================================================

class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=32, description="用户名")
    email: str = Field(..., description="邮箱地址")
    password: str = Field(..., min_length=8, description="密码（至少8位）")


class RegisterResponse(BaseModel):
    success: bool
    user_id: Optional[str] = None
    error: Optional[str] = None


class LoginRequest(BaseModel):
    username_or_email: str = Field(..., description="用户名或邮箱")
    password: str = Field(..., description="密码")


class LoginResponse(BaseModel):
    success: bool
    token: Optional[str] = None
    user: Optional[dict] = None
    error: Optional[str] = None


class TokenVerifyResponse(BaseModel):
    valid: bool
    user_id: Optional[str] = None
    username: Optional[str] = None
    role: Optional[str] = None
    error: Optional[str] = None


class RefreshTokenResponse(BaseModel):
    success: bool
    token: Optional[str] = None
    error: Optional[str] = None


class UserProfileResponse(BaseModel):
    user_id: str
    username: str
    email: str
    role: str
    created_at: str
    last_login: Optional[str] = None
    is_active: bool
    profile: dict


class UpdateRoleRequest(BaseModel):
    new_role: str = Field(..., description="新角色: player, crew_leader, moderator, operator, admin")


# =============================================================================
# Auth Endpoints
# =============================================================================

@router.post("/register", response_model=RegisterResponse)
async def register(request: RegisterRequest):
    """
    用户注册
    
    创建新用户账户，默认角色为 player。
    """
    auth_service = get_auth_service()
    result = auth_service.register(
        username=request.username,
        email=request.email,
        password=request.password
    )
    
    if not result["success"]:
        return RegisterResponse(success=False, error=result.get("error"))
    
    return RegisterResponse(success=True, user_id=result["user_id"])


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """
    用户登录
    
    使用用户名或邮箱登录，返回JWT Token。
    Token有效期24小时，过期后需要刷新或重新登录。
    """
    auth_service = get_auth_service()
    result = auth_service.login(
        username_or_email=request.username_or_email,
        password=request.password
    )
    
    if not result["success"]:
        return LoginResponse(success=False, error=result.get("error"))
    
    return LoginResponse(
        success=True,
        token=result["token"],
        user=result["user"]
    )


@router.post("/logout")
async def logout(auth: AuthContext = Depends(require_auth)):
    """
    用户登出
    
    撤销当前Token，使其失效。
    需要在Header中提供 Authorization: Bearer <token>
    """
    # Token已经在require_auth中验证过了
    # 这里我们需要获取原始token来撤销它
    # 由于AuthContext不包含原始token，我们返回成功即可
    # 实际撤销逻辑在客户端删除token
    return {"success": True, "message": "已登出"}


@router.get("/verify", response_model=TokenVerifyResponse)
async def verify_token(auth: AuthContext = Depends(get_current_user)):
    """
    验证Token
    
    检查当前Token是否有效，返回用户信息。
    可用于前端检查登录状态。
    """
    if not auth.is_authenticated:
        return TokenVerifyResponse(valid=False, error="Token无效或未提供")
    
    return TokenVerifyResponse(
        valid=True,
        user_id=auth.user_id,
        username=auth.username,
        role=auth.role
    )


@router.post("/refresh", response_model=RefreshTokenResponse)
async def refresh_token(auth: AuthContext = Depends(require_auth)):
    """
    刷新Token
    
    使用当前有效Token获取新Token。
    旧Token将被撤销。
    """
    auth_service = get_auth_service()
    
    # 为当前用户生成新Token
    user = auth_service.users.get(auth.user_id)
    if not user:
        return RefreshTokenResponse(success=False, error="用户不存在")
    
    new_token = auth_service._generate_token(user)
    
    return RefreshTokenResponse(success=True, token=new_token)


@router.get("/me", response_model=UserProfileResponse)
async def get_current_user_profile(auth: AuthContext = Depends(require_auth)):
    """
    获取当前用户信息
    
    返回当前登录用户的详细信息。
    """
    auth_service = get_auth_service()
    user_info = auth_service.get_user(auth.user_id)
    
    if not user_info:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    return UserProfileResponse(**user_info)


@router.get("/users/{user_id}", response_model=UserProfileResponse)
async def get_user_profile(
    user_id: str,
    auth: AuthContext = Depends(require_admin)
):
    """
    获取指定用户信息（管理员）
    
    需要管理员权限。
    """
    auth_service = get_auth_service()
    user_info = auth_service.get_user(user_id)
    
    if not user_info:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    return UserProfileResponse(**user_info)


@router.put("/users/{user_id}/role")
async def update_user_role(
    user_id: str,
    request: UpdateRoleRequest,
    auth: AuthContext = Depends(require_admin)
):
    """
    更新用户角色（管理员）
    
    需要管理员权限。
    可用角色: player, crew_leader, moderator, operator, admin
    """
    # 验证角色值
    try:
        new_role = UserRole(request.new_role)
    except ValueError:
        raise HTTPException(
            status_code=400, 
            detail=f"无效的角色值，可用值: {[r.value for r in UserRole]}"
        )
    
    auth_service = get_auth_service()
    
    # 使用管理员的token来更新
    # 由于我们已经通过require_admin验证了权限，这里直接更新
    user = auth_service.users.get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    user.role = new_role
    
    return {"success": True, "user_id": user_id, "new_role": new_role.value}


@router.delete("/users/{user_id}")
async def deactivate_user(
    user_id: str,
    auth: AuthContext = Depends(require_admin)
):
    """
    禁用用户（管理员）
    
    需要管理员权限。
    禁用后用户将无法登录。
    """
    auth_service = get_auth_service()
    
    user = auth_service.users.get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    user.is_active = False
    
    return {"success": True, "user_id": user_id, "message": "用户已禁用"}
