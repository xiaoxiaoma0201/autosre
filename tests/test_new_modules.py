"""
新模块单元测试 - 缓存、RBAC、预测性维护
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from datetime import datetime


class TestLRUCache:
    """缓存测试"""
    
    def setup_method(self):
        from agents.cache import LRUCache
        self.cache = LRUCache(capacity=3, ttl=60)
    
    def test_set_get(self):
        self.cache.set('key1', 'value1')
        assert self.cache.get('key1') == 'value1'
    
    def test_capacity_eviction(self):
        self.cache.set('k1', 'v1')
        self.cache.set('k2', 'v2')
        self.cache.set('k3', 'v3')
        self.cache.set('k4', 'v4')  # 淘汰 k1
        assert self.cache.get('k1') is None
        assert self.cache.get('k4') == 'v4'
    
    def test_ttl_expiry(self):
        cache = __import__('agents.cache', fromlist=['LRUCache']).LRUCache(capacity=5, ttl=0)
        cache.set('key', 'value')
        assert cache.get('key') is None  # 立即过期


class TestRBAC:
    """RBAC 权限测试"""
    
    def setup_method(self):
        from agents.rbac import RBAC, Permission
        self.rbac = RBAC()
        self.Permission = Permission
    
    def test_admin_has_all_permissions(self):
        assert self.rbac.check_permission('autosre-admin-2024', self.Permission.MANAGE) == True
        assert self.rbac.check_permission('autosre-admin-2024', self.Permission.EXECUTE) == True
    
    def test_viewer_only_view(self):
        assert self.rbac.check_permission('autosre-viewer-2024', self.Permission.VIEW) == True
        assert self.rbac.check_permission('autosre-viewer-2024', self.Permission.EXECUTE) == False
    
    def test_invalid_key(self):
        assert self.rbac.check_permission('invalid-key', self.Permission.VIEW) == False
    
    def test_add_user(self):
        from agents.rbac import Role
        self.rbac.add_user('testuser', Role.VIEWER, 'test-key-123')
        assert self.rbac.check_permission('test-key-123', self.Permission.VIEW) == True


class TestPredictiveAgent:
    """预测性维护测试"""
    
    def test_empty_history(self):
        from agents.predictive_agent import PredictiveAgent
        agent = PredictiveAgent()
        result = agent.process({})
        assert 'predictions' in result
    
    def test_risk_level_low(self):
        from agents.predictive_agent import PredictiveAgent
        agent = PredictiveAgent()
        result = agent._calculate_risk_level([])
        assert result == 'low'


if __name__ == "__main__":
    pytest.main([__file__, "-v"])