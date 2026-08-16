"""
可选集成测试 - 需要本地 Prometheus/LLM 环境
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from datetime import datetime, timedelta


class TestRootCause:
    """根因推理测试（需要本地环境）"""
    
    def setup_method(self):
        from agents.root_cause import RootCauseAgent
        self.agent = RootCauseAgent()
    
    def test_cpu_root_cause(self):
        alert_group = {
            "group_id": "test",
            "alerts": [{
                "alertname": "HighCPUUsage",
                "service": "test-service"
            }]
        }
        
        result = self.agent.process({
            "alert_group": alert_group,
            "log_result": {"analysis_result": {}},
            "metric_result": {"metrics": {}}
        })
        
        assert result['confidence'] > 0
        assert "CPU" in result['top_hypothesis']['cause']
    
    def test_memory_root_cause(self):
        alert_group = {
            "group_id": "test",
            "alerts": [{
                "alertname": "OutOfMemory",
                "service": "test-service"
            }]
        }
        
        result = self.agent.process({
            "alert_group": alert_group,
            "log_result": {"analysis_result": {}},
            "metric_result": {"metrics": {}}
        })
        
        assert result['confidence'] > 0
        assert "内存" in result['top_hypothesis']['cause']


class TestMetricQuerier:
    """指标查询测试（需要本地环境）"""
    
    def setup_method(self):
        from agents.metric_querier import MetricQuerierAgent
        self.agent = MetricQuerierAgent()
    
    def test_metric_definitions(self):
        assert 'cpu_usage' in self.agent.metric_definitions
        assert 'memory_usage' in self.agent.metric_definitions
        assert 'disk_usage' in self.agent.metric_definitions
    
    def test_threshold_check(self):
        assert self.agent._check_threshold(90, 80) == True
        assert self.agent._check_threshold(50, 80) == False
        assert self.agent._check_threshold(None, 80) == False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])