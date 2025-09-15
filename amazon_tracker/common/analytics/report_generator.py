"""报告生成器"""

import base64
import io
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Optional

try:
    import matplotlib.pyplot as plt
    import pandas as pd
    import seaborn as sns

    VISUALIZATION_AVAILABLE = True
except ImportError:
    VISUALIZATION_AVAILABLE = False

try:
    from reportlab.lib.colors import Color, black, blue, green, red
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    from reportlab.lib.pagesizes import A4, letter
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.pdfgen import canvas
    from reportlab.platypus import (
        Image,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

from ..database.connection import get_db_session
from ..database.models.product import Product
from .market_analyzer import MarketTrendAnalyzer

logger = logging.getLogger(__name__)


@dataclass
class ReportSection:
    """报告章节"""

    title: str
    content: str
    charts: list[dict[str, Any]]
    data: dict[str, Any]


@dataclass
class GeneratedReport:
    """生成的报告"""

    report_id: str
    report_type: str
    format: str
    content: Any  # 可以是字符串、字节或字典
    file_path: Optional[str]
    file_size: int
    created_at: datetime
    expires_at: Optional[datetime]


class ReportGenerator:
    """报告生成器"""

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.market_analyzer = MarketTrendAnalyzer()

    async def generate_report(
        self,
        tenant_id: str,
        report_type: str,
        product_ids: Optional[list[int]] = None,
        time_period: str = "30d",
        include_charts: bool = True,
        format: str = "pdf",
    ) -> GeneratedReport:
        """生成报告"""

        report_id = f"report_{datetime.utcnow().timestamp()}"

        try:
            # 根据报告类型生成内容
            if report_type == "product":
                report_data = await self._generate_product_report(
                    tenant_id, product_ids, time_period, include_charts
                )
            elif report_type == "competitor":
                raise ValueError("Competitor analysis is currently disabled")
            elif report_type == "market":
                report_data = await self._generate_market_report(
                    tenant_id, time_period, include_charts
                )
            elif report_type == "comprehensive":
                report_data = await self._generate_comprehensive_report(
                    tenant_id, product_ids, time_period, include_charts
                )
            else:
                raise ValueError(f"Unsupported report type: {report_type}")

            # 根据格式生成最终报告
            if format == "pdf":
                content, file_path, file_size = await self._generate_pdf_report(
                    report_id, report_data, include_charts
                )
            elif format == "html":
                content, file_path, file_size = await self._generate_html_report(
                    report_id, report_data, include_charts
                )
            elif format == "json":
                content, file_path, file_size = await self._generate_json_report(
                    report_id, report_data
                )
            else:
                raise ValueError(f"Unsupported format: {format}")

            return GeneratedReport(
                report_id=report_id,
                report_type=report_type,
                format=format,
                content=content,
                file_path=file_path,
                file_size=file_size,
                created_at=datetime.utcnow(),
                expires_at=datetime.utcnow() + timedelta(days=7),  # 7天后过期
            )

        except Exception as e:
            self.logger.error(f"Report generation failed: {e}")
            raise

    async def _generate_product_report(
        self,
        tenant_id: str,
        product_ids: Optional[list[int]],
        time_period: str,
        include_charts: bool,
    ) -> dict[str, Any]:
        """生成产品报告"""

        with get_db_session() as db:
            # 获取产品
            if product_ids:
                products = (
                    db.query(Product)
                    .filter(Product.id.in_(product_ids), Product.tenant_id == tenant_id)
                    .all()
                )
            else:
                products = (
                    db.query(Product)
                    .filter(Product.tenant_id == tenant_id, Product.is_deleted == False)
                    .limit(50)
                    .all()
                )  # 限制最多50个产品

            if not products:
                raise ValueError("No products found")

            sections = []

            # 产品概览章节
            overview_section = await self._create_product_overview_section(products)
            sections.append(overview_section)

            # 价格分析章节
            price_section = await self._create_price_analysis_section(
                products, time_period, include_charts
            )
            sections.append(price_section)

            # 排名分析章节
            rank_section = await self._create_rank_analysis_section(
                products, time_period, include_charts
            )
            sections.append(rank_section)

            # 评分分析章节
            rating_section = await self._create_rating_analysis_section(products)
            sections.append(rating_section)

            # 详细产品信息章节
            if len(products) <= 10:  # 只有产品数量少时才包含详细信息
                detail_section = await self._create_product_detail_section(products)
                sections.append(detail_section)

            return {
                "title": f"产品分析报告 - {len(products)} 个产品",
                "subtitle": f"分析周期: {time_period}",
                "sections": sections,
                "summary": self._create_product_summary(products),
                "metadata": {
                    "product_count": len(products),
                    "time_period": time_period,
                    "generated_at": datetime.utcnow().isoformat(),
                },
            }


    async def _generate_market_report(
        self, tenant_id: str, time_period: str, include_charts: bool
    ) -> dict[str, Any]:
        """生成市场趋势报告"""

        # 执行市场趋势分析
        market_analysis = await self.market_analyzer.analyze_market_trends(
            tenant_id=tenant_id,
            time_period=time_period,
            metrics=["price", "rank", "rating"],
        )

        if "error" in market_analysis:
            raise ValueError(market_analysis["error"])

        sections = []

        # 市场概览章节
        overview_section = ReportSection(
            title="市场概览",
            content=f"分析了 {market_analysis['product_count']} 个产品的市场趋势",
            charts=[],
            data={
                "product_count": market_analysis["product_count"],
                "time_period": time_period,
                "market_health": market_analysis["insights"]["summary"][
                    "market_health"
                ],
            },
        )
        sections.append(overview_section)

        # 价格趋势章节
        if "price" in market_analysis["trend_data"]:
            price_section = await self._create_market_price_section(
                market_analysis["trend_data"]["price"], include_charts
            )
            sections.append(price_section)

        # 排名趋势章节
        if "rank" in market_analysis["trend_data"]:
            rank_section = await self._create_market_rank_section(
                market_analysis["trend_data"]["rank"], include_charts
            )
            sections.append(rank_section)

        # 市场洞察章节
        insights_section = ReportSection(
            title="市场洞察",
            content="\n".join(
                f"• {trend}"
                for trend in market_analysis["insights"]["summary"]["key_trends"]
            ),
            charts=[],
            data=market_analysis["insights"],
        )
        sections.append(insights_section)

        return {
            "title": "市场趋势分析报告",
            "subtitle": f"分析周期: {time_period}",
            "sections": sections,
            "summary": market_analysis["insights"]["summary"],
            "metadata": {
                "product_count": market_analysis["product_count"],
                "time_period": time_period,
                "generated_at": market_analysis["generated_at"],
            },
        }

    async def _generate_comprehensive_report(
        self,
        tenant_id: str,
        product_ids: Optional[list[int]],
        time_period: str,
        include_charts: bool,
    ) -> dict[str, Any]:
        """生成综合报告"""

        # 组合产品报告和市场报告
        product_report = await self._generate_product_report(
            tenant_id, product_ids, time_period, include_charts
        )

        market_report = await self._generate_market_report(
            tenant_id, time_period, include_charts
        )

        # 合并所有章节 (competitor analysis disabled)
        all_sections = product_report["sections"] + market_report["sections"]

        return {
            "title": "综合分析报告",
            "subtitle": f"分析周期: {time_period}",
            "sections": all_sections,
            "summary": {
                "product_summary": product_report["summary"],
                "market_summary": market_report["summary"],
                "total_sections": len(all_sections),
            },
            "metadata": {
                "report_type": "comprehensive",
                "time_period": time_period,
                "generated_at": datetime.utcnow().isoformat(),
            },
        }

    async def _create_product_overview_section(
        self, products: list[Product]
    ) -> ReportSection:
        """创建产品概览章节"""

        total_products = len(products)
        active_products = sum(1 for p in products if p.is_active)
        avg_price = (
            sum(p.current_price for p in products if p.current_price)
            / len([p for p in products if p.current_price])
            if any(p.current_price for p in products)
            else 0
        )
        avg_rating = (
            sum(p.rating for p in products if p.rating)
            / len([p for p in products if p.rating])
            if any(p.rating for p in products)
            else 0
        )

        content = f"""
产品概览统计:
• 总产品数: {total_products}
• 活跃产品数: {active_products}
• 平均价格: ${avg_price:.2f}
• 平均评分: {avg_rating:.2f}/5.0
        """.strip()

        return ReportSection(
            title="产品概览",
            content=content,
            charts=[],
            data={
                "total_products": total_products,
                "active_products": active_products,
                "avg_price": avg_price,
                "avg_rating": avg_rating,
            },
        )

    async def _create_price_analysis_section(
        self, products: list[Product], time_period: str, include_charts: bool
    ) -> ReportSection:
        """创建价格分析章节"""

        prices = [p.current_price for p in products if p.current_price]

        if not prices:
            return ReportSection(
                title="价格分析", content="无价格数据可供分析", charts=[], data={}
            )

        min_price = min(prices)
        max_price = max(prices)
        avg_price = sum(prices) / len(prices)

        content = f"""
价格分析:
• 最低价格: ${min_price:.2f}
• 最高价格: ${max_price:.2f}
• 平均价格: ${avg_price:.2f}
• 价格区间: ${max_price - min_price:.2f}
        """.strip()

        charts = []
        if include_charts and VISUALIZATION_AVAILABLE:
            # 生成价格分布图
            chart_data = self._create_price_distribution_chart(prices)
            charts.append(chart_data)

        return ReportSection(
            title="价格分析",
            content=content,
            charts=charts,
            data={
                "min_price": min_price,
                "max_price": max_price,
                "avg_price": avg_price,
                "price_range": max_price - min_price,
                "price_list": prices,
            },
        )

    async def _create_rank_analysis_section(
        self, products: list[Product], time_period: str, include_charts: bool
    ) -> ReportSection:
        """创建排名分析章节"""

        ranks = [p.current_rank for p in products if p.current_rank]

        if not ranks:
            return ReportSection(
                title="排名分析", content="无排名数据可供分析", charts=[], data={}
            )

        best_rank = min(ranks)
        worst_rank = max(ranks)
        avg_rank = sum(ranks) / len(ranks)

        content = f"""
排名分析:
• 最佳排名: #{best_rank}
• 最差排名: #{worst_rank}
• 平均排名: #{avg_rank:.0f}
• 排名产品数: {len(ranks)}/{len(products)}
        """.strip()

        charts = []
        if include_charts and VISUALIZATION_AVAILABLE:
            # 生成排名分布图
            chart_data = self._create_rank_distribution_chart(ranks)
            charts.append(chart_data)

        return ReportSection(
            title="排名分析",
            content=content,
            charts=charts,
            data={
                "best_rank": best_rank,
                "worst_rank": worst_rank,
                "avg_rank": avg_rank,
                "ranked_products": len(ranks),
                "rank_list": ranks,
            },
        )

    async def _create_rating_analysis_section(
        self, products: list[Product]
    ) -> ReportSection:
        """创建评分分析章节"""

        ratings = [p.rating for p in products if p.rating]

        if not ratings:
            return ReportSection(
                title="评分分析", content="无评分数据可供分析", charts=[], data={}
            )

        avg_rating = sum(ratings) / len(ratings)
        high_rated = sum(1 for r in ratings if r >= 4.0)
        low_rated = sum(1 for r in ratings if r < 3.0)

        content = f"""
评分分析:
• 平均评分: {avg_rating:.2f}/5.0
• 高评分产品 (≥4.0): {high_rated}
• 低评分产品 (<3.0): {low_rated}
• 有评分产品数: {len(ratings)}/{len(products)}
        """.strip()

        return ReportSection(
            title="评分分析",
            content=content,
            charts=[],
            data={
                "avg_rating": avg_rating,
                "high_rated_count": high_rated,
                "low_rated_count": low_rated,
                "rated_products": len(ratings),
                "rating_list": ratings,
            },
        )

    async def _create_product_detail_section(
        self, products: list[Product]
    ) -> ReportSection:
        """创建产品详细信息章节"""

        content_lines = ["产品详细信息:\n"]

        for i, product in enumerate(products[:10], 1):  # 最多显示10个产品
            price_str = (
                f"${product.current_price:.2f}" if product.current_price else "N/A"
            )
            rating_str = f"{product.rating:.1f}/5.0" if product.rating else "N/A"
            rank_str = f"#{product.current_rank}" if product.current_rank else "N/A"

            content_lines.append(
                f"{i}. {product.title[:50]}...\n"
                f"   ASIN: {product.asin} | 价格: {price_str} | 评分: {rating_str} | 排名: {rank_str}\n"
            )

        return ReportSection(
            title="产品详细信息",
            content="\n".join(content_lines),
            charts=[],
            data={"products": [p.__dict__ for p in products[:10]]},
        )

    def _create_product_summary(self, products: list[Product]) -> dict[str, Any]:
        """创建产品总结"""

        return {
            "total_products": len(products),
            "active_products": sum(1 for p in products if p.is_active),
            "avg_price": sum(p.current_price for p in products if p.current_price)
            / len([p for p in products if p.current_price])
            if any(p.current_price for p in products)
            else None,
            "avg_rating": sum(p.rating for p in products if p.rating)
            / len([p for p in products if p.rating])
            if any(p.rating for p in products)
            else None,
            "top_categories": list(set(p.category for p in products if p.category))[:5],
            "top_brands": list(set(p.brand for p in products if p.brand))[:5],
        }

    def _create_price_distribution_chart(self, prices: list[float]) -> dict[str, Any]:
        """创建价格分布图"""
        if not VISUALIZATION_AVAILABLE:
            return {"error": "Visualization libraries not available"}

        try:
            plt.figure(figsize=(10, 6))
            plt.hist(prices, bins=20, alpha=0.7, color="blue")
            plt.title("价格分布")
            plt.xlabel("价格 ($)")
            plt.ylabel("产品数量")
            plt.grid(True, alpha=0.3)

            # 保存图表为base64字符串
            buffer = io.BytesIO()
            plt.savefig(buffer, format="png", dpi=150, bbox_inches="tight")
            buffer.seek(0)
            chart_base64 = base64.b64encode(buffer.getvalue()).decode()
            plt.close()

            return {
                "type": "histogram",
                "title": "价格分布",
                "data": chart_base64,
                "format": "png",
            }

        except Exception as e:
            return {"error": f"Chart generation failed: {e}"}

    def _create_rank_distribution_chart(self, ranks: list[int]) -> dict[str, Any]:
        """创建排名分布图"""
        if not VISUALIZATION_AVAILABLE:
            return {"error": "Visualization libraries not available"}

        try:
            plt.figure(figsize=(10, 6))
            plt.hist(ranks, bins=20, alpha=0.7, color="green")
            plt.title("排名分布")
            plt.xlabel("排名")
            plt.ylabel("产品数量")
            plt.grid(True, alpha=0.3)

            # 保存图表为base64字符串
            buffer = io.BytesIO()
            plt.savefig(buffer, format="png", dpi=150, bbox_inches="tight")
            buffer.seek(0)
            chart_base64 = base64.b64encode(buffer.getvalue()).decode()
            plt.close()

            return {
                "type": "histogram",
                "title": "排名分布",
                "data": chart_base64,
                "format": "png",
            }

        except Exception as e:
            return {"error": f"Chart generation failed: {e}"}


    async def _create_market_price_section(
        self, price_data: list[dict], include_charts: bool
    ) -> ReportSection:
        """创建市场价格章节"""

        if not price_data:
            return ReportSection(
                title="市场价格趋势", content="无价格趋势数据", charts=[], data={}
            )

        first_price = price_data[0]["value"]
        last_price = price_data[-1]["value"]
        change_percent = (last_price - first_price) / first_price * 100

        direction = (
            "上涨" if change_percent > 0 else "下跌" if change_percent < 0 else "稳定"
        )

        content = f"""
市场价格趋势:
• 期初平均价格: ${first_price:.2f}
• 期末平均价格: ${last_price:.2f}
• 变化幅度: {abs(change_percent):.1f}% ({direction})
• 数据点数: {len(price_data)}
        """.strip()

        return ReportSection(
            title="市场价格趋势",
            content=content,
            charts=[],
            data={
                "first_price": first_price,
                "last_price": last_price,
                "change_percent": change_percent,
                "direction": direction,
                "data_points": len(price_data),
            },
        )

    async def _create_market_rank_section(
        self, rank_data: list[dict], include_charts: bool
    ) -> ReportSection:
        """创建市场排名章节"""

        if not rank_data:
            return ReportSection(
                title="市场排名趋势", content="无排名趋势数据", charts=[], data={}
            )

        first_rank = rank_data[0]["value"]
        last_rank = rank_data[-1]["value"]
        change_percent = (first_rank - last_rank) / first_rank * 100  # 排名降低是好事

        direction = (
            "改善" if change_percent > 0 else "下降" if change_percent < 0 else "稳定"
        )

        content = f"""
市场排名趋势:
• 期初平均排名: #{first_rank:.0f}
• 期末平均排名: #{last_rank:.0f}
• 变化幅度: {abs(change_percent):.1f}% ({direction})
• 数据点数: {len(rank_data)}
        """.strip()

        return ReportSection(
            title="市场排名趋势",
            content=content,
            charts=[],
            data={
                "first_rank": first_rank,
                "last_rank": last_rank,
                "change_percent": change_percent,
                "direction": direction,
                "data_points": len(rank_data),
            },
        )

    async def _generate_pdf_report(
        self, report_id: str, report_data: dict[str, Any], include_charts: bool
    ) -> tuple:
        """生成PDF报告"""

        if not PDF_AVAILABLE:
            raise ValueError("PDF generation libraries not available")

        file_path = f"/tmp/{report_id}.pdf"

        try:
            # 创建PDF文档
            doc = SimpleDocTemplate(file_path, pagesize=A4)
            styles = getSampleStyleSheet()
            story = []

            # 标题
            title_style = ParagraphStyle(
                "CustomTitle",
                parent=styles["Heading1"],
                fontSize=18,
                spaceAfter=30,
                alignment=TA_CENTER,
            )
            story.append(Paragraph(report_data["title"], title_style))

            if report_data.get("subtitle"):
                story.append(Paragraph(report_data["subtitle"], styles["Heading2"]))

            story.append(Spacer(1, 20))

            # 添加各个章节
            for section in report_data["sections"]:
                # 章节标题
                story.append(Paragraph(section.title, styles["Heading2"]))
                story.append(Spacer(1, 10))

                # 章节内容
                content_lines = section.content.split("\n")
                for line in content_lines:
                    if line.strip():
                        story.append(Paragraph(line, styles["Normal"]))

                story.append(Spacer(1, 15))

                # 添加图表（如果有）
                for chart in section.charts:
                    if chart.get("data") and not chart.get("error"):
                        try:
                            # 解码base64图片
                            image_data = base64.b64decode(chart["data"])
                            image_buffer = io.BytesIO(image_data)

                            # 添加图片到PDF
                            img = Image(image_buffer, width=400, height=240)
                            story.append(img)
                            story.append(Spacer(1, 10))
                        except Exception as e:
                            self.logger.warning(f"Failed to add chart to PDF: {e}")

            # 生成PDF
            doc.build(story)

            # 获取文件大小
            import os

            file_size = os.path.getsize(file_path)

            # 读取文件内容
            with open(file_path, "rb") as f:
                content = f.read()

            return content, file_path, file_size

        except Exception as e:
            self.logger.error(f"PDF generation failed: {e}")
            raise

    async def _generate_html_report(
        self, report_id: str, report_data: dict[str, Any], include_charts: bool
    ) -> tuple:
        """生成HTML报告"""

        html_template = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }}
        h1 {{ color: #333; text-align: center; }}
        h2 {{ color: #666; border-bottom: 2px solid #ddd; padding-bottom: 10px; }}
        .section {{ margin-bottom: 30px; }}
        .chart {{ text-align: center; margin: 20px 0; }}
        pre {{ background: #f4f4f4; padding: 15px; border-radius: 5px; }}
        .summary {{ background: #f9f9f9; padding: 20px; border-radius: 5px; margin: 20px 0; }}
    </style>
</head>
<body>
    <h1>{title}</h1>
    {subtitle}

    {content}

    <div class="summary">
        <h2>报告总结</h2>
        <pre>{summary}</pre>
    </div>

    <footer>
        <p><small>生成时间: {generated_at}</small></p>
    </footer>
</body>
</html>
        """

        # 构建内容
        content_html = ""
        for section in report_data["sections"]:
            content_html += '<div class="section">\n'
            content_html += f"<h2>{section.title}</h2>\n"
            content_html += f"<pre>{section.content}</pre>\n"

            # 添加图表
            for chart in section.charts:
                if chart.get("data") and not chart.get("error"):
                    content_html += '<div class="chart">\n'
                    content_html += f'<img src="data:image/png;base64,{chart["data"]}" alt="{chart["title"]}" style="max-width: 100%;">\n'
                    content_html += "</div>\n"

            content_html += "</div>\n"

        # 生成HTML
        html_content = html_template.format(
            title=report_data["title"],
            subtitle=f'<p style="text-align: center; color: #666;">{report_data.get("subtitle", "")}</p>'
            if report_data.get("subtitle")
            else "",
            content=content_html,
            summary=json.dumps(
                report_data.get("summary", {}), indent=2, ensure_ascii=False
            ),
            generated_at=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        )

        # 保存文件
        file_path = f"/tmp/{report_id}.html"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        file_size = len(html_content.encode("utf-8"))

        return html_content, file_path, file_size

    async def _generate_json_report(
        self, report_id: str, report_data: dict[str, Any]
    ) -> tuple:
        """生成JSON报告"""

        # 直接返回JSON数据
        json_content = json.dumps(
            report_data, indent=2, ensure_ascii=False, default=str
        )

        file_path = f"/tmp/{report_id}.json"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(json_content)

        file_size = len(json_content.encode("utf-8"))

        return json_content, file_path, file_size
