"""Redis缓存管理器"""

import json
import logging
from collections.abc import Callable
from functools import wraps
from typing import Any, Optional, Union

import redis
from redis import Redis

from ..config.settings import get_settings

logger = logging.getLogger(__name__)


class RedisCache:
    """Redis缓存管理器"""

    def __init__(self, redis_url: Optional[str] = None):
        settings = get_settings()
        self.redis_url = redis_url or settings.REDIS_URL
        self._client: Optional[Redis] = None

        # 缓存时间配置（秒）
        self.TTL_30_MINUTES = 30 * 60
        self.TTL_2_HOURS = 2 * 60 * 60
        self.TTL_6_HOURS = 6 * 60 * 60
        self.TTL_24_HOURS = 24 * 60 * 60
        self.TTL_48_HOURS = 48 * 60 * 60
        self.TTL_7_DAYS = 7 * 24 * 60 * 60

    @property
    def client(self) -> Redis:
        """获取Redis客户端"""
        if self._client is None:
            try:
                self._client = redis.from_url(
                    self.redis_url,
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=5,
                )
                # 测试连接
                self._client.ping()
                logger.info("Redis connection established successfully")
            except Exception as e:
                logger.error(f"Failed to connect to Redis: {e}")
                raise
        return self._client

    def _serialize(self, data: Any) -> str:
        """序列化数据"""
        try:
            if isinstance(data, (dict, list, tuple)):
                return json.dumps(data, ensure_ascii=False, default=str)
            elif isinstance(data, (int, float, str, bool)):
                return str(data)
            else:
                return json.dumps(data, ensure_ascii=False, default=str)
        except Exception as e:
            logger.error(f"Failed to serialize data: {e}")
            return str(data)

    def _deserialize(self, data: str) -> Any:
        """反序列化数据"""
        try:
            # 尝试解析为JSON
            return json.loads(data)
        except (json.JSONDecodeError, TypeError):
            # 如果不是JSON，返回原始字符串
            return data

    def set(
        self, key: str, value: Any, ttl: int = None, prefix: str = "amazon_tracker"
    ) -> bool:
        """设置缓存

        Args:
            key: 缓存键
            value: 缓存值
            ttl: 过期时间（秒），默认24小时
            prefix: 键前缀

        Returns:
            是否设置成功
        """
        try:
            full_key = f"{prefix}:{key}"
            serialized_value = self._serialize(value)
            ttl = ttl or self.TTL_24_HOURS

            result = self.client.setex(full_key, ttl, serialized_value)

            if result:
                logger.debug(f"Cache set: {full_key} (TTL: {ttl}s)")
            return result

        except Exception as e:
            logger.error(f"Failed to set cache {key}: {e}")
            return False

    def get(self, key: str, prefix: str = "amazon_tracker") -> Any:
        """获取缓存

        Args:
            key: 缓存键
            prefix: 键前缀

        Returns:
            缓存值，不存在时返回None
        """
        try:
            full_key = f"{prefix}:{key}"
            value = self.client.get(full_key)

            if value is None:
                logger.debug(f"Cache miss: {full_key}")
                return None

            logger.debug(f"Cache hit: {full_key}")
            return self._deserialize(value)

        except Exception as e:
            logger.error(f"Failed to get cache {key}: {e}")
            return None

    def delete(self, key: str, prefix: str = "amazon_tracker") -> bool:
        """删除缓存

        Args:
            key: 缓存键
            prefix: 键前缀

        Returns:
            是否删除成功
        """
        try:
            full_key = f"{prefix}:{key}"
            result = self.client.delete(full_key)

            if result:
                logger.debug(f"Cache deleted: {full_key}")
            return bool(result)

        except Exception as e:
            logger.error(f"Failed to delete cache {key}: {e}")
            return False

    def exists(self, key: str, prefix: str = "amazon_tracker") -> bool:
        """检查缓存是否存在

        Args:
            key: 缓存键
            prefix: 键前缀

        Returns:
            是否存在
        """
        try:
            full_key = f"{prefix}:{key}"
            return bool(self.client.exists(full_key))
        except Exception as e:
            logger.error(f"Failed to check cache existence {key}: {e}")
            return False

    def get_ttl(self, key: str, prefix: str = "amazon_tracker") -> int:
        """获取缓存剩余过期时间

        Args:
            key: 缓存键
            prefix: 键前缀

        Returns:
            剩余秒数，-1表示永不过期，-2表示不存在
        """
        try:
            full_key = f"{prefix}:{key}"
            return self.client.ttl(full_key)
        except Exception as e:
            logger.error(f"Failed to get TTL for {key}: {e}")
            return -2

    def clear_pattern(self, pattern: str, prefix: str = "amazon_tracker") -> int:
        """删除匹配模式的所有缓存

        Args:
            pattern: 模式（支持通配符*）
            prefix: 键前缀

        Returns:
            删除的键数量
        """
        try:
            full_pattern = f"{prefix}:{pattern}"
            keys = self.client.keys(full_pattern)

            if keys:
                deleted = self.client.delete(*keys)
                logger.info(f"Deleted {deleted} keys matching pattern: {full_pattern}")
                return deleted
            return 0

        except Exception as e:
            logger.error(f"Failed to clear pattern {pattern}: {e}")
            return 0

    # 专门的缓存方法
    def cache_product_data(
        self, product_id: Union[int, str], data: dict[str, Any], ttl: int = None
    ) -> bool:
        """缓存产品数据

        Args:
            product_id: 产品ID
            data: 产品数据
            ttl: 过期时间，默认24小时

        Returns:
            是否缓存成功
        """
        key = f"product:{product_id}"
        ttl = ttl or self.TTL_24_HOURS
        return self.set(key, data, ttl, prefix="products")

    def get_product_data(self, product_id: Union[int, str]) -> Optional[dict[str, Any]]:
        """获取产品数据缓存

        Args:
            product_id: 产品ID

        Returns:
            产品数据或None
        """
        key = f"product:{product_id}"
        return self.get(key, prefix="products")

    def cache_analysis_report(
        self, report_id: str, data: dict[str, Any], ttl: int = None
    ) -> bool:
        """缓存分析报告

        Args:
            report_id: 报告ID
            data: 报告数据
            ttl: 过期时间，默认48小时

        Returns:
            是否缓存成功
        """
        key = f"report:{report_id}"
        ttl = ttl or self.TTL_48_HOURS
        return self.set(key, data, ttl, prefix="reports")

    def get_analysis_report(self, report_id: str) -> Optional[dict[str, Any]]:
        """获取分析报告缓存

        Args:
            report_id: 报告ID

        Returns:
            报告数据或None
        """
        key = f"report:{report_id}"
        return self.get(key, prefix="reports")

    def cache_api_response(
        self, endpoint: str, params: dict[str, Any], response: Any, ttl: int = None
    ) -> bool:
        """缓存API响应

        Args:
            endpoint: API端点
            params: 请求参数
            response: 响应数据
            ttl: 过期时间，默认30分钟

        Returns:
            是否缓存成功
        """
        # 创建缓存键
        params_str = json.dumps(params, sort_keys=True, ensure_ascii=False)
        key = f"api:{endpoint}:{hash(params_str)}"
        ttl = ttl or self.TTL_30_MINUTES
        return self.set(key, response, ttl, prefix="api_cache")

    def get_api_response(self, endpoint: str, params: dict[str, Any]) -> Any:
        """获取API响应缓存

        Args:
            endpoint: API端点
            params: 请求参数

        Returns:
            缓存的响应数据或None
        """
        params_str = json.dumps(params, sort_keys=True, ensure_ascii=False)
        key = f"api:{endpoint}:{hash(params_str)}"
        return self.get(key, prefix="api_cache")

    def cache_stats(self) -> dict[str, Any]:
        """获取缓存统计信息"""
        try:
            info = self.client.info()
            return {
                "connected_clients": info.get("connected_clients", 0),
                "used_memory": info.get("used_memory", 0),
                "used_memory_human": info.get("used_memory_human", "0B"),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0),
                "hit_rate": info.get("keyspace_hits", 0)
                / max(info.get("keyspace_hits", 0) + info.get("keyspace_misses", 0), 1)
                * 100,
            }
        except Exception as e:
            logger.error(f"Failed to get cache stats: {e}")
            return {}


