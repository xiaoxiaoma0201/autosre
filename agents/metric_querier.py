"""
指标查询 Agent - 查询真实的 Prometheus 指标
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import requests
from .base_agent import BaseAgent
from .message_bus import MessageType
from .cache import metric_cache


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
            # 检查缓存
            cached = metric_cache.get(metric_name)
            if cached:
                metrics[metric_name] = cached
                continue
            
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
                    
                    # 存入缓存
                    metric_cache.set(metric_name, metrics[metric_name])
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
        """查询 Prometheus"""
        try:
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
            
            # 尝试瞬时查询
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
                            import time
                            return [(time.time(), float(value[1]))]
            
            return []
        except Exception as e:
            self.logger.warning(f"Prometheus query failed: {str(e)}")
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