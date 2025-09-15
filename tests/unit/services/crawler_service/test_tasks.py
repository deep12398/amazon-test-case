"""爬虫任务管理API端点单元测试"""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from fastapi import HTTPException
from fastapi.testclient import TestClient

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../..')))

from amazon_tracker.services.crawler_service.main import app


class TestManualTasks:
    """手动任务端点测试"""

    def setup_method(self):
        """测试前设置"""
        self.client = TestClient(app)
        self.test_headers = {
            "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI0IiwiZW1haWwiOiJhZG1pbkBkZW1vLmNvbSIsInVzZXJuYW1lIjoiYWRtaW4iLCJ0ZW5hbnRfaWQiOiJ0ZW5hbnRfVjl3VkRZMi1mc3VpRldtdXpQaTdOdyIsImlzX3N1cGVyX2FkbWluIjpmYWxzZSwicm9sZXMiOltdLCJwZXJtaXNzaW9ucyI6W10sInNlc3Npb25faWQiOiI4MmRjYzhjNy1mZDVlLTQwMWMtOGE3Yy04ZTEwNDhmNDY1ZTciLCJleHAiOjE3NjA0NTgyNzksImlhdCI6MTc1Nzg2NjI4MCwianRpIjoiMGM4MjFjODQtZGViOC00YWRkLTk0YTAtZTlkOGVlM2ZlMmU4IiwidHlwZSI6ImFjY2VzcyJ9.iO0TofBBuWkAqv6fePacV8QF4dmZvoHsakBRgQZDVG8"
        }

    @patch('amazon_tracker.services.crawler_service.api.v1.tasks.crawl_products_batch')
    def test_batch_crawl_success(self, mock_crawl_task):
        """测试批量爬取任务成功触发"""
        # 模拟任务成功执行
        mock_result = Mock()
        mock_result.get.return_value = "Batch crawl completed successfully"
        mock_crawl_task.apply.return_value = mock_result

        response = self.client.post("/api/v1/tasks/manual/batch-crawl", headers=self.test_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "triggered successfully" in data["message"]
        assert data["task_id"] == 123
        assert data["status"] == "started"

        # 验证任务被调用
        mock_crawl_task.apply.assert_called_once()

    @patch('amazon_tracker.services.crawler_service.api.v1.tasks.crawl_products_batch')
    def test_batch_crawl_task_exception(self, mock_crawl_task):
        """测试批量爬取任务抛出异常"""
        # 模拟任务执行异常
        mock_crawl_task.apply.side_effect = Exception("Task execution failed")

        response = self.client.post("/api/v1/tasks/manual/batch-crawl", headers=self.test_headers)

        assert response.status_code == 500
        data = response.json()
        assert "Failed to trigger batch crawl task" in data["detail"]

    @patch('amazon_tracker.services.crawler_service.api.v1.tasks.crawl_products_batch')
    def test_batch_crawl_result_exception(self, mock_crawl_task):
        """测试批量爬取任务结果获取异常"""
        # 模拟任务结果获取异常
        mock_result = Mock()
        mock_result.get.side_effect = Exception("Result access failed")
        mock_crawl_task.apply.return_value = mock_result

        response = self.client.post("/api/v1/tasks/manual/batch-crawl", headers=self.test_headers)

        assert response.status_code == 500
        data = response.json()
        assert "Failed to trigger batch crawl task" in data["detail"]

    @patch('amazon_tracker.services.crawler_service.api.v1.tasks.scan_all_product_anomalies')
    def test_monitoring_success(self, mock_monitoring_task):
        """测试监控任务成功触发"""
        # 模拟任务成功执行
        mock_result = Mock()
        mock_result.get.return_value = "Monitoring completed successfully"
        mock_monitoring_task.apply.return_value = mock_result

        response = self.client.post("/api/v1/tasks/manual/monitoring", headers=self.test_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "triggered successfully" in data["message"]
        assert data["task_id"] == 456
        assert data["status"] == "started"

        # 验证任务被调用
        mock_monitoring_task.apply.assert_called_once()

    @patch('amazon_tracker.services.crawler_service.api.v1.tasks.scan_all_product_anomalies')
    def test_monitoring_task_exception(self, mock_monitoring_task):
        """测试监控任务抛出异常"""
        # 模拟任务执行异常
        mock_monitoring_task.apply.side_effect = Exception("Monitoring task failed")

        response = self.client.post("/api/v1/tasks/manual/monitoring", headers=self.test_headers)

        assert response.status_code == 500
        data = response.json()
        assert "Failed to trigger monitoring task" in data["detail"]

    @patch('amazon_tracker.services.crawler_service.api.v1.tasks.scan_all_product_anomalies')
    def test_monitoring_result_exception(self, mock_monitoring_task):
        """测试监控任务结果获取异常"""
        # 模拟任务结果获取异常
        mock_result = Mock()
        mock_result.get.side_effect = Exception("Result access failed")
        mock_monitoring_task.apply.return_value = mock_result

        response = self.client.post("/api/v1/tasks/manual/monitoring", headers=self.test_headers)

        assert response.status_code == 500
        data = response.json()
        assert "Failed to trigger monitoring task" in data["detail"]

    def test_batch_crawl_endpoint_accessibility(self):
        """测试批量爬取端点可访问性"""
        response = self.client.post("/api/v1/tasks/manual/batch-crawl", headers=self.test_headers)
        # 端点应该存在（不是404）
        assert response.status_code != 404

    def test_monitoring_endpoint_accessibility(self):
        """测试监控端点可访问性"""
        response = self.client.post("/api/v1/tasks/manual/monitoring", headers=self.test_headers)
        # 端点应该存在（不是404）
        assert response.status_code != 404