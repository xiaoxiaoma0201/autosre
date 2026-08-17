"""
告警升级策略模块 - 根据严重程度和时间自动升级告警
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from enum import Enum
from loguru import logger


class EscalationLevel(Enum):
    """升级等级"""
    L1 = "L1"  # 普通 - 仅通知
    L2 = "L2"  # 重要 - 通知 + 自动分析
    L3 = "L3"  # 紧急 - 通知 + 自动分析 + 自动修复
    L4 = "L4"  # 严重 - 通知 + 分析 + 修复 + 人工介入


class EscalationPolicy:
    """告警升级策略"""
    
    def __init__(self):
        # 定义升级规则
        self.rules = {
            # severity -> (初始等级, 升级时间(分钟), 升级后等级)
            "info": (EscalationLevel.L1, 60, EscalationLevel.L2),
            "warning": (EscalationLevel.L2, 30, EscalationLevel.L3),
            "critical": (EscalationLevel.L3, 10, EscalationLevel.L4),
        }
        
        # 通知渠道映射
        self.notification_channels = {
            EscalationLevel.L1: ["log"],
            EscalationLevel.L2: ["log", "dingtalk"],
            EscalationLevel.L3: ["log", "dingtalk", "auto_repair"],
            EscalationLevel.L4: ["log", "dingtalk", "auto_repair", "phone_call"],
        }
    
    def get_initial_level(self, severity: str) -> EscalationLevel:
        """获取初始升级等级"""
        rule = self.rules.get(severity.lower(), (EscalationLevel.L1, 60, EscalationLevel.L2))
        return rule[0]
    
    def should_escalate(self, alert: Dict[str, Any]) -> bool:
        """判断是否需要升级"""
        severity = alert.get('severity', 'info')
        created_time = self._parse_time(alert.get('timestamp'))
        
        if not created_time:
            return False
        
        rule = self.rules.get(severity.lower(), (EscalationLevel.L1, 60, EscalationLevel.L2))
        _, escalate_after_minutes, _ = rule
        
        elapsed = datetime.now() - created_time
        return elapsed > timedelta(minutes=escalate_after_minutes)
    
    def get_escalated_level(self, alert: Dict[str, Any]) -> EscalationLevel:
        """获取升级后的等级"""
        severity = alert.get('severity', 'info')
        rule = self.rules.get(severity.lower(), (EscalationLevel.L1, 60, EscalationLevel.L2))
        
        if self.should_escalate(alert):
            return rule[2]
        return rule[0]
    
    def get_notification_channels(self, level: EscalationLevel) -> List[str]:
        """获取通知渠道"""
        return self.notification_channels.get(level, ["log"])
    
    def _parse_time(self, timestamp: Optional[str]) -> Optional[datetime]:
        """解析时间戳"""
        if not timestamp:
            return None
        try:
            return datetime.fromisoformat(timestamp)
        except:
            return None
    
    def evaluate_alert(self, alert: Dict[str, Any]) -> Dict[str, Any]:
        """评估告警并返回处理建议"""
        severity = alert.get('severity', 'info')
        level = self.get_escalated_level(alert)
        channels = self.get_notification_channels(level)
        
        return {
            "alertname": alert.get('alertname', 'unknown'),
            "severity": severity,
            "escalation_level": level.value,
            "notification_channels": channels,
            "should_auto_repair": level in [EscalationLevel.L3, EscalationLevel.L4],
            "requires_manual": level == EscalationLevel.L4,
            "evaluated_at": datetime.now().isoformat()
        }
    
    def evaluate_batch(self, alerts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """批量评估告警"""
        results = []
        for alert in alerts:
            results.append(self.evaluate_alert(alert))
        return results
    
    def get_policy_summary(self) -> Dict[str, Any]:
        """获取策略摘要"""
        return {
            "rules": {
                "info": "L1 -> 60min -> L2",
                "warning": "L2 -> 30min -> L3",
                "critical": "L3 -> 10min -> L4",
            },
            "channels": {
                "L1": ["日志"],
                "L2": ["日志", "钉钉"],
                "L3": ["日志", "钉钉", "自动修复"],
                "L4": ["日志", "钉钉", "自动修复", "电话"],
            }
        }