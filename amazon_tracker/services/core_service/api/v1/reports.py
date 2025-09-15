"""报告生成API端点"""

import os
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from fastapi.responses import FileResponse, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from amazon_tracker.common.analytics.report_generator import ReportGenerator
from amazon_tracker.common.auth.jwt_auth import verify_token, get_current_user
from amazon_tracker.common.auth.permissions import PermissionScope, require_permission
from amazon_tracker.common.database.connection import get_db_session
from amazon_tracker.common.database.base import get_db_session as get_direct_db_session
from amazon_tracker.common.database.models.product import Product

from .schemas import ReportGenerateRequest, ReportResponse

router = APIRouter(prefix="/reports", tags=["reports"])
security = HTTPBearer()

# 报告存储
report_store = {}  # 在实际应用中应该使用数据库或文件存储


@router.post("/generate", response_model=ReportResponse)
async def generate_report(
    request: ReportGenerateRequest,
    background_tasks: BackgroundTasks,
    authorization: HTTPAuthorizationCredentials = Depends(HTTPBearer()),
):
    """生成报告"""

    # JWT认证
    if not authorization or authorization.scheme != "Bearer":
        raise HTTPException(status_code=401, detail="Invalid authentication")

    token_data = verify_token(authorization.credentials)
    if not token_data:
        raise HTTPException(status_code=401, detail="Invalid token")

    current_user_data = get_current_user(token_data)
    if not current_user_data:
        raise HTTPException(status_code=401, detail="User not found")

    # 权限检查
    # require_permission(current_user, PermissionScope.REPORT_CREATE)

    try:
        # 获取数据库会话
        db = get_direct_db_session()

        try:
            # 获取指定的主产品
            main_product = (
                db.query(Product)
                .filter(
                    Product.tenant_id == current_user_data.tenant_id,
                    Product.id == request.main_product_id
                )
                .first()
            )

            if not main_product:
                raise HTTPException(status_code=404, detail=f"Main product with ID {request.main_product_id} not found")

            # 获取竞品产品
            if request.competitor_product_ids:
                # 使用指定的竞品产品IDs
                competitor_products = (
                    db.query(Product)
                    .filter(
                        Product.tenant_id == current_user_data.tenant_id,
                        Product.id.in_(request.competitor_product_ids)
                    )
                    .all()
                )
                if len(competitor_products) != len(request.competitor_product_ids):
                    raise HTTPException(status_code=404, detail="Some competitor products not found")
            else:
                # 自动选择2个竞品（排除主产品）
                competitor_products = (
                    db.query(Product)
                    .filter(
                        Product.tenant_id == current_user_data.tenant_id,
                        Product.id != main_product.id
                    )
                    .limit(2)
                    .all()
                )

            if len(competitor_products) < 1:
                raise HTTPException(status_code=404, detail="Not enough competitor products for comparison")

            selected_products = [main_product] + competitor_products

            # 生成详细的Markdown格式报告
            report_content = generate_detailed_markdown_report(
                main_product,
                competitor_products,
                current_user_data.tenant_id
            )

            # 创建报告对象
            report_id = f"report_{datetime.utcnow().timestamp()}"
            report = type('Report', (), {
                'report_id': report_id,
                'report_type': 'competitor_analysis',
                'content': report_content,
                'file_path': None,
                'file_size': len(report_content.encode('utf-8')),
                'created_at': datetime.utcnow(),
                'expires_at': datetime.utcnow() + timedelta(days=7),
                'format': 'markdown'
            })()

            # 存储报告
            report_store[report.report_id] = report

            return ReportResponse(
                report_id=report.report_id,
                report_type="competitor_analysis",
                status="completed",
                file_url=None,
                file_size=report.file_size,
                created_at=report.created_at,
                expires_at=report.expires_at,
            )

        finally:
            db.close()

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Report generation failed: {str(e)}"
        )