# 单例实例
cache_manager = RedisCache()


def cache_result(
    ttl: int = 30 * 60,
    prefix: str = "func_cache",
    key_generator: Optional[Callable] = None,
):
    """缓存函数结果的装饰器

    Args:
        ttl: 缓存时间（秒）
        prefix: 缓存键前缀
        key_generator: 自定义键生成函数
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # 生成缓存键
            if key_generator:
                cache_key = key_generator(*args, **kwargs)
            else:
                args_str = json.dumps(args, sort_keys=True, default=str)
                kwargs_str = json.dumps(kwargs, sort_keys=True, default=str)
                cache_key = f"{func.__name__}:{hash(args_str + kwargs_str)}"

            # 尝试从缓存获取
            cached_result = cache_manager.get(cache_key, prefix)
            if cached_result is not None:
                logger.debug(f"Cache hit for {func.__name__}")
                return cached_result

            # 执行函数并缓存结果
            result = await func(*args, **kwargs)
            cache_manager.set(cache_key, result, ttl, prefix)
            logger.debug(f"Cache set for {func.__name__}")

            return result

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # 生成缓存键
            if key_generator:
                cache_key = key_generator(*args, **kwargs)
            else:
                args_str = json.dumps(args, sort_keys=True, default=str)
                kwargs_str = json.dumps(kwargs, sort_keys=True, default=str)
                cache_key = f"{func.__name__}:{hash(args_str + kwargs_str)}"

            # 尝试从缓存获取
            cached_result = cache_manager.get(cache_key, prefix)
            if cached_result is not None:
                logger.debug(f"Cache hit for {func.__name__}")
                return cached_result

            # 执行函数并缓存结果
            result = func(*args, **kwargs)
            cache_manager.set(cache_key, result, ttl, prefix)
            logger.debug(f"Cache set for {func.__name__}")

            return result

        # 检查是否是异步函数
        import asyncio

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator
