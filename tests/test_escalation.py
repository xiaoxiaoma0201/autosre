"""
告警升级策略测试
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from datetime import datetime, timedelta

from agents.escalation import EscalationPolicy, EscalationLevel


class TestEscalation:
    """升级策略测试"""
    
    def setup_method(self):
        self.policy = EscalationPolicy()
    
    def test_initial_level_info(self):
        level = self.policy.get_initial_level('info')
        assert level == EscalationLevel.L1
    
    def test_initial_level_critical(self):
        level = self.policy.get_initial_level('critical')
        assert level == EscalationLevel.L3
    
    def test_should_escalate_old_alert(self):
        alert = {
            "alertname": "Test",
            "severity": "critical",
            "timestamp": (datetime.now() - timedelta(minutes=20)).isoformat()
        }
        assert self.policy.should_escalate(alert) == True
    
    def test_should_not_escalate_new_alert(self):
        alert = {
            "alertname": "Test",
            "severity": "critical",
            "timestamp": datetime.now().isoformat()
        }
        assert self.policy.should_escalate(alert) == False
    
    def test_evaluate_alert(self):
        alert = {
            "alertname": "HighCPU",
            "severity": "critical",
            "timestamp": datetime.now().isoformat()
        }
        result = self.policy.evaluate_alert(alert)
        assert result['escalation_level'] == 'L3'
        assert result['should_auto_repair'] == True
    
    def test_get_policy_summary(self):
        summary = self.policy.get_policy_summary()
        assert 'rules' in summary
        assert 'channels' in summary


if __name__ == "__main__":
    pytest.main([__file__, "-v"])