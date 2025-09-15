"""基于LangChain的竞品分析报告生成器"""

import json
import logging
from datetime import datetime
from typing import Any, Optional

from langchain.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from ..cache.redis_manager import cache_manager, cache_result
from ..config.settings import get_settings

logger = logging.getLogger(__name__)


class CompetitorReportGenerator:
    """竞品分析报告生成器"""

    def __init__(self):
        settings = get_settings()
        self.openai_api_key = settings.OPENAI_API_KEY
        self.model_name = settings.OPENAI_MODEL
        self.max_tokens = settings.OPENAI_MAX_TOKENS

        if not self.openai_api_key:
            raise ValueError("OpenAI API key is required for report generation")

        # 初始化LangChain模型
        self.llm = ChatOpenAI(
            model=self.model_name,
            api_key=self.openai_api_key,
            max_tokens=self.max_tokens,
            temperature=0.3,  # 稍低的温度以获得更一致的结果
        )

    def _create_competitor_analysis_prompt(self) -> ChatPromptTemplate:
        """创建竞品分析提示模板"""

        prompt_template = """
        你是一位资深的Amazon产品分析专家，拥有丰富的电商竞品分析经验。请基于以下数据生成一份专业、深入的竞品分析报告。

        ## 主产品信息
        - **ASIN**: {main_asin}
        - **产品标题**: {main_title}
        - **品牌**: {main_brand}
        - **当前价格**: ${main_price}
        - **评分**: {main_rating}/5.0 ({main_review_count}条评论)
        - **BSR排名**: #{main_rank}
        - **产品分类**: {main_category}

        ## 竞品数据
        {competitors_data}

        ## 分析要求

        请从以下维度进行全面、深入的分析，每个维度都要提供具体的数据支撑和可执行的建议：

        ### 1. 📊 市场定位与竞争态势分析
        - 分析主产品在价格-质量矩阵中的定位（价值型、高端、平衡型、成本型）
        - 识别主要竞争对手并分析其竞争策略
        - 评估市场集中度和竞争激烈程度
        - 分析主产品的差异化优势和劣势

        ### 2. 💰 价格策略与竞争力分析
        - 主产品价格在竞品中的百分位排名
        - 价格敏感性分析和最优定价区间建议
        - 与同质量级别竞品的价格对比
        - 价格调整的风险与机会评估
        - 具体的定价策略建议（涨价/降价/维持）

        ### 3. ⭐ 产品质量与用户满意度分析
        - 评分和评论数的综合信任度分析
        - 与竞品的评分差距及其影响
        - 用户满意度趋势预测
        - 产品质量改进的优先级建议

        ### 4. 📈 市场表现与销售潜力分析
        - BSR排名表现及其市场意义
        - 基于评论数量的市场份额估算
        - 销售趋势和增长潜力评估
        - 市场机会识别和威胁分析

        ### 5. 🎯 竞争优势与差异化策略
        - 识别主产品的核心竞争优势
        - 分析竞品的优势并提出应对策略
        - 差异化竞争点的挖掘和强化建议
        - 蓝海市场机会识别

        ### 6. 🚀 具体优化行动计划
        - **短期行动（1-3个月）**：立即可执行的改进措施
        - **中期策略（3-6个月）**：需要资源投入的优化项目
        - **长期规划（6-12个月）**：战略性发展方向
        - 每项建议都要包含：预期效果、实施难度、资源需求、关键指标

        ### 7. 📋 监控指标与预警机制
        - 关键竞争指标的监控建议
        - 竞品动态预警机制
        - 市场变化的应对预案

        ## 输出要求
        1. 使用专业的商业分析语言，避免空泛表述
        2. 每个分析点都要有具体数据支撑
        3. 建议要具体、可执行、有优先级
        4. 使用Markdown格式，结构清晰
        5. 包含风险评估和机会量化
        6. 提供决策支持的关键洞察

        请确保分析深度和实用性，为电商运营团队提供有价值的决策依据。
        """

        return ChatPromptTemplate.from_template(prompt_template)

    def _format_competitors_data(self, competitors: list[dict]) -> str:
        """格式化竞品数据为文本"""
        if not competitors:
            return "未找到竞品数据"

        formatted_data = []
        
        # 添加竞品概览
        total_competitors = len(competitors)
        avg_price = sum(c.get('price', 0) for c in competitors if c.get('price')) / len([c for c in competitors if c.get('price')]) if competitors else 0
        avg_rating = sum(c.get('rating', 0) for c in competitors if c.get('rating')) / len([c for c in competitors if c.get('rating')]) if competitors else 0
        
        overview = f"""
### 竞品概览
- **竞品总数**: {total_competitors}
- **平均价格**: ${avg_price:.2f}
- **平均评分**: {avg_rating:.1f}/5.0
- **价格区间**: ${min(c.get('price', 0) for c in competitors if c.get('price', 0)):.2f} - ${max(c.get('price', 0) for c in competitors if c.get('price', 0)):.2f}

### 详细竞品信息
        """
        formatted_data.append(overview.strip())

        for i, competitor in enumerate(competitors, 1):
            # 计算信任度评分
            trust_score = 0
            if competitor.get('rating') and competitor.get('review_count'):
                trust_score = competitor.get('rating', 0) * (1 + min(competitor.get('review_count', 0) / 1000, 2))
            
            # 价格定位分析
            price_position = "未知"
            if competitor.get('price') and avg_price > 0:
                price_ratio = competitor.get('price', 0) / avg_price
                if price_ratio > 1.2:
                    price_position = "高端定位"
                elif price_ratio < 0.8:
                    price_position = "价值定位"
                else:
                    price_position = "中端定位"
            
            # 特征提取
            features_text = ""
            if competitor.get('features'):
                features_list = competitor.get('features', [])[:5]  # 只显示前5个特征
                features_text = f"  - **主要特征**: {', '.join(features_list)}"
            
            competitor_info = f"""
**竞品 {i}** - {competitor.get('brand', 'Unknown Brand')}
- **ASIN**: {competitor.get('asin', 'N/A')}
- **产品名称**: {competitor.get('title', 'N/A')[:100]}{'...' if len(competitor.get('title', '')) > 100 else ''}
- **价格**: ${competitor.get('price', 0):.2f} ({price_position})
- **评分**: {competitor.get('rating', 0)}/5.0 ({competitor.get('review_count', 0):,}条评论)
- **BSR排名**: #{competitor.get('rank', 'N/A')}
- **信任度评分**: {trust_score:.1f}
- **竞争力评分**: {competitor.get('competitive_score', 0):.1f}/100
- **相似度评分**: {competitor.get('similarity_score', 0):.1f}/100{features_text}
- **产品分类**: {competitor.get('category', 'N/A')}
- **可用性**: {competitor.get('availability', 'N/A')}
            """
            formatted_data.append(competitor_info.strip())

        return "\n\n".join(formatted_data)

    @cache_result(ttl=48 * 60 * 60, prefix="ai_reports")  # 48小时缓存
    async def generate_competitor_report(
        self,
        main_product: dict[str, Any],
        competitors: list[dict[str, Any]],
        report_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """生成竞品分析报告

        Args:
            main_product: 主产品数据
            competitors: 竞品数据列表
            report_id: 报告ID（用于缓存）

        Returns:
            包含报告内容和元数据的字典
        """
        try:
            # 创建提示模板
            prompt = self._create_competitor_analysis_prompt()

            # 格式化竞品数据
            competitors_text = self._format_competitors_data(competitors)

            # 构建LangChain链
            chain = prompt | self.llm

            # 准备输入数据
            input_data = {
                "main_asin": main_product.get("asin", "N/A"),
                "main_title": main_product.get("title", "N/A"),
                "main_brand": main_product.get("brand", "N/A"),
                "main_price": main_product.get("price", 0),
                "main_rating": main_product.get("rating", 0),
                "main_review_count": main_product.get("review_count", 0),
                "main_rank": main_product.get("rank", "N/A"),
                "main_category": main_product.get("category", "N/A"),
                "competitors_data": competitors_text,
            }

            logger.info(
                f"Generating competitor report for ASIN: {main_product.get('asin')}"
            )

            # 调用LLM生成报告
            response = await chain.ainvoke(input_data)

            # 构建报告结果
            report = {
                "report_id": report_id or f"report_{datetime.utcnow().timestamp()}",
                "main_product": {
                    "asin": main_product.get("asin"),
                    "title": main_product.get("title"),
                    "brand": main_product.get("brand"),
                },
                "competitors_count": len(competitors),
                "analysis_content": response.content,
                "generation_metadata": {
                    "model": self.model_name,
                    "generated_at": datetime.utcnow().isoformat(),
                    "input_tokens_estimate": len(str(input_data)) // 4,  # 粗略估算
                    "competitors_analyzed": len(competitors),
                },
            }

            # 缓存报告
            if report_id:
                cache_manager.cache_analysis_report(report_id, report)

            logger.info(
                f"Report generated successfully for ASIN: {main_product.get('asin')}"
            )
            return report

        except Exception as e:
            logger.error(f"Failed to generate competitor report: {e}")
            return {
                "error": str(e),
                "report_id": report_id,
                "generated_at": datetime.utcnow().isoformat(),
            }

    def _create_optimization_suggestions_prompt(self) -> ChatPromptTemplate:
        """创建优化建议提示模板"""

        prompt_template = """
        你是一位Amazon产品优化专家和电商运营顾问，拥有多年的Amazon平台运营经验。请基于以下产品数据和竞品分析，生成一份详细、可执行的产品优化策略报告。

        ## 📊 产品当前表现
        - **ASIN**: {asin}
        - **产品标题**: {title}
        - **当前价格**: ${current_price}
        - **评分**: {rating}/5.0 ({review_count}条评论)
        - **BSR排名**: #{rank}
        - **价格趋势**: {price_trend}
        - **排名趋势**: {rank_trend}

        ## 🔍 竞品分析洞察
        {competitor_insights}

        ## 📋 优化建议要求

        请针对以下维度提供具体、可执行的优化建议，每个建议都要包含详细的实施计划：

        ### 1. 💰 定价策略优化
        **分析竞品价格策略并提供定价建议：**
        - 基于竞品价格分布的最优定价区间
        - 价格弹性分析和收益最大化策略
        - 促销时机和折扣幅度建议
        - 动态定价策略（应对竞品价格变化）
        - Bundle销售策略建议
        
        **每项建议包含：**
        - 具体价格建议（具体数值）
        - 预期销量和收入影响
        - 风险评估和缓解措施
        - 实施时间点建议

        ### 2. 🎯 产品页面优化（Listing优化）
        **全面的Listing优化方案：**
        - **标题优化**：关键词策略、可读性提升、转化率优化
        - **图片优化**：主图改进建议、生活场景图创意、信息图设计
        - **五点描述优化**：卖点提炼、差异化表达、用户痛点解决
        - **A+页面内容**：品牌故事、产品对比、使用场景展示
        - **关键词策略**：后台搜索词优化、长尾关键词挖掘
        
        **每项建议包含：**
        - 具体修改内容示例
        - 预期点击率和转化率提升
        - 制作成本和时间估算
        - A/B测试建议

        ### 3. 📦 库存与运营优化
        **运营效率提升方案：**
        - **库存管理**：安全库存设置、补货周期优化、季节性调整
        - **FBA策略**：仓储费用优化、配送速度提升、退货率降低
        - **广告投放**：关键词出价策略、广告类型选择、预算分配
        - **促销活动**：Lightning Deal、Coupon、Best Deal申请策略
        
        **每项建议包含：**
        - 具体操作步骤
        - 预期成本和收益
        - KPI监控指标
        - 时间节点规划

        ### 4. 😊 客户体验提升
        **全方位客户体验改善：**
        - **产品质量改进**：基于负面评论的产品缺陷修复
        - **客户服务优化**：响应时间、解决方案、满意度提升
        - **售后体系**：退换货流程、质保政策、客户关怀
        - **评论管理**：Review获取策略、负面评论处理、客户反馈循环
        
        **每项建议包含：**
        - 具体改进措施
        - 客户满意度提升预期
        - 实施资源需求
        - 效果衡量标准

        ### 5. 🚀 竞争策略与差异化
        **市场竞争优势构建：**
        - **差异化定位**：独特卖点挖掘、市场空白点识别
        - **品牌建设**：品牌故事包装、用户认知提升
        - **产品创新**：功能升级方向、新品开发机会
        - **市场拓展**：新类目进入、国际市场机会
        - **生态系统构建**：产品组合策略、交叉销售机会
        
        **每项建议包含：**
        - 战略实施路径
        - 投资回报预期
        - 竞争壁垒构建
        - 长期价值创造

        ### 6. 📈 数据监控与迭代优化
        **持续优化体系建立：**
        - 关键指标监控仪表板设计
        - 竞品动态追踪机制
        - 市场变化预警系统
        - 优化效果评估标准

        ## 📋 输出格式要求
        1. **优先级排序**：根据影响度和实施难度进行优先级排序（P0-P2）
        2. **时间规划**：短期（1-2周）、中期（1-3个月）、长期（3-12个月）
        3. **资源需求**：人力、时间、资金的具体需求估算
        4. **风险评估**：每项建议的潜在风险和缓解方案
        5. **ROI预期**：投入产出比的合理预期和计算逻辑
        6. **执行清单**：可直接执行的行动项清单

        请确保所有建议都是基于数据分析的结论，具有很强的可操作性和实用价值。
        """

        return ChatPromptTemplate.from_template(prompt_template)

    @cache_result(ttl=24 * 60 * 60, prefix="ai_suggestions")  # 24小时缓存
    async def generate_optimization_suggestions(
        self,
        product_data: dict[str, Any],
        competitor_insights: dict[str, Any],
        historical_data: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """生成产品优化建议

        Args:
            product_data: 产品数据
            competitor_insights: 竞品分析洞察
            historical_data: 历史数据（趋势分析）

        Returns:
            优化建议报告
        """
        try:
            # 创建提示模板
            prompt = self._create_optimization_suggestions_prompt()

            # 准备趋势数据
            price_trend = "数据不足"
            rank_trend = "数据不足"

            if historical_data:
                price_trend = historical_data.get("price_trend", {}).get(
                    "direction", "稳定"
                )
                rank_trend = historical_data.get("rank_trend", {}).get(
                    "direction", "稳定"
                )

            # 格式化竞品洞察
            insights_text = json.dumps(
                competitor_insights, ensure_ascii=False, indent=2
            )

            # 构建链
            chain = prompt | self.llm

            # 准备输入数据
            input_data = {
                "asin": product_data.get("asin", "N/A"),
                "title": product_data.get("title", "N/A"),
                "current_price": product_data.get("price", 0),
                "rating": product_data.get("rating", 0),
                "review_count": product_data.get("review_count", 0),
                "rank": product_data.get("rank", "N/A"),
                "price_trend": price_trend,
                "rank_trend": rank_trend,
                "competitor_insights": insights_text,
            }

            logger.info(
                f"Generating optimization suggestions for ASIN: {product_data.get('asin')}"
            )

            # 调用LLM
            response = await chain.ainvoke(input_data)

            suggestion_report = {
                "product_asin": product_data.get("asin"),
                "suggestions_content": response.content,
                "generation_metadata": {
                    "model": self.model_name,
                    "generated_at": datetime.utcnow().isoformat(),
                    "based_on_competitors": len(
                        competitor_insights.get("competitors", [])
                    ),
                    "has_historical_data": historical_data is not None,
                },
            }

            logger.info(
                f"Optimization suggestions generated for ASIN: {product_data.get('asin')}"
            )
            return suggestion_report

        except Exception as e:
            logger.error(f"Failed to generate optimization suggestions: {e}")
            return {
                "error": str(e),
                "product_asin": product_data.get("asin"),
                "generated_at": datetime.utcnow().isoformat(),
            }

    async def generate_market_summary(
        self, category: str, products_data: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """生成市场概况总结

        Args:
            category: 产品分类
            products_data: 产品数据列表

        Returns:
            市场概况报告
        """
        prompt_template = """
        基于以下{category}类别的产品数据，生成市场概况分析报告：

        产品数据概览：
        {products_summary}

        请分析以下内容：
        1. **市场价格分布**
        2. **品牌竞争格局**
        3. **消费者偏好趋势**
        4. **市场机会识别**
        5. **进入壁垒分析**

        提供客观的数据分析和市场洞察。
        """

        try:
            # 处理产品数据
            products_summary = "\n".join(
                [
                    f"- {p.get('brand', 'Unknown')}: ${p.get('price', 0):.2f}, "
                    f"评分{p.get('rating', 0)}, 排名#{p.get('rank', 'N/A')}"
                    for p in products_data[:20]  # 限制数量以避免token过多
                ]
            )

            prompt = ChatPromptTemplate.from_template(prompt_template)
            chain = prompt | self.llm

            response = await chain.ainvoke(
                {"category": category, "products_summary": products_summary}
            )

            return {
                "category": category,
                "market_summary": response.content,
                "products_analyzed": len(products_data),
                "generated_at": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Failed to generate market summary: {e}")
            return {"error": str(e), "category": category}
    
    async def generate_competitive_landscape_report(
        self,
        main_product: dict[str, Any],
        competitors: list[dict[str, Any]],
        market_insights: dict[str, Any],
        report_id: Optional[str] = None
    ) -> dict[str, Any]:
        """生成竞争格局报告"""
        
        prompt_template = """
        作为一位资深的市场分析专家，请基于以下数据生成一份全面的竞争格局分析报告。

        ## 主产品信息
        - **ASIN**: {main_asin}
        - **品牌**: {main_brand}
        - **产品**: {main_title}
        - **价格**: ${main_price}
        - **评分**: {main_rating}/5.0 ({main_review_count}条评论)
        - **排名**: #{main_rank}

        ## 竞品分析数据
        {competitors_data}

        ## 市场洞察数据
        {market_insights}

        请生成以下分析报告：

        ### 1. 🏆 竞争格局概览
        - 市场主要玩家识别和分类（领导者、挑战者、跟随者、利基玩家）
        - 市场集中度分析（CR4、HHI指数）
        - 竞争激烈程度评估
        - 市场进入壁垒分析

        ### 2. 📊 竞争维度矩阵分析
        - 价格-质量四象限定位图
        - 品牌知名度-市场份额分析
        - 产品创新度-客户满意度评估
        - 渠道覆盖-营销投入对比

        ### 3. 🎯 主要竞争对手深度画像
        为每个主要竞争对手提供：
        - 竞争策略分析（成本领先/差异化/聚焦）
        - 核心竞争优势和劣势
        - 市场行为模式和反应特点
        - 未来发展趋势预测

        ### 4. 💡 市场机会与威胁识别
        - **蓝海机会**：未被满足的市场需求
        - **红海挑战**：激烈竞争的市场领域
        - **新兴威胁**：潜在的颠覆性竞争者
        - **结构性变化**：可能改变竞争格局的因素

        ### 5. 🚀 竞争策略建议
        - 针对不同竞争对手的具体应对策略
        - 市场定位优化建议
        - 差异化竞争策略
        - 防御性策略和进攻性策略平衡

        ### 6. 📈 未来竞争格局预测
        - 6-12个月市场变化趋势预测
        - 新进入者威胁评估
        - 技术变革对竞争格局的影响
        - 监控预警指标设置

        请确保分析客观、深入，提供具有战略价值的洞察和建议。
        """

        try:
            competitors_text = self._format_competitors_data(competitors)
            market_insights_text = json.dumps(market_insights, ensure_ascii=False, indent=2)

            prompt = ChatPromptTemplate.from_template(prompt_template)
            chain = prompt | self.llm

            input_data = {
                "main_asin": main_product.get("asin", "N/A"),
                "main_brand": main_product.get("brand", "N/A"),
                "main_title": main_product.get("title", "N/A"),
                "main_price": main_product.get("price", 0),
                "main_rating": main_product.get("rating", 0),
                "main_review_count": main_product.get("review_count", 0),
                "main_rank": main_product.get("rank", "N/A"),
                "competitors_data": competitors_text,
                "market_insights": market_insights_text
            }

            logger.info(f"Generating competitive landscape report for ASIN: {main_product.get('asin')}")

            response = await chain.ainvoke(input_data)

            report = {
                "report_id": report_id or f"landscape_{datetime.utcnow().timestamp()}",
                "report_type": "competitive_landscape",
                "main_product": {
                    "asin": main_product.get("asin"),
                    "brand": main_product.get("brand"),
                    "title": main_product.get("title")
                },
                "competitors_analyzed": len(competitors),
                "landscape_content": response.content,
                "market_insights": market_insights,
                "generation_metadata": {
                    "model": self.model_name,
                    "generated_at": datetime.utcnow().isoformat(),
                    "analysis_scope": "competitive_landscape",
                    "data_sources": ["competitor_analysis", "market_insights"]
                }
            }

            logger.info(f"Competitive landscape report generated for ASIN: {main_product.get('asin')}")
            return report

        except Exception as e:
            logger.error(f"Failed to generate competitive landscape report: {e}")
            return {
                "error": str(e),
                "report_id": report_id,
                "generated_at": datetime.utcnow().isoformat()
            }
    
    async def generate_pricing_strategy_report(
        self,
        main_product: dict[str, Any],
        competitors: list[dict[str, Any]],
        pricing_analysis: dict[str, Any],
        report_id: Optional[str] = None
    ) -> dict[str, Any]:
        """生成定价策略报告"""
        
        prompt_template = """
        作为一位定价策略专家，请基于以下数据生成详细的定价策略分析报告。

        ## 产品信息
        - **ASIN**: {main_asin}
        - **当前价格**: ${main_price}
        - **评分**: {main_rating}/5.0
        - **评论数**: {main_review_count}
        - **BSR排名**: #{main_rank}

        ## 竞品价格数据
        {competitors_data}

        ## 定价分析数据
        {pricing_analysis}

        请提供以下定价策略分析：

        ### 1. 💰 当前定价诊断
        - 价格竞争力评估
        - 价格-价值匹配度分析
        - 价格弹性估算
        - 定价策略类型识别

        ### 2. 📊 市场定价基准分析
        - 竞品价格分布和定价模式
        - 价格区间机会识别
        - 最优定价区间建议
        - 价格敏感度分析

        ### 3. 🎯 动态定价策略
        - **促销定价策略**：何时降价、降价幅度、促销周期
        - **季节性定价**：淡旺季定价调整策略
        - **竞争性定价**：应对竞品价格变动的策略
        - **心理定价**：价格锚点和消费者心理因素

        ### 4. 📈 收益优化模型
        - 不同价格点的收益预测模型
        - 销量-价格-利润三维优化
        - 最大化收益的定价建议
        - ROI和利润率影响分析

        ### 5. ⚠️ 定价风险评估
        - 价格战风险和应对策略
        - 品牌价值稀释风险
        - 客户流失风险评估
        - 价格调整时机风险

        ### 6. 🚀 实施建议
        - 分阶段定价调整计划
        - A/B测试策略设计
        - 监控指标和预警机制
        - 定价决策流程优化

        请提供具体的价格数值建议和详细的实施路径。
        """

        try:
            competitors_text = self._format_competitors_data(competitors)
            pricing_analysis_text = json.dumps(pricing_analysis, ensure_ascii=False, indent=2)

            prompt = ChatPromptTemplate.from_template(prompt_template)
            chain = prompt | self.llm

            input_data = {
                "main_asin": main_product.get("asin", "N/A"),
                "main_price": main_product.get("price", 0),
                "main_rating": main_product.get("rating", 0),
                "main_review_count": main_product.get("review_count", 0),
                "main_rank": main_product.get("rank", "N/A"),
                "competitors_data": competitors_text,
                "pricing_analysis": pricing_analysis_text
            }

            logger.info(f"Generating pricing strategy report for ASIN: {main_product.get('asin')}")

            response = await chain.ainvoke(input_data)

            report = {
                "report_id": report_id or f"pricing_{datetime.utcnow().timestamp()}",
                "report_type": "pricing_strategy",
                "main_product": {
                    "asin": main_product.get("asin"),
                    "current_price": main_product.get("price")
                },
                "competitors_analyzed": len(competitors),
                "pricing_content": response.content,
                "pricing_data": pricing_analysis,
                "generation_metadata": {
                    "model": self.model_name,
                    "generated_at": datetime.utcnow().isoformat(),
                    "analysis_focus": "pricing_strategy"
                }
            }

            logger.info(f"Pricing strategy report generated for ASIN: {main_product.get('asin')}")
            return report

        except Exception as e:
            logger.error(f"Failed to generate pricing strategy report: {e}")
            return {
                "error": str(e),
                "report_id": report_id,
                "generated_at": datetime.utcnow().isoformat()
            }
