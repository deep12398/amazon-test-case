"""爬虫任务管理API端点"""

from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from amazon_tracker.common.auth.jwt_auth import verify_token, get_current_user
from amazon_tracker.common.task_queue.crawler_tasks import crawl_products_batch
from amazon_tracker.common.task_queue.monitoring_tasks import scan_all_product_anomalies

router = APIRouter(prefix="/tasks", tags=["tasks"])
security = HTTPBearer()


@router.post("/manual/batch-crawl")
async def trigger_manual_batch_crawl(
    authorization: HTTPAuthorizationCredentials = Depends(security)
):
    """手动触发批量产品抓取任务"""

    # JWT认证
    if not authorization or authorization.scheme != "Bearer":
        raise HTTPException(status_code=401, detail="Invalid authentication")

    token_data = verify_token(authorization.credentials)
    if not token_data:
        raise HTTPException(status_code=401, detail="Invalid token")

    current_user_data = get_current_user(token_data)
    if not current_user_data:
        raise HTTPException(status_code=401, detail="User not found")

    try:
        print(f"异步执行批量爬取任务 (租户: {current_user_data.tenant_id})")

        # 传递租户ID给批量爬取任务
        result = crawl_products_batch.apply(args=[current_user_data.tenant_id])
        print(result.get())  # 获取返回值

        return {
            "success": True,
            "message": "Batch crawl task triggered successfully",
            "tenant_id": current_user_data.tenant_id,
            "task_id": 123,
            "status": "started"
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to trigger batch crawl task: {str(e)}"
        )

@router.post("/manual/monitoring")
async def trigger_manual_monitoring(
    authorization: HTTPAuthorizationCredentials = Depends(security)
):
    """手动触发监控任务"""

    # JWT认证
    if not authorization or authorization.scheme != "Bearer":
        raise HTTPException(status_code=401, detail="Invalid authentication")

    token_data = verify_token(authorization.credentials)
    if not token_data:
        raise HTTPException(status_code=401, detail="Invalid token")

    current_user_data = get_current_user(token_data)
    if not current_user_data:
        raise HTTPException(status_code=401, detail="User not found")

    try:
        print(f"异步执行监控任务 (租户: {current_user_data.tenant_id})")

        # 传递租户ID给监控任务
        result = scan_all_product_anomalies.apply(args=[current_user_data.tenant_id])
        print(result.get())  # 获取返回值

        return {
            "success": True,
            "message": "monitoring task triggered successfully",
            "tenant_id": current_user_data.tenant_id,
            "task_id": 456,
            "status": "started"
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to trigger monitoring task: {str(e)}"
        )