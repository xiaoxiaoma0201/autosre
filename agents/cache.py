"""
缓存模块 - 提升查询性能
"""
import time
from typing import Dict, Any, Optional
from collections import OrderedDict
from loguru import logger


class LRUCache:
    """LRU 缓存"""
    
    def __init__(self, capacity: int = 100, ttl: int = 60):
        self.capacity = capacity
        self.ttl = ttl  # 秒
        self._cache = OrderedDict()
        
    def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        if key not in self._cache:
            return None
        
        value, timestamp = self._cache[key]
        
        # 检查是否过期
        if time.time() - timestamp > self.ttl:
            del self._cache[key]
            return None
        
        # 移动到末尾（最近使用）
        self._cache.move_to_end(key)
        return value
    
    def set(self, key: str, value: Any):
        """设置缓存"""
        if key in self._cache:
            self._cache.move_to_end(key)
        
        self._cache[key] = (value, time.time())
        
        # 淘汰最久未使用的
        if len(self._cache) > self.capacity:
            self._cache.popitem(last=False)
    
    def clear(self):
        """清空缓存"""
        self._cache.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        return {
            "size": len(self._cache),
            "capacity": self.capacity,
            "ttl": self.ttl
        }


# 全局缓存实例
metric_cache = LRUCache(capacity=50, ttl=30)  # 指标缓存30秒
log_cache = LRUCache(capacity=20, ttl=60)     # 日志缓存60秒