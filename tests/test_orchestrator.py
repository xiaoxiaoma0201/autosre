"""
编排器核心流程测试
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from datetime import datetime


class TestOrchestrator:
    """编排器测试"""
    
    def setup_method(self):
        from agents.orchestrator import AutoSREOrchestrator
        self.orchestrator = AutoSREOrchestrator({"auto_execute": False})
    
    def test_handle_empty_alerts(self):
        """测试空告警"""
        result = self.orchestrator.handle_incident([])
        assert result is not None
        assert 'status' in result
    
    def test_handle_single_alert(self):
        """测试单条告警"""
        alert = {
            "alertname": "TestAlert",
            "service": "test-service",
            "instance": "instance-1",
            "severity": "warning",
            "timestamp": datetime.now().isoformat()
        }
        result = self.orchestrator.handle_incident([alert])
        assert result is not None
        assert result.get('status') in ['completed', 'failed', 'no_alerts']
        assert 'summary' in result
    
    def test_generate_summary(self):
        """测试摘要生成"""
        results = [{
            'group_id': 'test-group',
            'alert_group': {'alert_count': 1},
            'repair_result': {'executed': False},
            'root_cause': {
                'top_hypothesis': {'cause': 'CPU issue'},
                'confidence': 0.8
            }
        }]
        summary = self.orchestrator._generate_summary('test-id', results)
        assert summary['total_alerts'] == 1
        assert summary['alert_groups'] == 1
        assert len(summary['top_causes']) == 1


class TestDatabase:
    """数据库测试"""
    
    def test_save_and_stats(self):
        import tempfile
        import os
        
        # 使用临时文件数据库
        temp_db = os.path.join(tempfile.gettempdir(), "test_autosre.db")
        from agents.database import Database
        db = Database(temp_db)
        
        incident = {
            "incident_id": "test-123",
            "status": "completed",
            "summary": {
                "total_alerts": 1,
                "alert_groups": 1,
                "top_causes": [{"cause": "CPU", "confidence": 0.8}],
                "reports_generated": 1
            }
        }
        
        assert db.save_incident(incident) == True
        
        stats = db.get_incident_stats()
        assert stats['total_incidents'] == 1
        assert stats['success_rate'] == 1.0
        
        # 清理
        if os.path.exists(temp_db):
            os.remove(temp_db)