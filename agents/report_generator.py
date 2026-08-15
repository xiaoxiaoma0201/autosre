"""
复盘报告 Agent - 生成故障时间线、根因分析、修复记录、预防建议
"""
from typing import Dict, Any, List
from datetime import datetime
import os
import json
from .base_agent import BaseAgent
from .message_bus import MessageType


class ReportGeneratorAgent(BaseAgent):
    """复盘报告 Agent"""
    
    def __init__(self, name: str = "report_generator", message_bus=None,
                 report_dir: str = "reports",
                 template_path: str = "templates/incident_report.md.j2"):
        super().__init__(name, message_bus)
        self.report_dir = report_dir
        self.template_path = template_path
        
        os.makedirs(report_dir, exist_ok=True)
        
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """生成复盘报告"""
        incident_id = input_data.get("incident_id", "")
        if not incident_id:
            incident_id = f"incident_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        report_data = self._build_report_data(input_data)
        report_content = self._generate_report_content(report_data)
        report_path = self._save_report(incident_id, report_content)
        
        result = {
            "incident_id": incident_id,
            "report_path": report_path,
            "generated_at": datetime.now().isoformat()
        }
        self.send_message(MessageType.REPORT_GENERATED, result)
        
        return result
    
    def _build_report_data(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """构建报告数据"""
        alert_group = input_data.get("alert_group", {})
        log_result = input_data.get("log_result", {})
        metric_result = input_data.get("metric_result", {})
        root_cause = input_data.get("root_cause", {})
        repair_result = input_data.get("repair_result", {})
        
        timeline = self._build_timeline(input_data)
        key_metrics = self._extract_key_metrics(metric_result)
        error_patterns = self._extract_error_patterns(log_result)
        
        return {
            "incident_id": input_data.get("incident_id", ""),
            "report_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "severity": alert_group.get("severity", "unknown"),
            "affected_services": alert_group.get("services", []),
            "affected_instances": alert_group.get("instances", []),
            "alert_count": alert_group.get("alert_count", 0),
            "duration": self._calculate_duration(alert_group),
            "timeline": timeline,
            "root_cause": root_cause.get("top_hypothesis", {}).get("cause", "未知"),
            "confidence": root_cause.get("confidence", 0),
            "key_metrics": key_metrics,
            "error_patterns": error_patterns,
            "repair_action": repair_result.get("action", "未执行"),
            "repair_success": repair_result.get("executed", False),
            "prevention": root_cause.get("top_hypothesis", {}).get("prevention", "无"),
            "evidence": root_cause.get("top_hypothesis", {}).get("evidence", []),
            "llm_analysis": root_cause.get("llm_analysis", "")
        }
    
    def _build_timeline(self, input_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """构建故障时间线"""
        timeline = []
        
        alert_group = input_data.get("alert_group", {})
        for alert in alert_group.get("alerts", []):
            timeline.append({
                "time": alert.get("timestamp", ""),
                "event": f"告警: {alert.get('alertname', 'unknown')}",
                "type": "alert",
                "details": alert.get('annotations', {}).get('summary', '')
            })
        
        log_result = input_data.get("log_result", {})
        for event in log_result.get("analysis_result", {}).get("key_events", []):
            timeline.append({
                "time": event.get("timestamp", ""),
                "event": f"日志: {event.get('event', '')}",
                "type": "log",
                "details": f"Level: {event.get('level', 'unknown')}"
            })
        
        metric_result = input_data.get("metric_result", {})
        for anomaly in metric_result.get("anomalies", []):
            timeline.append({
                "time": anomaly.get("timestamp", ""),
                "event": f"指标异常: {anomaly.get('metric', 'unknown')}",
                "type": "metric",
                "details": f"Value: {anomaly.get('current_value', 'N/A')}"
            })
        
        repair_result = input_data.get("repair_result", {})
        if repair_result.get("executed"):
            timeline.append({
                "time": repair_result.get("timestamp", ""),
                "event": f"执行修复: {repair_result.get('action', 'unknown')}",
                "type": "repair",
                "details": str(repair_result.get("result", ""))
            })
        
        timeline.sort(key=lambda x: x.get("time", ""))
        
        return timeline
    
    def _extract_key_metrics(self, metric_result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """提取关键指标"""
        key_metrics = []
        
        for metric_name, metric_data in metric_result.get("metrics", {}).items():
            # 只显示有数据的指标
            if metric_data.get('status') != 'success':
                continue
            
            current_value = metric_data.get("current_value")
            if current_value is None:
                continue
            
            key_metrics.append({
                "name": metric_name,
                "current_value": round(current_value, 2) if isinstance(current_value, (int, float)) else current_value,
                "threshold": metric_data.get("threshold"),
                "unit": metric_data.get("unit", ""),
                "exceeded": metric_data.get("exceeded_threshold", False)
            })
        
        return key_metrics
    
    def _extract_error_patterns(self, log_result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """提取错误模式"""
        patterns = log_result.get("analysis_result", {}).get("error_patterns", {})
        return patterns.get("summary", [])
    
    def _calculate_duration(self, alert_group: Dict[str, Any]) -> str:
        """计算故障持续时间"""
        start_time = alert_group.get("start_time")
        end_time = alert_group.get("end_time")
        
        if start_time and end_time:
            try:
                start = datetime.fromisoformat(start_time)
                end = datetime.fromisoformat(end_time)
                duration = end - start
                minutes = int(duration.total_seconds() / 60)
                return f"{minutes} 分钟"
            except:
                pass
        
        return "未知"
    
    def _generate_report_content(self, report_data: Dict[str, Any]) -> str:
        """生成报告内容"""
        return self._generate_default_report(report_data)
    
    def _generate_default_report(self, data: Dict[str, Any]) -> str:
        """生成默认格式报告"""
        report = f"""
# 故障复盘报告

## 基本信息
- **故障 ID**: {data['incident_id']}
- **报告时间**: {data['report_time']}
- **严重程度**: {data['severity']}
- **影响服务**: {', '.join(data['affected_services'])}
- **影响实例**: {', '.join(data['affected_instances'])}
- **告警数量**: {data['alert_count']}
- **持续时间**: {data['duration']}

## 故障时间线

| 时间 | 事件 | 类型 |
|------|------|------|
"""
        for event in data['timeline']:
            report += f"| {event['time']} | {event['event']} | {event['type']} |\n"
        
        report += f"""
## 根因分析
- **根因**: {data['root_cause']}
- **置信度**: {data['confidence']:.2%}
- **证据**:
"""
        for evidence in data['evidence']:
            report += f"  - {evidence}\n"
        
        report += f"""
## 关键指标
| 指标 | 当前值 | 阈值 | 状态 |
|------|--------|------|------|
"""
        for metric in data['key_metrics']:
            status = "异常" if metric['exceeded'] else "正常"
            unit = metric.get('unit') or ''
            current = metric['current_value'] if metric['current_value'] is not None else 'N/A'
            threshold = metric['threshold'] if metric['threshold'] is not None else 'N/A'
            report += f"| {metric['name']} | {current} {unit} | {threshold} {unit} | {status} |\n"
        
        report += f"""
## 修复操作
- **动作**: {data['repair_action']}
- **结果**: {'成功' if data['repair_success'] else '失败/未执行'}

## LLM 深度分析
{data['llm_analysis'] if data.get('llm_analysis') else '未生成 LLM 分析'}

## 预防建议
{data['prevention']}

## 总结
本次故障严重程度为 **{data['severity']}**，影响了 {len(data['affected_services'])} 个服务。
根因分析置信度为 **{data['confidence']:.2%}**。
建议根据预防建议进行改进，避免类似问题再次发生。
"""
        return report
    
    def _save_report(self, incident_id: str, content: str) -> str:
        """保存报告 - 使用时间戳命名"""
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"{timestamp}_report.md"
        filepath = os.path.join(self.report_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return filepath