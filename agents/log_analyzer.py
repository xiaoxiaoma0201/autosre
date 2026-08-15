"""
日志分析 Agent - 分析日志，提取异常栈和错误模式
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import re
from .base_agent import BaseAgent
from .message_bus import MessageType


class LogAnalyzerAgent(BaseAgent):
    """日志分析 Agent"""
    
    def __init__(self, name: str = "log_analyzer", message_bus=None,
                 elk_url: str = "http://localhost:9200",
                 grafana_url: str = "http://localhost:3000"):
        super().__init__(name, message_bus)
        self.elk_url = elk_url
        self.grafana_url = grafana_url
        
        self.error_patterns = {
            'out_of_memory': r'OutOfMemoryError|memory exhausted|Cannot allocate memory',
            'null_pointer': r'NullPointerException|NoneType.*has no attribute',
            'connection_timeout': r'Connection timed out|connect timeout|timeout expired',
            'disk_full': r'No space left on device|disk full|insufficient space',
            'database_error': r'SQLException|database error|connection refused.*database',
            'high_cpu': r'high CPU|CPU usage.*\d+%|load average',
            'deadlock': r'Deadlock found|deadlock detected|Lock wait timeout',
            'service_unavailable': r'503|Service Unavailable|service unavailable',
            'authentication_failed': r'authentication failed|unauthorized|401|403',
            'network_error': r'Network is unreachable|connection refused|DNS resolution failed'
        }
        
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理日志分析"""
        alert_group = input_data.get("alert_group", {})
        if not alert_group:
            return {"error": "No alert group provided"}
        
        time_range = self._get_time_range(alert_group)
        logs = self._generate_mock_logs(alert_group, time_range)
        analysis_result = self._analyze_logs(logs, alert_group)
        
        result = {
            "alert_group_id": alert_group.get("group_id"),
            "analysis_result": analysis_result,
            "timestamp": datetime.now().isoformat()
        }
        self.send_message(MessageType.LOG_ANALYSIS_RESULT, result)
        
        return result
    
    def _analyze_logs(self, logs: List[Dict[str, Any]], alert_group: Dict[str, Any]) -> Dict[str, Any]:
        """分析日志内容"""
        if not logs:
            return {"error": "No logs found"}
        
        level_stats = Counter(log.get('level', 'INFO') for log in logs)
        error_patterns = self._extract_error_patterns(logs)
        stack_traces = self._identify_stack_traces(logs)
        key_events = self._extract_key_events(logs)
        anomaly_score = self._calculate_anomaly_score(level_stats, error_patterns)
        
        return {
            "log_count": len(logs),
            "level_stats": dict(level_stats),
            "error_patterns": error_patterns,
            "stack_traces": stack_traces,
            "key_events": key_events,
            "anomaly_score": anomaly_score,
            "time_range": {
                "start": logs[0].get('@timestamp'),
                "end": logs[-1].get('@timestamp')
            }
        }
    
    def _extract_error_patterns(self, logs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """提取错误模式"""
        patterns = []
        pattern_counter = defaultdict(int)
        
        for log in logs:
            if log.get('level') in ['ERROR', 'FATAL', 'CRITICAL']:
                message = log.get('message', '')
                
                for pattern_name, pattern_regex in self.error_patterns.items():
                    if re.search(pattern_regex, message, re.IGNORECASE):
                        pattern_counter[pattern_name] += 1
                        match = re.search(pattern_regex, message, re.IGNORECASE)
                        if match:
                            patterns.append({
                                "pattern": pattern_name,
                                "message": message,
                                "matched_text": match.group(),
                                "timestamp": log.get('@timestamp'),
                                "service": log.get('service', 'unknown'),
                                "instance": log.get('instance', 'unknown')
                            })
        
        pattern_summary = [
            {"pattern": name, "count": count}
            for name, count in pattern_counter.items()
        ]
        
        return {
            "patterns": patterns[:10],
            "summary": pattern_summary
        }
    
    def _identify_stack_traces(self, logs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """识别异常栈"""
        stack_traces = []
        current_trace = []
        
        for log in logs:
            message = log.get('message', '')
            
            if re.search(r'Exception|Error|Traceback', message, re.IGNORECASE):
                if current_trace:
                    stack_traces.append(self._format_stack_trace(current_trace))
                current_trace = [log]
            elif current_trace and re.search(r'^\s+at |^\s+File ', message):
                current_trace.append(log)
            elif current_trace:
                stack_traces.append(self._format_stack_trace(current_trace))
                current_trace = []
        
        if current_trace:
            stack_traces.append(self._format_stack_trace(current_trace))
        
        return stack_traces[:5]
    
    def _format_stack_trace(self, trace_logs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """格式化异常栈"""
        return {
            "exception_type": self._extract_exception_type(trace_logs[0].get('message', '')),
            "message": trace_logs[0].get('message', ''),
            "frames": [log.get('message', '') for log in trace_logs[1:]],
            "timestamp": trace_logs[0].get('@timestamp'),
            "service": trace_logs[0].get('service', 'unknown')
        }
    
    def _extract_exception_type(self, message: str) -> str:
        """提取异常类型"""
        match = re.search(r'(\w+(?:Exception|Error))', message)
        return match.group(1) if match else 'UnknownException'
    
    def _extract_key_events(self, logs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """提取关键事件"""
        key_events = []
        keywords = ['start', 'stop', 'restart', 'fail', 'error', 'warning', 
                   'deploy', 'rollback', 'scale', 'config change']
        
        for log in logs:
            message = log.get('message', '').lower()
            if any(keyword in message for keyword in keywords):
                if log.get('level') in ['ERROR', 'WARN', 'WARNING', 'FATAL']:
                    key_events.append({
                        "event": log.get('message', ''),
                        "timestamp": log.get('@timestamp'),
                        "level": log.get('level'),
                        "service": log.get('service', 'unknown')
                    })
        
        return key_events[:10]
    
    def _calculate_anomaly_score(self, level_stats: Dict[str, int], 
                                 error_patterns: Dict[str, Any]) -> float:
        """计算异常分数"""
        total_logs = sum(level_stats.values())
        if total_logs == 0:
            return 0.0
        
        error_count = level_stats.get('ERROR', 0) + level_stats.get('FATAL', 0)
        error_ratio = error_count / total_logs
        pattern_bonus = min(len(error_patterns.get('summary', [])), 5) * 0.05
        
        score = min(error_ratio * 0.7 + pattern_bonus, 1.0)
        return round(score, 3)
    
    def _get_time_range(self, alert_group: Dict[str, Any]) -> tuple:
        """获取时间范围"""
        start_time = alert_group.get('start_time')
        end_time = alert_group.get('end_time')
        
        if start_time:
            start = datetime.fromisoformat(start_time) - timedelta(minutes=5)
        else:
            start = datetime.now() - timedelta(minutes=15)
            
        if end_time:
            end = datetime.fromisoformat(end_time) + timedelta(minutes=5)
        else:
            end = datetime.now()
            
        return start.isoformat(), end.isoformat()
    
    def _generate_mock_logs(self, alert_group: Dict[str, Any], 
                           time_range: tuple) -> List[Dict[str, Any]]:
        """生成模拟日志"""
        mock_logs = []
        services = alert_group.get('services', ['test-service'])
        
        sample_logs = [
            {"level": "INFO", "message": "Application started successfully", "service": services[0]},
            {"level": "INFO", "message": "Processing request from user", "service": services[0]},
            {"level": "WARN", "message": "High memory usage detected: 85%", "service": services[0]},
            {"level": "ERROR", "message": "OutOfMemoryError: Java heap space", "service": services[0]},
            {"level": "ERROR", "message": "Failed to process request: Connection timed out", "service": services[0]},
            {"level": "INFO", "message": "Retrying connection to database", "service": services[0]},
            {"level": "ERROR", "message": "SQLException: Connection refused to database", "service": services[0]},
            {"level": "WARN", "message": "Disk usage exceeded 80% threshold", "service": services[0]},
            {"level": "FATAL", "message": "Service crashed due to insufficient memory", "service": services[0]},
            {"level": "INFO", "message": "Service restart initiated", "service": services[0]}
        ]
        
        for i, log in enumerate(sample_logs):
            log['@timestamp'] = (datetime.now() - timedelta(minutes=10-i)).isoformat()
            log['instance'] = 'instance-1'
            mock_logs.append(log)
        
        return mock_logs
