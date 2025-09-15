"""认证相关API路由"""

import secrets
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import and_
from sqlalchemy.orm import Session

from amazon_tracker.common.auth.jwt_auth import JWTBearer, jwt_auth
from amazon_tracker.common.auth.models import (
    AuthUser,
    ChangePasswordRequest,
    LoginRequest,
    LoginResponse,
    PasswordResetConfirm,
    PasswordResetRequest,
    RefreshTokenRequest,
    RegisterRequest,
    RegisterResponse,
    SessionInfo,
)
from amazon_tracker.common.database.base import get_db_session
from amazon_tracker.common.database.models import Tenant, User, UserSession, UserStatus

router = APIRouter()


def get_client_info(request: Request) -> dict:
    """获取客户端信息"""
    user_agent = request.headers.get("user-agent", "")

    # 简单的设备类型判断
    device_type = "web"
    if "Mobile" in user_agent or "Android" in user_agent or "iPhone" in user_agent:
        device_type = "mobile"
    elif (
        "Postman" in user_agent
        or "curl" in user_agent
        or "python-requests" in user_agent
    ):
        device_type = "api"

    return {
        "ip_address": request.client.host,
        "user_agent": user_agent,
        "device_type": device_type,
    }


@router.post("/register", response_model=RegisterResponse)
def register(
    request: RegisterRequest,
    client_request: Request,
    db: Session = Depends(get_db_session),
):
    """用户注册"""

    # 检查邮箱是否已存在
    existing_user = db.query(User).filter(User.email == request.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="邮箱已被注册"
        )

    # 创建租户（如果提供了公司名称）
    tenant = Tenant(name=request.company_name or f"{request.email}的组织")
    db.add(tenant)
    db.flush()  # 获取tenant_id

    # 创建用户
    user = User(
        email=request.email,
        username=request.username,
        full_name=request.full_name,
        tenant_id=tenant.tenant_id,
        status=UserStatus.PENDING_VERIFICATION,
    )
    user.set_password(request.password)

    # 生成邮箱验证令牌
    verification_token = user.generate_email_verification_token()

    db.add(user)
    db.commit()

    # TODO: 发送验证邮件
    # await send_verification_email(user.email, verification_token)

    return RegisterResponse(
        message="注册成功，请检查邮箱进行验证",
        user_id=user.id,
        tenant_id=tenant.tenant_id,
        verification_required=True,
    )


@router.post("/login", response_model=LoginResponse)
async def login(
    request: LoginRequest,
    client_request: Request,
    db: Session = Depends(get_db_session),
):
    """用户登录"""

    client_info = get_client_info(client_request)

    # 查找用户
    user = db.query(User).filter(User.email == request.email).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="邮箱或密码错误"
        )

    # 检查账户锁定
    if user.is_locked():
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED, detail="账户已被锁定，请稍后再试"
        )

    # 验证密码
    if not user.verify_password(request.password):
        # 增加失败次数
        user.failed_login_attempts += 1

        # 如果失败次数过多，锁定账户
        if user.failed_login_attempts >= 5:
            user.lock_account(30)  # 锁定30分钟
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail="登录失败次数过多，账户已被锁定30分钟",
            )

        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="邮箱或密码错误"
        )

    # 检查用户状态
    if user.status not in [UserStatus.ACTIVE, UserStatus.PENDING_VERIFICATION]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="账户已被禁用"
        )

    # 重置失败次数
    user.failed_login_attempts = 0
    user.unlock_account()

    # 更新登录信息
    user.last_login_at = datetime.utcnow()
    user.last_login_ip = client_info["ip_address"]
    user.login_count += 1

    # 创建用户会话
    session_expires = timedelta(days=7) if request.remember_me else timedelta(hours=24)
    session = UserSession(
        user_id=user.id,
        device_type=client_info["device_type"],
        user_agent=client_info["user_agent"],
        ip_address=client_info["ip_address"],
        expires_at=datetime.utcnow() + session_expires,
        jwt_jti=secrets.token_urlsafe(32),
    )

    db.add(session)
    db.flush()  # 获取session_id

    # 创建JWT令牌
    access_token_expires = timedelta(days=30)  # 访问令牌30天过期
    access_token = jwt_auth.create_access_token(
        user, str(session.session_id), access_token_expires
    )

    refresh_token = None
    if request.remember_me:
        refresh_token = jwt_auth.create_refresh_token(
            user, str(session.session_id), session_expires
        )
        session.refresh_token = refresh_token

    db.commit()

    # 构建用户信息
    auth_user = AuthUser(
        id=user.id,
        email=user.email,
        username=user.username,
        full_name=user.full_name,
        tenant_id=user.tenant_id,
        is_super_admin=user.is_super_admin,
        is_email_verified=user.is_email_verified,
        status=user.status.value,
        last_login_at=user.last_login_at,
        preferences=user.preferences or {},
    )

    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=int(access_token_expires.total_seconds()),
        user=auth_user,
    )


