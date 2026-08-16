"""
Agent 单元测试 - 只测试不依赖外部服务的功能
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from datetime import datetime, timedelta

from agents.alert_convergence import AlertConvergenceAgent
from agents.message_bus import MessageBus, AgentMessage, MessageType


class TestMessageBus:
    """消息总线测试"""
    
    def test_publish(self):
        bus = MessageBus()
        msg = AgentMessage(msg_type=MessageType.HEARTBEAT, sender="test")
        bus.publish(msg)
        assert len(bus.messages) == 1
    
    def test_subscribe(self):
        bus = MessageBus()
        received = []
        bus.subscribe(MessageType.ALERT_CONVERGED, lambda m: received.append(m))
        msg = AgentMessage(msg_type=MessageType.ALERT_CONVERGED, sender="test")
        bus.publish(msg)
        assert len(received) == 1


class TestAlertConvergence:
    """告警收敛测试"""
    
    def setup_method(self):
        self.agent = AlertConvergenceAgent()
    
    def test_empty_alerts(self):
        result = self.agent.process({"alerts": []})
        assert result['total_alerts'] == 0
        assert result['alert_groups'] == []
    
    def test_single_alert(self):
        alerts = [{
            "alertname": "TestAlert",
            "service": "test-service",
            "instance": "instance-1",
            "severity": "warning",
            "timestamp": datetime.now().isoformat()
        }]
        result = self.agent.process({"alerts": alerts})
        assert result['total_alerts'] == 1
        assert result['total_groups'] == 1
    
    def test_similar_alerts_convergence(self):
        now = datetime.now()
        alerts = []
        for i in range(3):
            alerts.append({
                "alertname": "HighCPU",
                "service": "test-service",
                "instance": "instance-1",
                "severity": "critical",
                "timestamp": (now - timedelta(minutes=i)).isoformat()
            })
        
        result = self.agent.process({"alerts": alerts})
        assert result['total_groups'] == 1
    
    def test_different_alerts_separated(self):
        now = datetime.now()
        alerts = [
            {
                "alertname": "HighCPU",
                "service": "svc-a",
                "timestamp": now.isoformat()
            },
            {
                "alertname": "HighMemory",
                "service": "svc-b",
                "timestamp": now.isoformat()
            }
        ]
        result = self.agent.process({"alerts": alerts})
        assert result['total_groups'] == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])