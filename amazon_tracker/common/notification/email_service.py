"""邮件通知服务"""

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Optional

from ..config.settings import get_settings

logger = logging.getLogger(__name__)


class EmailNotifier:
    """邮件通知服务"""

    def __init__(self):
        self.settings = get_settings()
        self.smtp_host = getattr(self.settings, "SMTP_HOST", "smtp.gmail.com")
        self.smtp_port = getattr(self.settings, "SMTP_PORT", 587)
        self.smtp_user = getattr(self.settings, "SMTP_USER", None)
        self.smtp_password = getattr(self.settings, "SMTP_PASSWORD", None)
        self.from_email = getattr(self.settings, "FROM_EMAIL", self.smtp_user)
        self.notification_email = getattr(
            self.settings, "NOTIFICATION_EMAIL", self.smtp_user
        )

    def _create_smtp_connection(self) -> smtplib.SMTP:
        """创建SMTP连接"""
        try:
            server = smtplib.SMTP(self.smtp_host, self.smtp_port)
            server.starttls()
            if self.smtp_user and self.smtp_password:
                server.login(self.smtp_user, self.smtp_password)
            return server
        except Exception as e:
            logger.error(f"Failed to create SMTP connection: {e}")
            raise

    def send_email(
        self,
        to_email: str,
        subject: str,
        html_body: str,
        text_body: Optional[str] = None,
    ) -> bool:
        """发送邮件

        Args:
            to_email: 收件人邮箱
            subject: 邮件主题
            html_body: HTML格式邮件内容
            text_body: 纯文本格式邮件内容

        Returns:
            发送是否成功
        """
        if not self.smtp_user or not self.smtp_password:
            logger.warning("SMTP credentials not configured, skipping email send")
            return False

        try:
            # 创建邮件
            msg = MIMEMultipart("alternative")
            msg["From"] = self.from_email
            msg["To"] = to_email
            msg["Subject"] = subject

            # 添加纯文本内容
            if text_body:
                text_part = MIMEText(text_body, "plain", "utf-8")
                msg.attach(text_part)

            # 添加HTML内容
            html_part = MIMEText(html_body, "html", "utf-8")
            msg.attach(html_part)

            # 发送邮件
            with self._create_smtp_connection() as server:
                server.send_message(msg)

            logger.info(f"Email sent successfully to {to_email}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}")
            return False

    def send_price_alert(self, anomaly_data: dict[str, Any]) -> bool:
        """发送价格异常预警邮件

        Args:
            anomaly_data: 价格异常数据

        Returns:
            发送是否成功
        """
        if not anomaly_data.get("is_anomaly"):
            return False

        product_asin = anomaly_data.get("product_asin", "Unknown")
        product_title = anomaly_data.get("product_title", "Unknown Product")
        current_price = anomaly_data.get("current_price", 0)
        average_price = anomaly_data.get("average_price", 0)
        change_percent = anomaly_data.get("change_percent", 0)
        direction = anomaly_data.get("direction", "unknown")

        # 邮件主题
        subject = (
            f"🚨 价格预警: {product_asin} - {direction.title()} {change_percent:.1f}%"
        )

        # HTML邮件内容
        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background-color: #f8f9fa; padding: 20px; border-radius: 8px;">
                <h2 style="color: #dc3545; margin-top: 0;">🚨 产品价格异常预警</h2>

                <div style="background-color: white; padding: 15px; border-radius: 5px; margin: 15px 0;">
                    <h3 style="color: #333; margin-top: 0;">产品信息</h3>
                    <p><strong>ASIN:</strong> {product_asin}</p>
                    <p><strong>标题:</strong> {product_title}</p>
                    <p><strong>Amazon链接:</strong>
                        <a href="https://amazon.com/dp/{product_asin}" target="_blank">
                            查看产品页面
                        </a>
                    </p>
                </div>

                <div style="background-color: {'#fff3cd' if direction == 'increase' else '#d1ecf1'};
                           padding: 15px; border-radius: 5px; margin: 15px 0;
                           border-left: 4px solid {'#ffc107' if direction == 'increase' else '#17a2b8'};">
                    <h3 style="color: #333; margin-top: 0;">价格变化详情</h3>
                    <p><strong>当前价格:</strong> ${current_price:.2f}</p>
                    <p><strong>平均价格:</strong> ${average_price:.2f}</p>
                    <p><strong>变化幅度:</strong>
                        <span style="color: {'#dc3545' if direction == 'increase' else '#28a745'}; font-weight: bold;">
                            {direction.title()} {change_percent:.1f}%
                        </span>
                    </p>
                    <p><strong>预警阈值:</strong> 10%</p>
                </div>

                <div style="background-color: white; padding: 15px; border-radius: 5px; margin: 15px 0;">
                    <h3 style="color: #333; margin-top: 0;">建议动作</h3>
                    <ul>
                        {'<li>价格上涨超过阈值，建议检查竞品价格调整策略</li>' if direction == 'increase'
                         else '<li>价格下降超过阈值，可能影响利润率或市场表现</li>'}
                        <li>登录系统查看详细的价格历史趋势</li>
                        <li>考虑调整价格策略或库存管理</li>
                    </ul>
                </div>

                <div style="text-align: center; margin-top: 20px; color: #6c757d; font-size: 12px;">
                    <p>本邮件由Amazon产品追踪系统自动发送</p>
                    <p>检测时间: {anomaly_data.get('check_time', '')}</p>
                </div>
            </div>
        </body>
        </html>
        """

        # 纯文本内容
        text_body = f"""
        产品价格异常预警

        产品信息:
        ASIN: {product_asin}
        标题: {product_title}

        价格变化:
        当前价格: ${current_price:.2f}
        平均价格: ${average_price:.2f}
        变化幅度: {direction.title()} {change_percent:.1f}%

        请登录系统查看详细信息。
        """

        return self.send_email(
            to_email=self.notification_email,
            subject=subject,
            html_body=html_body,
            text_body=text_body,
        )

    def send_bsr_alert(self, anomaly_data: dict[str, Any]) -> bool:
        """发送BSR排名异常预警邮件

        Args:
            anomaly_data: BSR异常数据

        Returns:
            发送是否成功
        """
        if not anomaly_data.get("is_anomaly"):
            return False

        product_asin = anomaly_data.get("product_asin", "Unknown")
        product_title = anomaly_data.get("product_title", "Unknown Product")
        current_rank = anomaly_data.get("current_rank", 0)
        average_rank = anomaly_data.get("average_rank", 0)
        change_percent = anomaly_data.get("change_percent", 0)
        direction = anomaly_data.get("direction", "unknown")

        # 邮件主题
        subject = (
            f"📊 排名预警: {product_asin} - {direction.title()} {change_percent:.1f}%"
        )

        # HTML邮件内容
        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background-color: #f8f9fa; padding: 20px; border-radius: 8px;">
                <h2 style="color: #fd7e14; margin-top: 0;">📊 产品排名异常预警</h2>

                <div style="background-color: white; padding: 15px; border-radius: 5px; margin: 15px 0;">
                    <h3 style="color: #333; margin-top: 0;">产品信息</h3>
                    <p><strong>ASIN:</strong> {product_asin}</p>
                    <p><strong>标题:</strong> {product_title}</p>
                    <p><strong>Amazon链接:</strong>
                        <a href="https://amazon.com/dp/{product_asin}" target="_blank">
                            查看产品页面
                        </a>
                    </p>
                </div>

                <div style="background-color: {'#d1ecf1' if direction == 'better' else '#f8d7da'};
                           padding: 15px; border-radius: 5px; margin: 15px 0;
                           border-left: 4px solid {'#17a2b8' if direction == 'better' else '#dc3545'};">
                    <h3 style="color: #333; margin-top: 0;">BSR排名变化详情</h3>
                    <p><strong>当前排名:</strong> #{current_rank:,}</p>
                    <p><strong>平均排名:</strong> #{average_rank:,}</p>
                    <p><strong>变化幅度:</strong>
                        <span style="color: {'#28a745' if direction == 'better' else '#dc3545'}; font-weight: bold;">
                            {direction.title()} {change_percent:.1f}%
                        </span>
                    </p>
                    <p><strong>预警阈值:</strong> 30%</p>
                </div>

                <div style="background-color: white; padding: 15px; border-radius: 5px; margin: 15px 0;">
                    <h3 style="color: #333; margin-top: 0;">建议动作</h3>
                    <ul>
                        {'<li>排名提升显著，建议保持当前策略</li><li>考虑加大营销投入巩固优势</li>' if direction == 'better'
                         else '<li>排名下降超过阈值，需要分析原因</li><li>检查库存、价格、评价等关键指标</li>'}
                        <li>登录系统查看详细的排名趋势分析</li>
                        <li>对比竞品表现，调整运营策略</li>
                    </ul>
                </div>

                <div style="text-align: center; margin-top: 20px; color: #6c757d; font-size: 12px;">
                    <p>本邮件由Amazon产品追踪系统自动发送</p>
                    <p>检测时间: {anomaly_data.get('check_time', '')}</p>
                </div>
            </div>
        </body>
        </html>
        """

        # 纯文本内容
        text_body = f"""
        产品BSR排名异常预警

        产品信息:
        ASIN: {product_asin}
        标题: {product_title}

        排名变化:
        当前排名: #{current_rank:,}
        平均排名: #{average_rank:,}
        变化幅度: {direction.title()} {change_percent:.1f}%

        请登录系统查看详细信息。
        """

        return self.send_email(
            to_email=self.notification_email,
            subject=subject,
            html_body=html_body,
            text_body=text_body,
        )

    def send_buy_box_alert(self, anomaly_data: dict[str, Any]) -> bool:
        """发送Buy Box价格异常预警邮件

        Args:
            anomaly_data: Buy Box异常数据

        Returns:
            发送是否成功
        """
        if not anomaly_data.get("is_anomaly"):
            return False

        product_asin = anomaly_data.get("product_asin", "Unknown")
        product_title = anomaly_data.get("product_title", "Unknown Product")
        current_buy_box_price = anomaly_data.get("current_buy_box_price", 0)
        average_buy_box_price = anomaly_data.get("average_buy_box_price", 0)
        change_percent = anomaly_data.get("change_percent", 0)
        direction = anomaly_data.get("direction", "unknown")

        # 邮件主题
        subject = f"🛒 Buy Box价格预警: {product_asin} - {direction.title()} {change_percent:.1f}%"

        # HTML邮件内容
        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background-color: #f8f9fa; padding: 20px; border-radius: 8px;">
                <h2 style="color: #6f42c1; margin-top: 0;">🛒 Buy Box价格异常预警</h2>

                <div style="background-color: white; padding: 15px; border-radius: 5px; margin: 15px 0;">
                    <h3 style="color: #333; margin-top: 0;">产品信息</h3>
                    <p><strong>ASIN:</strong> {product_asin}</p>
                    <p><strong>标题:</strong> {product_title}</p>
                    <p><strong>Amazon链接:</strong>
                        <a href="https://amazon.com/dp/{product_asin}" target="_blank">
                            查看产品页面
                        </a>
                    </p>
                </div>

                <div style="background-color: {'#d1ecf1' if direction == 'decrease' else '#f8d7da'};
                           padding: 15px; border-radius: 5px; margin: 15px 0;
                           border-left: 4px solid {'#17a2b8' if direction == 'decrease' else '#dc3545'};">
                    <h3 style="color: #333; margin-top: 0;">Buy Box价格变化详情</h3>
                    <p><strong>当前Buy Box价格:</strong> ${current_buy_box_price:.2f}</p>
                    <p><strong>平均Buy Box价格:</strong> ${average_buy_box_price:.2f}</p>
                    <p><strong>变化幅度:</strong>
                        <span style="color: {'#17a2b8' if direction == 'decrease' else '#dc3545'}; font-weight: bold;">
                            {direction.title()} {change_percent:.1f}%
                        </span>
                    </p>
                    <p><strong>价格差异:</strong> ${abs(current_buy_box_price - average_buy_box_price):.2f}</p>
                    <p><strong>触发阈值:</strong> {anomaly_data.get('threshold', 15)}%</p>
                    <p><strong>检测时间:</strong> {anomaly_data.get('check_time', 'Unknown')}</p>
                </div>

                <div style="background-color: #fff3cd; padding: 15px; border-radius: 5px; margin: 15px 0;
                           border-left: 4px solid #ffc107;">
                    <h4 style="color: #856404; margin-top: 0;">⚠️ 建议采取的行动</h4>
                    <ul style="color: #856404; margin: 0; padding-left: 20px;">
                        <li>检查竞争对手的价格策略调整</li>
                        <li>确认产品库存状态和可用性</li>
                        <li>考虑调整产品价格以保持竞争力</li>
                        <li>监控Buy Box获得情况</li>
                        <li>分析其他卖家的活动</li>
                    </ul>
                </div>

                <div style="text-align: center; margin-top: 20px;">
                    <p style="color: #6c757d; font-size: 12px;">
                        本邮件由Amazon产品监控系统自动发送 |
                        <a href="https://amazon.com/dp/{product_asin}" target="_blank">查看产品详情</a>
                    </p>
                </div>
            </div>
        </body>
        </html>
        """

        # 纯文本内容
        text_body = f"""
        Buy Box价格异常预警

        产品信息:
        ASIN: {product_asin}
        标题: {product_title}

        Buy Box价格变化:
        当前Buy Box价格: ${current_buy_box_price:.2f}
        平均Buy Box价格: ${average_buy_box_price:.2f}
        变化幅度: {direction.title()} {change_percent:.1f}%

        建议采取行动:
        - 检查竞争对手价格策略
        - 确认产品库存状态
        - 考虑调整价格策略
        - 监控Buy Box获得情况

        请登录系统查看详细信息。
        """

        return self.send_email(
            to_email=self.notification_email,
            subject=subject,
            html_body=html_body,
            text_body=text_body,
        )

    def send_category_anomalies_report(
        self, category_name: str, anomalies: list[dict]
    ) -> bool:
        """发送品类异常汇总报告

        Args:
            category_name: 品类名称
            anomalies: 异常产品列表

        Returns:
            发送是否成功
        """
        if not anomalies:
            return False

        # 统计异常类型
        total_products = len(anomalies)
        price_anomalies = sum(
            1 for a in anomalies if a.get("price_anomaly", {}).get("is_anomaly")
        )
        bsr_anomalies = sum(
            1 for a in anomalies if a.get("bsr_anomaly", {}).get("is_anomaly")
        )
        buy_box_anomalies = sum(
            1 for a in anomalies if a.get("buy_box_anomaly", {}).get("is_anomaly")
        )
        rating_anomalies = sum(
            1 for a in anomalies if a.get("rating_anomaly", {}).get("is_anomaly")
        )

        # 邮件主题
        subject = f"📊 品类异常汇总报告 - {category_name} ({total_products}个异常产品)"

        # 构建产品异常详情
        product_details_html = ""
        product_details_text = ""

        for i, anomaly in enumerate(anomalies[:10], 1):  # 只显示前10个
            product_asin = anomaly.get("product_asin", "Unknown")
            product_title = anomaly.get("product_title", "Unknown Product")[:50]

            anomaly_types = []
            if anomaly.get("price_anomaly", {}).get("is_anomaly"):
                price_data = anomaly["price_anomaly"]
                anomaly_types.append(
                    f"价格{price_data.get('direction', '')} {price_data.get('change_percent', 0):.1f}%"
                )

            if anomaly.get("buy_box_anomaly", {}).get("is_anomaly"):
                bb_data = anomaly["buy_box_anomaly"]
                anomaly_types.append(
                    f"Buy Box{bb_data.get('direction', '')} {bb_data.get('change_percent', 0):.1f}%"
                )

            if anomaly.get("bsr_anomaly", {}).get("is_anomaly"):
                bsr_data = anomaly["bsr_anomaly"]
                anomaly_types.append(
                    f"排名{bsr_data.get('direction', '')} {bsr_data.get('change_percent', 0):.1f}%"
                )

            if anomaly.get("rating_anomaly", {}).get("is_anomaly"):
                rating_data = anomaly["rating_anomaly"]
                anomaly_types.append(
                    f"评分{rating_data.get('direction', '')} {rating_data.get('change', 0):.1f}分"
                )

            anomaly_summary = ", ".join(anomaly_types)

            product_details_html += f"""
            <tr style="border-bottom: 1px solid #dee2e6;">
                <td style="padding: 8px;">{i}</td>
                <td style="padding: 8px;">
                    <a href="https://amazon.com/dp/{product_asin}" target="_blank">{product_asin}</a>
                </td>
                <td style="padding: 8px;">{product_title}...</td>
                <td style="padding: 8px; font-size: 12px;">{anomaly_summary}</td>
            </tr>
            """

            product_details_text += (
                f"{i}. {product_asin} - {product_title}... ({anomaly_summary})\n"
            )

        # HTML邮件内容
        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 700px; margin: 0 auto;">
            <div style="background-color: #f8f9fa; padding: 20px; border-radius: 8px;">
                <h2 style="color: #495057; margin-top: 0;">📊 品类异常汇总报告</h2>
                <h3 style="color: #6f42c1;">{category_name}</h3>

                <div style="background-color: white; padding: 15px; border-radius: 5px; margin: 15px 0;">
                    <h3 style="color: #333; margin-top: 0;">异常统计概览</h3>
                    <div style="display: flex; flex-wrap: wrap; gap: 10px;">
                        <div style="background-color: #e9ecef; padding: 10px; border-radius: 5px; flex: 1; min-width: 120px; text-align: center;">
                            <div style="font-size: 20px; font-weight: bold; color: #495057;">{total_products}</div>
                            <div style="font-size: 12px; color: #6c757d;">异常产品总数</div>
                        </div>
                        <div style="background-color: #f8d7da; padding: 10px; border-radius: 5px; flex: 1; min-width: 120px; text-align: center;">
                            <div style="font-size: 20px; font-weight: bold; color: #721c24;">{price_anomalies}</div>
                            <div style="font-size: 12px; color: #721c24;">价格异常</div>
                        </div>
                        <div style="background-color: #d1ecf1; padding: 10px; border-radius: 5px; flex: 1; min-width: 120px; text-align: center;">
                            <div style="font-size: 20px; font-weight: bold; color: #0c5460;">{buy_box_anomalies}</div>
                            <div style="font-size: 12px; color: #0c5460;">Buy Box异常</div>
                        </div>
                        <div style="background-color: #fff3cd; padding: 10px; border-radius: 5px; flex: 1; min-width: 120px; text-align: center;">
                            <div style="font-size: 20px; font-weight: bold; color: #856404;">{bsr_anomalies}</div>
                            <div style="font-size: 12px; color: #856404;">排名异常</div>
                        </div>
                        <div style="background-color: #d4edda; padding: 10px; border-radius: 5px; flex: 1; min-width: 120px; text-align: center;">
                            <div style="font-size: 20px; font-weight: bold; color: #155724;">{rating_anomalies}</div>
                            <div style="font-size: 12px; color: #155724;">评分异常</div>
                        </div>
                    </div>
                </div>

                <div style="background-color: white; padding: 15px; border-radius: 5px; margin: 15px 0;">
                    <h3 style="color: #333; margin-top: 0;">异常产品详情</h3>
                    <table style="width: 100%; border-collapse: collapse;">
                        <thead>
                            <tr style="background-color: #f8f9fa;">
                                <th style="padding: 8px; text-align: left; border-bottom: 2px solid #dee2e6;">#</th>
                                <th style="padding: 8px; text-align: left; border-bottom: 2px solid #dee2e6;">ASIN</th>
                                <th style="padding: 8px; text-align: left; border-bottom: 2px solid #dee2e6;">产品标题</th>
                                <th style="padding: 8px; text-align: left; border-bottom: 2px solid #dee2e6;">异常类型</th>
                            </tr>
                        </thead>
                        <tbody>
                            {product_details_html}
                        </tbody>
                    </table>
                    {f'<p style="color: #6c757d; font-size: 12px; margin-top: 10px;">*仅显示前10个异常产品，共{total_products}个</p>' if total_products > 10 else ''}
                </div>

                <div style="background-color: #fff3cd; padding: 15px; border-radius: 5px; margin: 15px 0;
                           border-left: 4px solid #ffc107;">
                    <h4 style="color: #856404; margin-top: 0;">🎯 建议采取的行动</h4>
                    <ul style="color: #856404; margin: 0; padding-left: 20px;">
                        <li>重点关注价格和Buy Box异常产品，及时调整定价策略</li>
                        <li>分析排名下降产品，检查库存和广告投放情况</li>
                        <li>关注评分变化，查看最新客户评价和反馈</li>
                        <li>对比竞争对手在该品类的表现和策略调整</li>
                        <li>考虑增加对异常产品的监控频率</li>
                    </ul>
                </div>

                <div style="text-align: center; margin-top: 20px;">
                    <p style="color: #6c757d; font-size: 12px;">
                        本报告由Amazon品类监控系统自动生成 |
                        检测时间: {anomalies[0].get('check_time', 'Unknown') if anomalies else 'Unknown'}
                    </p>
                </div>
            </div>
        </body>
        </html>
        """

        # 纯文本内容
        text_body = f"""
        品类异常汇总报告 - {category_name}

        异常统计概览:
        - 异常产品总数: {total_products}
        - 价格异常: {price_anomalies}
        - Buy Box异常: {buy_box_anomalies}
        - 排名异常: {bsr_anomalies}
        - 评分异常: {rating_anomalies}

        异常产品详情:
        {product_details_text}

        建议采取行动:
        - 重点关注价格和Buy Box异常产品
        - 分析排名下降产品的原因
        - 关注评分变化和客户反馈
        - 对比竞争对手策略
        - 增加异常产品监控频率

        请登录系统查看完整详情。
        """

        return self.send_email(
            to_email=self.notification_email,
            subject=subject,
            html_body=html_body,
            text_body=text_body,
        )

    def send_multiple_alerts(self, anomaly_results: dict[str, Any]) -> dict[str, bool]:
        """发送多个异常预警邮件

        Args:
            anomaly_results: 异常检测结果（包含价格和BSR异常）

        Returns:
            各类型预警的发送结果
        """
        results = {}

        # 发送价格预警
        price_anomaly = anomaly_results.get("price_anomaly", {})
        if price_anomaly.get("is_anomaly"):
            results["price_alert"] = self.send_price_alert(price_anomaly)

        # 发送BSR预警
        bsr_anomaly = anomaly_results.get("bsr_anomaly", {})
        if bsr_anomaly.get("is_anomaly"):
            results["bsr_alert"] = self.send_bsr_alert(bsr_anomaly)

        return results

    def send_rank_alert(self, alert_data: dict[str, Any]) -> bool:
        """发送排名变化预警邮件 - 适配监控任务

        Args:
            alert_data: 排名变化数据

        Returns:
            发送是否成功
        """
        # 转换为BSR预警格式
        bsr_anomaly_data = {
            "is_anomaly": True,
            "product_asin": alert_data.get("asin"),
            "product_title": alert_data.get("title"),
            "current_rank": alert_data.get("new_rank"),
            "average_rank": alert_data.get("old_rank"), 
            "change_percent": alert_data.get("change_percent"),
            "direction": "worse" if alert_data.get("new_rank") > alert_data.get("old_rank") else "better",
            "check_time": alert_data.get("timestamp", ""),
        }
        
        return self.send_bsr_alert(bsr_anomaly_data)

    def send_price_change_alert(self, alert_data: dict[str, Any]) -> bool:
        """发送价格变化预警邮件 - 适配监控任务

        Args:
            alert_data: 价格变化数据

        Returns:
            发送是否成功
        """
        # 转换为价格预警格式
        price_anomaly_data = {
            "is_anomaly": True,
            "product_asin": alert_data.get("asin"),
            "product_title": alert_data.get("title"),
            "current_price": alert_data.get("new_price"),
            "average_price": alert_data.get("old_price"),
            "change_percent": alert_data.get("change_percent"),
            "direction": "increase" if alert_data.get("new_price") > alert_data.get("old_price") else "decrease",
            "check_time": alert_data.get("timestamp", ""),
        }
        
        return self.send_price_alert(price_anomaly_data)
