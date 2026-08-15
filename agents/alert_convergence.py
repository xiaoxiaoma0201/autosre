"""
告警收敛 Agent - 聚合短时间内多条告警，判断是否同一根因
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict
import hashlib
from .base_agent import BaseAgent
from .message_bus import MessageType


class AlertConvergenceAgent(BaseAgent):
    """告警收敛 Agent"""
    
    def __init__(self, name: str = "alert_convergence", message_bus=None,
                 time_window: int = 300, similarity_threshold: float = 0.6):
        super().__init__(name, message_bus)
        self.time_window = time_window
        self.similarity_threshold = similarity_threshold
        
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理告警收敛"""
        alerts = input_data.get("alerts", [])
        if not alerts:
            return {"alert_groups": [], "total_alerts": 0}
        
        alert_groups = self.converge(alerts)
        
        result = {
            "alert_groups": alert_groups,
            "total_alerts": len(alerts),
            "total_groups": len(alert_groups),
            "convergence_rate": 1 - (len(alert_groups) / len(alerts)),
            "timestamp": datetime.now().isoformat()
        }
        
        self.send_message(MessageType.ALERT_CONVERGED, result)
        
        return result
    
    def converge(self, alerts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """执行告警收敛"""
        if not alerts:
            return []
        
        sorted_alerts = sorted(alerts, key=lambda x: self._parse_timestamp(x.get('timestamp')))
        
        alert_groups = []
        current_group = []
        group_id = 0
        
        for alert in sorted_alerts:
            if not current_group:
                current_group.append(alert)
                continue
            
            first_alert = current_group[0]
            if self._should_merge(alert, first_alert):
                current_group.append(alert)
            else:
                alert_groups.append(self._create_group(current_group, group_id))
                group_id += 1
                current_group = [alert]
        
        if current_group:
            alert_groups.append(self._create_group(current_group, group_id))
        
        return alert_groups
    
    def _should_merge(self, alert1: Dict[str, Any], alert2: Dict[str, Any]) -> bool:
        """判断两个告警是否应该合并"""
        time1 = self._parse_timestamp(alert1.get('timestamp'))
        time2 = self._parse_timestamp(alert2.get('timestamp'))
        if abs((time1 - time2).total_seconds()) > self.time_window:
            return False
        
        similarity = self._calculate_similarity(alert1, alert2)
        return similarity >= self.similarity_threshold
    
    def _calculate_similarity(self, alert1: Dict[str, Any], alert2: Dict[str, Any]) -> float:
        """计算两个告警的相似度"""
        score = 0.0
        total_weight = 0.0
        
        if alert1.get('alertname') and alert2.get('alertname'):
            total_weight += 0.4
            if alert1['alertname'] == alert2['alertname']:
                score += 0.4
        
        if alert1.get('service') and alert2.get('service'):
            total_weight += 0.3
            if alert1['service'] == alert2['service']:
                score += 0.3
        
        if alert1.get('instance') and alert2.get('instance'):
            total_weight += 0.2
            if alert1['instance'] == alert2['instance']:
                score += 0.2
        
        if alert1.get('labels') and alert2.get('labels'):
            total_weight += 0.1
            common_labels = set(alert1['labels'].keys()) & set(alert2['labels'].keys())
            if common_labels:
                matching = sum(1 for k in common_labels 
                             if alert1['labels'][k] == alert2['labels'][k])
                score += 0.1 * (matching / len(common_labels))
        
        return score / total_weight if total_weight > 0 else 0.0
    
    def _create_group(self, alerts: List[Dict[str, Any]], group_id: int) -> Dict[str, Any]:
        """创建告警组"""
        group_key = self._generate_group_key(alerts)
        representative = self._find_representative(alerts)
        
        return {
            "group_id": f"alert_group_{group_id}_{group_key}",
            "alerts": alerts,
            "alert_count": len(alerts),
            "representative_alert": representative,
            "start_time": min(self._parse_timestamp(a.get('timestamp')) for a in alerts).isoformat(),
            "end_time": max(self._parse_timestamp(a.get('timestamp')) for a in alerts).isoformat(),
            "severity": self._determine_severity(alerts),
            "services": list(set(a.get('service') for a in alerts if a.get('service'))),
            "instances": list(set(a.get('instance') for a in alerts if a.get('instance')))
        }
    
    def _generate_group_key(self, alerts: List[Dict[str, Any]]) -> str:
        """生成告警组的唯一键"""
        key_components = []
        for alert in alerts:
            components = [
                alert.get('alertname', ''),
                alert.get('service', ''),
                alert.get('instance', '')
            ]
            key_components.append('|'.join(components))
        
        key_string = '&'.join(sorted(set(key_components)))
        return hashlib.md5(key_string.encode()).hexdigest()[:8]
    
    def _find_representative(self, alerts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """找出代表性告警"""
        severity_order = {'critical': 0, 'warning': 1, 'info': 2}
        return min(alerts, key=lambda x: severity_order.get(x.get('severity', 'info'), 3))
    
    def _determine_severity(self, alerts: List[Dict[str, Any]]) -> str:
        """确定告警组的严重程度"""
        severity_order = {'critical': 0, 'warning': 1, 'info': 2}
        severities = [a.get('severity', 'info') for a in alerts]
        return min(severities, key=lambda x: severity_order.get(x, 3))
    
    def _parse_timestamp(self, timestamp: Optional[str]) -> datetime:
        """解析时间戳"""
        if not timestamp:
            return datetime.now()
        try:
            return datetime.fromisoformat(timestamp)
        except:
            return datetime.now()