@router.post("/refresh", response_model=dict)
async def refresh_token(
    request: RefreshTokenRequest, db: Session = Depends(get_db_session)
):
    """刷新访问令牌"""

    new_access_token = jwt_auth.refresh_access_token(request.refresh_token)

    return {
        "access_token": new_access_token,
        "token_type": "bearer",
        "expires_in": jwt_auth.access_token_expire_minutes * 60,
    }


@router.post("/logout")
async def logout(
    credentials: HTTPAuthorizationCredentials = Depends(JWTBearer()),
    db: Session = Depends(get_db_session),
):
    """用户登出"""

    token_data = jwt_auth.verify_token(credentials.credentials)

    # 使会话失效
    session = (
        db.query(UserSession)
        .filter(
            UserSession.session_id == token_data.session_id,
            UserSession.is_active == True,
        )
        .first()
    )

    if session:
        session.invalidate()
        db.commit()

    # TODO: 将JWT令牌加入黑名单
    jwt_auth.invalidate_token(token_data.jti)

    return {"message": "登出成功"}


@router.post("/verify-email")
def verify_email(token: str, db: Session = Depends(get_db_session)):
    """验证邮箱"""

    user = (
        db.query(User)
        .filter(
            User.email_verification_token == token,
            User.email_verification_expires_at > datetime.utcnow(),
        )
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="验证链接无效或已过期"
        )

    # 激活用户
    user.is_email_verified = True
    user.status = UserStatus.ACTIVE
    user.email_verification_token = None
    user.email_verification_expires_at = None

    db.commit()

    return {"message": "邮箱验证成功"}


@router.post("/forgot-password")
async def forgot_password(
    request: PasswordResetRequest, db: Session = Depends(get_db_session)
):
    """忘记密码"""

    user = db.query(User).filter(User.email == request.email).first()

    # 即使用户不存在也返回成功，防止邮箱枚举攻击
    if user:
        reset_token = user.generate_password_reset_token()
        db.commit()

        # TODO: 发送密码重置邮件
        # await send_password_reset_email(user.email, reset_token)

    return {"message": "如果邮箱存在，将收到密码重置链接"}


@router.post("/reset-password")
async def reset_password(
    request: PasswordResetConfirm, db: Session = Depends(get_db_session)
):
    """重置密码"""

    user = (
        db.query(User)
        .filter(
            User.password_reset_token == request.token,
            User.password_reset_expires_at > datetime.utcnow(),
        )
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="重置链接无效或已过期"
        )

    # 设置新密码
    user.set_password(request.new_password)
    user.password_reset_token = None
    user.password_reset_expires_at = None

    # 使所有会话失效
    db.query(UserSession).filter(
        UserSession.user_id == user.id, UserSession.is_active == True
    ).update({"is_active": False})

    db.commit()

    return {"message": "密码重置成功，请重新登录"}


@router.post("/change-password")
async def change_password(
    request: ChangePasswordRequest,
    current_user: AuthUser = Depends(JWTBearer()),
    db: Session = Depends(get_db_session),
):
    """修改密码"""

    user = db.query(User).filter(User.id == current_user.id).first()

    if not user.verify_password(request.current_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="当前密码错误"
        )

    # 设置新密码
    user.set_password(request.new_password)

    # 使除当前会话外的所有会话失效
    db.query(UserSession).filter(
        and_(
            UserSession.user_id == user.id,
            UserSession.is_active == True,
            UserSession.session_id != current_user.session_id,
        )
    ).update({"is_active": False})

    db.commit()

    return {"message": "密码修改成功"}


@router.get("/sessions", response_model=list[SessionInfo])
async def get_user_sessions(
    current_user: AuthUser = Depends(JWTBearer()), db: Session = Depends(get_db_session)
):
    """获取用户会话列表"""

    sessions = (
        db.query(UserSession)
        .filter(UserSession.user_id == current_user.id, UserSession.is_active == True)
        .order_by(UserSession.last_activity_at.desc())
        .all()
    )

    return sessions


@router.delete("/sessions/{session_id}")
async def revoke_session(
    session_id: str,
    current_user: AuthUser = Depends(JWTBearer()),
    db: Session = Depends(get_db_session),
):
    """撤销指定会话"""

    session = (
        db.query(UserSession)
        .filter(
            UserSession.session_id == session_id,
            UserSession.user_id == current_user.id,
            UserSession.is_active == True,
        )
        .first()
    )

    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="会话不存在")

    session.invalidate()
    db.commit()

    return {"message": "会话已撤销"}