@router.get("/", response_model=list[ReportResponse])
async def list_reports(
    report_type: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    """获取报告列表"""

    # 权限检查
    require_permission(current_user, PermissionScope.REPORT_READ)

    # 过滤用户的报告（这里简化为检查存储的报告）
    user_reports = []

    for report_id, report in report_store.items():
        # 检查报告是否过期
        if report.expires_at and datetime.utcnow() > report.expires_at:
            continue

        # 类型过滤
        if report_type and report.report_type != report_type:
            continue

        file_url = f"/api/v1/reports/{report_id}/download" if report.file_path else None

        user_reports.append(
            ReportResponse(
                report_id=report.report_id,
                report_type=report.report_type,
                status="completed",
                file_url=file_url,
                file_size=report.file_size,
                created_at=report.created_at,
                expires_at=report.expires_at,
            )
        )

    # 按创建时间排序并限制数量
    user_reports.sort(key=lambda x: x.created_at, reverse=True)
    return user_reports[:limit]


@router.get("/{report_id}", response_model=ReportResponse)
async def get_report(
    report_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    """获取报告详情"""

    # 权限检查
    require_permission(current_user, PermissionScope.REPORT_READ)

    if report_id not in report_store:
        raise HTTPException(status_code=404, detail="Report not found")

    report = report_store[report_id]

    # 检查报告是否过期
    if report.expires_at and datetime.utcnow() > report.expires_at:
        raise HTTPException(status_code=410, detail="Report has expired")

    file_url = f"/api/v1/reports/{report_id}/download" if report.file_path else None

    return ReportResponse(
        report_id=report.report_id,
        report_type=report.report_type,
        status="completed",
        file_url=file_url,
        file_size=report.file_size,
        created_at=report.created_at,
        expires_at=report.expires_at,
    )


@router.get("/{report_id}/download")
async def download_report(
    report_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    """下载报告文件"""

    # 权限检查
    require_permission(current_user, PermissionScope.REPORT_READ)

    if report_id not in report_store:
        raise HTTPException(status_code=404, detail="Report not found")

    report = report_store[report_id]

    # 检查报告是否过期
    if report.expires_at and datetime.utcnow() > report.expires_at:
        raise HTTPException(status_code=410, detail="Report has expired")

    # 只支持 Markdown 格式
    if report.format == "markdown":
        return Response(
            content=report.content,
            media_type="text/markdown",
            headers={"Content-Disposition": f"attachment; filename={report_id}.md"},
        )
    else:
        raise HTTPException(status_code=400, detail="Unsupported report format")


@router.get("/{report_id}/preview")
async def preview_report(
    report_id: str,
    authorization: HTTPAuthorizationCredentials = Depends(HTTPBearer()),
):
    """预览报告内容（仅限Markdown格式）"""

    # JWT认证
    if not authorization or authorization.scheme != "Bearer":
        raise HTTPException(status_code=401, detail="Invalid authentication")

    token_data = verify_token(authorization.credentials)
    if not token_data:
        raise HTTPException(status_code=401, detail="Invalid token")

    if report_id not in report_store:
        raise HTTPException(status_code=404, detail="Report not found")

    report = report_store[report_id]

    # 检查报告是否过期
    if report.expires_at and datetime.utcnow() > report.expires_at:
        raise HTTPException(status_code=410, detail="Report has expired")

    # 只支持 Markdown 格式预览
    if report.format == "markdown":
        return Response(content=report.content, media_type="text/markdown")
    else:
        raise HTTPException(status_code=400, detail="Unsupported report format")


@router.delete("/{report_id}")
async def delete_report(
    report_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    """删除报告"""

    # 权限检查
    require_permission(current_user, PermissionScope.REPORT_DELETE)

    if report_id not in report_store:
        raise HTTPException(status_code=404, detail="Report not found")

    report = report_store[report_id]

    # 删除文件（如果存在）
    if report.file_path and os.path.exists(report.file_path):
        try:
            os.remove(report.file_path)
        except Exception:
            # 记录错误但不阻止删除操作
            pass

    # 从存储中删除
    del report_store[report_id]

    return {"message": "Report deleted successfully"}


@router.post("/cleanup-expired")
async def cleanup_expired_reports(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    """清理过期报告"""

    # 权限检查（只有管理员可以执行清理）
    require_permission(current_user, PermissionScope.REPORT_MANAGE)

    now = datetime.utcnow()
    expired_reports = []

    for report_id, report in list(report_store.items()):
        if report.expires_at and now > report.expires_at:
            # 删除过期文件
            if report.file_path and os.path.exists(report.file_path):
                try:
                    os.remove(report.file_path)
                except Exception:
                    pass

            # 从存储中删除
            del report_store[report_id]
            expired_reports.append(report_id)

    return {
        "message": f"Cleaned up {len(expired_reports)} expired reports",
        "expired_reports": expired_reports,
    }


@router.get("/templates/available")
async def get_available_templates(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    """获取可用的报告模板"""

    # 权限检查
    require_permission(current_user, PermissionScope.REPORT_READ)

    templates = [
        {
            "type": "competitor",
            "name": "竞品分析报告",
            "description": "深度分析单个产品与其竞争对手的对比情况",
            "required_params": [],
            "supported_formats": ["markdown"],
            "estimated_time": "5-10分钟",
        },
    ]

    return {
        "templates": templates,
        "supported_time_periods": ["7d", "30d", "90d", "1y"],
        "supported_formats": ["markdown"],
        "max_products_per_report": 50,
        "report_retention_days": 7,
    }


@router.get("/stats/usage")
async def get_report_usage_stats(
    days: int = Query(30, ge=1, le=365),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    """获取报告使用统计"""

    # 权限检查
    require_permission(current_user, PermissionScope.REPORT_READ)

    # 计算统计（简化实现）
    now = datetime.utcnow()
    cutoff_date = now - timedelta(days=days)

    total_reports = 0
    by_type = {}
    by_format = {}

    for report in report_store.values():
        if report.created_at >= cutoff_date:
            total_reports += 1

            # 按类型统计
            by_type[report.report_type] = by_type.get(report.report_type, 0) + 1

            # 按格式统计
            by_format[report.format] = by_format.get(report.format, 0) + 1

    return {
        "time_period_days": days,
        "total_reports": total_reports,
        "by_type": by_type,
        "by_format": by_format,
        "active_reports": len(report_store),
        "generated_at": now,
    }


def generate_detailed_markdown_report(main_product, competitor_products, tenant_id):
    """生成详细的Markdown格式竞品对比报告"""

    def safe_get(obj, attr, default="N/A"):
        """安全获取对象属性，如果为None则返回默认值"""
        value = getattr(obj, attr, None)
        return value if value is not None else default

    def format_price(price):
        """格式化价格显示"""
        if price is None:
            return "N/A"
        return f"${float(price):.2f}"

    def format_rating(rating):
        """格式化评分显示"""
        if rating is None:
            return "N/A"
        return f"{float(rating):.1f}/5.0"

    def format_rank(rank):
        """格式化排名显示"""
        if rank is None:
            return "N/A"
        return f"#{rank:,}"

    def extract_bullet_points(product):
        """提取产品特色点"""
        if hasattr(product, 'bullet_points') and product.bullet_points:
            return product.bullet_points
        elif hasattr(product, 'product_data') and product.product_data:
            # 尝试从product_data中提取
            data = product.product_data
            if isinstance(data, dict):
                bullets = data.get('bullet_points') or data.get('features') or data.get('highlights')
                if bullets and isinstance(bullets, list):
                    return bullets
        return ["暂无产品特色信息"]

    # 开始构建报告
    report_lines = []
    report_lines.append("# 竞品分析报告")
    report_lines.append("")
    report_lines.append(f"**生成时间**: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    report_lines.append(f"**租户ID**: {tenant_id}")
    report_lines.append("")

    # 主产品信息
    report_lines.append("## 主产品信息")
    report_lines.append("")
    report_lines.append(f"**产品名称**: {safe_get(main_product, 'title')}")
    report_lines.append(f"**ASIN**: {safe_get(main_product, 'asin')}")
    report_lines.append(f"**品牌**: {safe_get(main_product, 'brand')}")
    report_lines.append(f"**分类**: {safe_get(main_product, 'category')}")
    report_lines.append(f"**当前价格**: {format_price(main_product.current_price)}")
    report_lines.append(f"**BSR排名**: {format_rank(main_product.current_rank)}")
    report_lines.append(f"**评分**: {format_rating(main_product.current_rating)}")
    report_lines.append(f"**评论数**: {safe_get(main_product, 'current_review_count'):,}")
    report_lines.append("")

    # 竞品信息
    report_lines.append("## 竞品信息")
    report_lines.append("")

    for i, competitor in enumerate(competitor_products, 1):
        report_lines.append(f"### 竞品 {i}")
        report_lines.append("")
        report_lines.append(f"**产品名称**: {safe_get(competitor, 'title')}")
        report_lines.append(f"**ASIN**: {safe_get(competitor, 'asin')}")
        report_lines.append(f"**品牌**: {safe_get(competitor, 'brand')}")
        report_lines.append(f"**分类**: {safe_get(competitor, 'category')}")
        report_lines.append(f"**当前价格**: {format_price(competitor.current_price)}")
        report_lines.append(f"**BSR排名**: {format_rank(competitor.current_rank)}")
        report_lines.append(f"**评分**: {format_rating(competitor.current_rating)}")
        report_lines.append(f"**评论数**: {safe_get(competitor, 'current_review_count'):,}")
        report_lines.append("")

    # 价格对比分析
    report_lines.append("## 价格对比分析")
    report_lines.append("")

    main_price = main_product.current_price
    if main_price is not None:
        report_lines.append(f"**主产品价格**: {format_price(main_price)}")
        report_lines.append("")

        for i, competitor in enumerate(competitor_products, 1):
            comp_price = competitor.current_price
            if comp_price is not None:
                price_diff = float(comp_price) - float(main_price)
                price_diff_pct = (price_diff / float(main_price)) * 100

                if price_diff > 0:
                    report_lines.append(f"- **竞品{i}**: {format_price(comp_price)} (比主产品贵 ${price_diff:.2f}, +{price_diff_pct:.1f}%)")
                elif price_diff < 0:
                    report_lines.append(f"- **竞品{i}**: {format_price(comp_price)} (比主产品便宜 ${abs(price_diff):.2f}, {price_diff_pct:.1f}%)")
                else:
                    report_lines.append(f"- **竞品{i}**: {format_price(comp_price)} (价格相同)")
            else:
                report_lines.append(f"- **竞品{i}**: 价格信息缺失")
    else:
        report_lines.append("主产品价格信息缺失，无法进行价格对比。")

    report_lines.append("")

    # BSR排名对比分析
    report_lines.append("## BSR排名对比分析")
    report_lines.append("")

    main_rank = main_product.current_rank
    if main_rank is not None:
        report_lines.append(f"**主产品BSR排名**: {format_rank(main_rank)}")
        report_lines.append("")

        for i, competitor in enumerate(competitor_products, 1):
            comp_rank = competitor.current_rank
            if comp_rank is not None:
                rank_diff = comp_rank - main_rank

                if rank_diff > 0:
                    report_lines.append(f"- **竞品{i}**: {format_rank(comp_rank)} (排名比主产品低 {rank_diff:,} 位)")
                elif rank_diff < 0:
                    report_lines.append(f"- **竞品{i}**: {format_rank(comp_rank)} (排名比主产品高 {abs(rank_diff):,} 位)")
                else:
                    report_lines.append(f"- **竞品{i}**: {format_rank(comp_rank)} (排名相同)")
            else:
                report_lines.append(f"- **竞品{i}**: BSR排名信息缺失")
    else:
        report_lines.append("主产品BSR排名信息缺失，无法进行排名对比。")

    report_lines.append("")

    # 评分优劣势分析
    report_lines.append("## 评分优劣势分析")
    report_lines.append("")

    main_rating = main_product.current_rating
    main_reviews = main_product.current_review_count or 0

    if main_rating is not None:
        report_lines.append(f"**主产品评分**: {format_rating(main_rating)} ({main_reviews:,} 条评论)")
        report_lines.append("")

        for i, competitor in enumerate(competitor_products, 1):
            comp_rating = competitor.current_rating
            comp_reviews = competitor.current_review_count or 0

            if comp_rating is not None:
                rating_diff = float(comp_rating) - float(main_rating)

                if rating_diff > 0:
                    report_lines.append(f"- **竞品{i}**: {format_rating(comp_rating)} ({comp_reviews:,} 条评论) - 评分比主产品高 {rating_diff:.1f} 分")
                elif rating_diff < 0:
                    report_lines.append(f"- **竞品{i}**: {format_rating(comp_rating)} ({comp_reviews:,} 条评论) - 评分比主产品低 {abs(rating_diff):.1f} 分")
                else:
                    report_lines.append(f"- **竞品{i}**: {format_rating(comp_rating)} ({comp_reviews:,} 条评论) - 评分相同")
            else:
                report_lines.append(f"- **竞品{i}**: 评分信息缺失")
    else:
        report_lines.append("主产品评分信息缺失，无法进行评分对比。")

    report_lines.append("")

    # 产品特色对比
    report_lines.append("## 产品特色对比")
    report_lines.append("")

    # 主产品特色
    report_lines.append("### 主产品特色")
    main_bullets = extract_bullet_points(main_product)
    for bullet in main_bullets[:5]:  # 最多显示5个特色点
        report_lines.append(f"- {bullet}")
    report_lines.append("")

    # 竞品特色
    for i, competitor in enumerate(competitor_products, 1):
        report_lines.append(f"### 竞品{i}特色")
        comp_bullets = extract_bullet_points(competitor)
        for bullet in comp_bullets[:5]:  # 最多显示5个特色点
            report_lines.append(f"- {bullet}")
        report_lines.append("")

    # 总结和建议
    report_lines.append("## 分析总结")
    report_lines.append("")

    # 价格竞争力
    if main_price is not None:
        cheaper_count = sum(1 for c in competitor_products if c.current_price and c.current_price < main_price)
        if cheaper_count == 0:
            report_lines.append("**价格竞争力**: 主产品价格相对较低，具有价格优势。")
        elif cheaper_count == len(competitor_products):
            report_lines.append("**价格竞争力**: 主产品价格偏高，建议考虑价格调整策略。")
        else:
            report_lines.append("**价格竞争力**: 主产品价格处于中等水平。")

    # 排名竞争力
    if main_rank is not None:
        better_rank_count = sum(1 for c in competitor_products if c.current_rank and c.current_rank < main_rank)
        if better_rank_count == 0:
            report_lines.append("**排名表现**: 主产品BSR排名领先，市场表现优秀。")
        elif better_rank_count == len(competitor_products):
            report_lines.append("**排名表现**: 主产品BSR排名落后，需要加强市场推广。")
        else:
            report_lines.append("**排名表现**: 主产品BSR排名表现一般，有提升空间。")

    # 评分竞争力
    if main_rating is not None:
        higher_rating_count = sum(1 for c in competitor_products if c.current_rating and c.current_rating > main_rating)
        if higher_rating_count == 0:
            report_lines.append("**用户满意度**: 主产品评分领先，用户满意度高。")
        elif higher_rating_count == len(competitor_products):
            report_lines.append("**用户满意度**: 主产品评分偏低，需要关注产品质量和用户体验。")
        else:
            report_lines.append("**用户满意度**: 主产品评分中等，可进一步提升用户满意度。")

    report_lines.append("")
    report_lines.append("---")
    report_lines.append("*此报告由Amazon产品跟踪系统自动生成*")

    return "\n".join(report_lines)
