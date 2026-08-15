"""
指标查询 Agent - 查询真实的 Prometheus 指标
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import requests
from .base_agent import BaseAgent
from .message_bus import MessageType


class MetricQuerierAgent(BaseAgent):
    """指标查询 Agent"""
    
    def __init__(self, name: str = "metric_querier", message_bus=None,
                 prometheus_url: str = "http://localhost:9090"):
        super().__init__(name, message_bus)
        self.prometheus_url = prometheus_url.rstrip('/')
        
        self.metric_definitions = {
            'cpu_usage': {
                'query': '100 - (avg(rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)',
                'threshold': 80,
                'unit': '%'
            },
            'memory_usage': {
                'query': '(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100',
                'threshold': 85,
                'unit': '%'
            },
            'disk_usage': {
                'query': '100 * (1 - (node_filesystem_avail_bytes{mountpoint="/"} / node_filesystem_size_bytes{mountpoint="/"}))',
                'threshold': 85,
                'unit': '%'
            },
            'network_receive': {
                'query': 'rate(node_network_receive_bytes_total[5m])',
                'threshold': None,
                'unit': 'bytes/s'
            },
            'load_average': {
                'query': 'node_load1',
                'threshold': 4,
                'unit': 'load'
            },
            'http_requests': {
                'query': 'rate(http_requests_total[5m])',
                'threshold': None,
                'unit': 'req/s'
            },
            'http_errors': {
                'query': 'rate(http_requests_total{status=~"5.."}[5m])',
                'threshold': 1,
                'unit': 'errors/s'
            }
        }
        
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理指标查询"""
        alert_group = input_data.get("alert_group", {})
        if not alert_group:
            return {"error": "No alert group provided"}
        
        time_range = self._get_time_range(alert_group)
        metrics = self._query_metrics(alert_group, time_range)
        anomalies = self._detect_anomalies(metrics)
        
        result = {
            "alert_group_id": alert_group.get("group_id"),
            "metrics": metrics,
            "anomalies": anomalies,
            "query_time": datetime.now().isoformat(),
            "data_source": "prometheus"
        }
        self.send_message(MessageType.METRIC_QUERY_RESULT, result)
        
        return result
    
    def _query_metrics(self, alert_group: Dict[str, Any], 
                       time_range: tuple) -> Dict[str, Any]:
        """查询指标数据"""
        metrics = {}
        
        for metric_name, metric_def in self.metric_definitions.items():
            try:
                metric_data = self._query_prometheus(metric_def['query'], time_range)
                
                if metric_data:
                    values = [point[1] for point in metric_data]
                    current_value = values[-1] if values else None
                    
                    metrics[metric_name] = {
                        'name': metric_name,
                        'query': metric_def['query'],
                        'unit': metric_def['unit'],
                        'threshold': metric_def['threshold'],
                        'current_value': current_value,
                        'max_value': max(values) if values else None,
                        'min_value': min(values) if values else None,
                        'avg_value': sum(values) / len(values) if values else None,
                        'exceeded_threshold': self._check_threshold(current_value, metric_def['threshold']),
                        'data_points': metric_data[-20:],
                        'status': 'success'
                    }
                else:
                    metrics[metric_name] = {
                        'name': metric_name,
                        'status': 'no_data',
                        'query': metric_def['query']
                    }
            except Exception as e:
                self.logger.warning(f"Query metric {metric_name} failed: {str(e)}")
                metrics[metric_name] = {
                    'name': metric_name,
                    'status': 'error',
                    'error': str(e),
                    'query': metric_def['query']
                }
        
        return metrics
    
    def _query_prometheus(self, query: str, time_range: tuple) -> List[tuple]:
        """查询 Prometheus - 先尝试范围查询，失败后使用瞬时查询"""
        try:
            # 先尝试范围查询
            response = requests.get(
                f"{self.prometheus_url}/api/v1/query_range",
                params={
                    'query': query,
                    'start': time_range[0],
                    'end': time_range[1],
                    'step': '30s'
                },
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'success':
                    results = data.get('data', {}).get('result', [])
                    if results:
                        values = results[0].get('values', [])
                        if values:
                            return [(float(v[0]), float(v[1])) for v in values]
            
            # 范围查询失败或返回空，尝试瞬时查询
            response = requests.get(
                f"{self.prometheus_url}/api/v1/query",
                params={'query': query},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'success':
                    results = data.get('data', {}).get('result', [])
                    if results:
                        value = results[0].get('value', [None, None])
                        if value[1]:
                            # 生成一个数据点
                            import time
                            return [(time.time(), float(value[1]))]
            
            return []
        except requests.exceptions.ConnectionError:
            self.logger.warning(f"Cannot connect to Prometheus: {self.prometheus_url}")
            return []
        except Exception as e:
            self.logger.error(f"Prometheus query failed: {str(e)}")
            return []
    
    def _check_threshold(self, value: Optional[float], threshold: Optional[float]) -> bool:
        """检查是否超过阈值"""
        if value is None or threshold is None:
            return False
        return value > threshold
    
    def _detect_anomalies(self, metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        """检测异常指标"""
        anomalies = []
        
        for metric_name, metric_data in metrics.items():
            if metric_data.get('status') != 'success':
                continue
            
            current_value = metric_data.get('current_value')
            threshold = metric_data.get('threshold')
            
            if current_value and threshold and current_value > threshold:
                anomalies.append({
                    'metric': metric_name,
                    'type': 'threshold_exceeded',
                    'current_value': current_value,
                    'threshold': threshold,
                    'severity': self._calculate_severity(current_value, threshold),
                    'timestamp': datetime.now().isoformat()
                })
            
            values = [point[1] for point in metric_data.get('data_points', [])]
            if len(values) > 5:
                avg = sum(values[:-1]) / len(values[:-1]) if len(values[:-1]) > 0 else 0
                if avg > 0 and current_value:
                    change_percent = abs(current_value - avg) / avg
                    if change_percent > 0.5:
                        anomalies.append({
                            'metric': metric_name,
                            'type': 'sudden_change',
                            'current_value': current_value,
                            'avg_value': avg,
                            'change_percent': change_percent,
                            'timestamp': datetime.now().isoformat()
                        })
        
        return anomalies
    
    def _calculate_severity(self, value: float, threshold: float) -> str:
        """计算异常严重程度"""
        if value > threshold * 1.3:
            return 'critical'
        elif value > threshold * 1.1:
            return 'warning'
        else:
            return 'info'
    
    def _get_time_range(self, alert_group: Dict[str, Any]) -> tuple:
        """获取时间范围"""
        start_time = alert_group.get('start_time')
        end_time = alert_group.get('end_time')
        
        if start_time:
            start = datetime.fromisoformat(start_time) - timedelta(minutes=10)
        else:
            start = datetime.now() - timedelta(minutes=30)
            
        if end_time:
            end = datetime.fromisoformat(end_time) + timedelta(minutes=5)
        else:
            end = datetime.now()
            
        return start.isoformat(), end.isoformat()
    
    def check_prometheus_health(self) -> Dict[str, Any]:
        """检查 Prometheus 健康状态"""
        try:
            response = requests.get(f"{self.prometheus_url}/-/healthy", timeout=5)
            return {
                'healthy': response.status_code == 200,
                'status_code': response.status_code,
                'url': self.prometheus_url
            }
        except Exception as e:
            return {
                'healthy': False,
                'error': str(e),
                'url': self.prometheus_url
            }
