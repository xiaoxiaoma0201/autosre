"""
通知模块 - 发送钉钉通知
"""
import requests
import json
from typing import Dict, Any, Optional
from datetime import datetime
from loguru import logger


class NotificationService:
    """通知服务"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.dingtalk_webhook = self.config.get('dingtalk_webhook', 'https://oapi.dingtalk.com/robot/send?access_token=b94dfd3f820d50dbc71a837c8d3407461210062d6fcb94af50f03f4e61a4c1b3')
        self.enabled = bool(self.dingtalk_webhook)
        
        if self.enabled:
            logger.info("钉钉通知已启用")
        else:
            logger.info("钉钉通知未启用")
    
    def send_dingtalk(self, title: str, content: str) -> bool:
        """发送钉钉通知"""
        if not self.enabled:
            return False
        
        try:
            message = {
                "msgtype": "markdown",
                "markdown": {
                    "title": title,
                    "text": f"## {title}\n\n{content}"
                }
            }
            
            response = requests.post(self.dingtalk_webhook, json=message, timeout=10)
            result = response.json()
            
            if result.get('errcode') == 0:
                logger.info("钉钉通知发送成功")
                return True
            else:
                logger.error(f"钉钉通知发送失败: {result}")
                return False
        except Exception as e:
            logger.error(f"钉钉通知异常: {str(e)}")
            return False
    
    def send_incident_notification(self, incident_result: Dict[str, Any]) -> bool:
        """发送故障处理完成通知"""
        title = "🚨 AutoSRE 故障处理完成"
        
        summary = incident_result.get('summary', {})
        content = f"""
**事件 ID**: {incident_result.get('incident_id')}
**状态**: {incident_result.get('status')}
**告警数**: {summary.get('total_alerts', 0)}
**告警组数**: {summary.get('alert_groups', 0)}
**生成报告数**: {summary.get('reports_generated', 0)}

**根因分析**:
"""
        for cause in summary.get('top_causes', []):
            content += f"- {cause['cause']} (置信度: {cause['confidence']:.2%})\n"
        
        return self.send_dingtalk(title, content)
