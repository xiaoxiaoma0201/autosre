"""
根因推理 Agent - 综合日志+指标+历史故障库，输出根因假设和置信度
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
from collections import defaultdict
import json
import os
from .base_agent import BaseAgent
from .llm_analyzer import LLMAnalyzer
from .message_bus import MessageType


class RootCauseAgent(BaseAgent):
    """根因推理 Agent"""
    
    def __init__(self, name: str = "root_cause_analyzer", message_bus=None,
                 knowledge_base_path: str = "config/agents/knowledge_base.json"):
        super().__init__(name, message_bus)
        self.knowledge_base_path = knowledge_base_path
        self.knowledge_base = self._load_knowledge_base()
        
        # 初始化 LLM（从配置读取）
        self.llm = None
        try:
            import json
            with open('config/autosre_config.json', 'r', encoding='utf-8') as f:
                llm_config = json.load(f)
            
            if llm_config.get('llm_enabled'):
                self.llm = LLMAnalyzer(
                    api_key=llm_config.get('llm_api_key'),
                    model=llm_config.get('llm_model', 'deepseek-v4-flash'),
                    base_url=llm_config.get('llm_base_url', 'https://api.deepseek.com')
                )
        except Exception as e:
            self.logger.warning(f"LLM init failed: {str(e)}")
        
        self.inference_rules = [
            self._rule_memory_issue,
            self._rule_disk_issue,
            self._rule_cpu_issue,
            self._rule_database_issue,
            self._rule_network_issue,
            self._rule_application_error,
            self._rule_service_crash
        ]
        
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理根因推理"""
        alert_group = input_data.get("alert_group", {})
        log_result = input_data.get("log_result", {})
        metric_result = input_data.get("metric_result", {})
        
        if not alert_group:
            return {"error": "No alert group provided"}
        
        hypotheses = self._infer_root_causes(alert_group, log_result, metric_result)
        ranked_hypotheses = self._rank_hypotheses(hypotheses)
        
        result = {
            "alert_group_id": alert_group.get("group_id"),
            "top_hypothesis": ranked_hypotheses[0] if ranked_hypotheses else {"cause": "无法确定根因", "confidence": 0, "evidence": ["证据不足"], "repair_action": "none", "prevention": "需要人工介入"},
            "all_hypotheses": ranked_hypotheses[:5],
            "confidence": ranked_hypotheses[0]['confidence'] if ranked_hypotheses else 0.3,
            "analysis_time": datetime.now().isoformat()
        }
        
        # 使用 LLM 增强根因分析
        if self.llm and self.llm.enabled:
            try:
                incident_data = {
                    "alerts": alert_group.get('alerts', []),
                    "metrics": metric_result.get('metrics', {}),
                    "root_cause": result
                }
                llm_result = self.llm.analyze_incident(incident_data)
                if llm_result.get('enabled') and llm_result.get('analysis'):
                    result['llm_analysis'] = llm_result['analysis']
                    self.logger.info("LLM 已增强根因分析")
                    self.logger.info(f"LLM 分析长度: {len(llm_result['analysis'])} 字符")
                else:
                    self.logger.warning(f"LLM 分析未返回结果: {llm_result.get('error', 'unknown')}")
            except Exception as e:
                self.logger.warning(f"LLM enhancement failed: {str(e)}")
        
        self.send_message(MessageType.ROOT_CAUSE_HYPOTHESIS, result)
        
        return result
    
    def _infer_root_causes(self, alert_group: Dict[str, Any],
                          log_result: Dict[str, Any],
                          metric_result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """推理根因"""
        hypotheses = []
        
        # 1. 基于告警名称的直接推理
        alert_hypotheses = self._alert_name_inference(alert_group)
        hypotheses.extend(alert_hypotheses)
        
        # 2. 基于规则的推理
        for rule in self.inference_rules:
            try:
                hypothesis = rule(alert_group, log_result, metric_result)
                if hypothesis:
                    hypotheses.append(hypothesis)
            except Exception as e:
                self.logger.warning(f"Rule {rule.__name__} failed: {str(e)}")
        
        # 3. 基于历史案例的推理
        case_hypotheses = self._case_based_inference(alert_group, log_result, metric_result)
        hypotheses.extend(case_hypotheses)
        
        return self._combine_hypotheses(hypotheses)
    
    def _alert_name_inference(self, alert_group: Dict[str, Any]) -> List[Dict[str, Any]]:
        """基于告警名称的直接推理"""
        hypotheses = []
        alerts = alert_group.get('alerts', [])
        
        for alert in alerts:
            alertname = alert.get('alertname', '').lower()
            
            # CPU 相关告警
            if 'cpu' in alertname or 'load' in alertname:
                hypotheses.append({
                    "cause": "CPU 资源不足",
                    "confidence": 0.8,
                    "evidence": [f"告警名称包含 CPU/Load 相关关键词: {alert.get('alertname')}"],
                    "repair_action": "scale_up",
                    "prevention": "优化代码性能，增加 CPU 资源"
                })
            
            # 内存相关告警
            if 'memory' in alertname or 'oom' in alertname or 'outofmemory' in alertname:
                hypotheses.append({
                    "cause": "内存不足/内存泄漏",
                    "confidence": 0.85,
                    "evidence": [f"告警名称包含内存相关关键词: {alert.get('alertname')}"],
                    "repair_action": "restart_service",
                    "prevention": "增加内存限制，优化内存使用"
                })
            
            # 磁盘相关告警
            if 'disk' in alertname or 'storage' in alertname:
                hypotheses.append({
                    "cause": "磁盘空间不足",
                    "confidence": 0.8,
                    "evidence": [f"告警名称包含磁盘相关关键词: {alert.get('alertname')}"],
                    "repair_action": "clean_disk",
                    "prevention": "定期清理日志，监控磁盘使用"
                })
            
            # 服务宕机
            if 'down' in alertname or 'crash' in alertname or 'service' in alertname:
                hypotheses.append({
                    "cause": "服务崩溃或宕机",
                    "confidence": 0.75,
                    "evidence": [f"告警名称包含服务宕机相关关键词: {alert.get('alertname')}"],
                    "repair_action": "restart_service",
                    "prevention": "增加健康检查，实现自动重启"
                })
            
            # 网络相关
            if 'network' in alertname or 'connection' in alertname:
                hypotheses.append({
                    "cause": "网络连接问题",
                    "confidence": 0.7,
                    "evidence": [f"告警名称包含网络相关关键词: {alert.get('alertname')}"],
                    "repair_action": "restart_service",
                    "prevention": "检查网络配置，增加重试机制"
                })
        
        return hypotheses
    
    def _rule_memory_issue(self, alert_group: Dict[str, Any],
                          log_result: Dict[str, Any],
                          metric_result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """内存问题规则"""
        evidence = []
        confidence = 0.0
        
        log_patterns = log_result.get('analysis_result', {}).get('error_patterns', {})
        if 'out_of_memory' in str(log_patterns):
            evidence.append("日志包含 OutOfMemoryError")
            confidence += 0.4
        
        memory_metric = metric_result.get('metrics', {}).get('memory_usage', {})
        if memory_metric.get('exceeded_threshold'):
            evidence.append(f"内存使用率过高: {memory_metric.get('current_value')}%")
            confidence += 0.3
        
        if self._check_service_crash(log_result):
            evidence.append("服务因内存问题崩溃")
            confidence += 0.3
        
        if confidence > 0.5:
            return {
                "cause": "内存不足/内存泄漏",
                "confidence": min(confidence, 0.95),
                "evidence": evidence,
                "repair_action": "restart_service",
                "prevention": "增加内存监控告警，优化内存使用，检查内存泄漏"
            }
        return None
    
    def _rule_disk_issue(self, alert_group: Dict[str, Any],
                         log_result: Dict[str, Any],
                         metric_result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """磁盘问题规则"""
        evidence = []
        confidence = 0.0
        
        log_patterns = log_result.get('analysis_result', {}).get('error_patterns', {})
        if 'disk_full' in str(log_patterns):
            evidence.append("日志包含磁盘空间不足错误")
            confidence += 0.4
        
        disk_metric = metric_result.get('metrics', {}).get('disk_usage', {})
        if disk_metric.get('exceeded_threshold'):
            evidence.append(f"磁盘使用率过高: {disk_metric.get('current_value')}%")
            confidence += 0.4
        
        if confidence > 0.5:
            return {
                "cause": "磁盘空间不足",
                "confidence": min(confidence, 0.9),
                "evidence": evidence,
                "repair_action": "clean_disk",
                "prevention": "设置磁盘使用率告警，定期清理日志和临时文件"
            }
        return None
    
    def _rule_cpu_issue(self, alert_group: Dict[str, Any],
                        log_result: Dict[str, Any],
                        metric_result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """CPU 问题规则"""
        evidence = []
        confidence = 0.0
        
        cpu_metric = metric_result.get('metrics', {}).get('cpu_usage', {})
        if cpu_metric.get('exceeded_threshold'):
            evidence.append(f"CPU 使用率过高: {cpu_metric.get('current_value')}%")
            confidence += 0.4
        
        load_metric = metric_result.get('metrics', {}).get('load_average', {})
        if load_metric.get('exceeded_threshold'):
            evidence.append(f"系统负载过高: {load_metric.get('current_value')}")
            confidence += 0.3
        
        if confidence > 0.5:
            return {
                "cause": "CPU 资源不足",
                "confidence": min(confidence, 0.85),
                "evidence": evidence,
                "repair_action": "scale_up",
                "prevention": "优化代码性能，增加 CPU 资源，设置负载均衡"
            }
        return None
    
    def _rule_database_issue(self, alert_group: Dict[str, Any],
                            log_result: Dict[str, Any],
                            metric_result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """数据库问题规则"""
        evidence = []
        confidence = 0.0
        
        log_patterns = log_result.get('analysis_result', {}).get('error_patterns', {})
        if 'database_error' in str(log_patterns):
            evidence.append("日志包含数据库错误")
            confidence += 0.4
        
        db_metric = metric_result.get('metrics', {}).get('db_connections', {})
        if db_metric.get('exceeded_threshold'):
            evidence.append(f"数据库连接数过高: {db_metric.get('current_value')}")
            confidence += 0.3
        
        if confidence > 0.5:
            return {
                "cause": "数据库连接问题",
                "confidence": min(confidence, 0.85),
                "evidence": evidence,
                "repair_action": "clear_connections",
                "prevention": "优化数据库连接池配置，检查慢查询"
            }
        return None
    
    def _rule_network_issue(self, alert_group: Dict[str, Any],
                           log_result: Dict[str, Any],
                           metric_result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """网络问题规则"""
        evidence = []
        confidence = 0.0
        
        log_patterns = log_result.get('analysis_result', {}).get('error_patterns', {})
        if 'network_error' in str(log_patterns) or 'connection_timeout' in str(log_patterns):
            evidence.append("日志包含网络错误")
            confidence += 0.5
        
        if confidence > 0.5:
            return {
                "cause": "网络连接问题",
                "confidence": confidence,
                "evidence": evidence,
                "repair_action": "restart_service",
                "prevention": "检查网络配置，增加重试机制"
            }
        return None
    
    def _rule_application_error(self, alert_group: Dict[str, Any],
                               log_result: Dict[str, Any],
                               metric_result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """应用错误规则"""
        evidence = []
        confidence = 0.0
        
        stack_traces = log_result.get('analysis_result', {}).get('stack_traces', [])
        if stack_traces:
            exception_types = [trace.get('exception_type') for trace in stack_traces]
            evidence.append(f"发现异常: {', '.join(exception_types[:3])}")
            confidence += 0.5
        
        if log_result.get('analysis_result', {}).get('anomaly_score', 0) > 0.7:
            evidence.append("日志异常分数高")
            confidence += 0.3
        
        if confidence > 0.5:
            return {
                "cause": "应用程序错误",
                "confidence": min(confidence, 0.8),
                "evidence": evidence,
                "repair_action": "rollback",
                "prevention": "加强代码审查，增加单元测试覆盖率"
            }
        return None
    
    def _rule_service_crash(self, alert_group: Dict[str, Any],
                           log_result: Dict[str, Any],
                           metric_result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """服务崩溃规则"""
        evidence = []
        confidence = 0.0
        
        key_events = log_result.get('analysis_result', {}).get('key_events', [])
        crash_events = [e for e in key_events if 'crash' in e.get('event', '').lower() 
                       or 'fatal' in e.get('level', '').lower()]
        
        if crash_events:
            evidence.append(f"发现服务崩溃事件: {crash_events[0].get('event')}")
            confidence += 0.6
        
        if confidence > 0.5:
            return {
                "cause": "服务崩溃",
                "confidence": confidence,
                "evidence": evidence,
                "repair_action": "restart_service",
                "prevention": "增加服务健康检查，实现自动重启机制"
            }
        return None
    
    def _case_based_inference(self, alert_group: Dict[str, Any],
                             log_result: Dict[str, Any],
                             metric_result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """基于历史案例的推理"""
        hypotheses = []
        current_features = self._extract_features(alert_group, log_result, metric_result)
        
        for case in self.knowledge_base.get('cases', []):
            similarity = self._calculate_case_similarity(current_features, case.get('features', {}))
            if similarity > 0.6:
                hypotheses.append({
                    "cause": case.get('root_cause'),
                    "confidence": similarity * 0.8,
                    "evidence": [f"与历史案例相似 (相似度: {similarity:.2f})"],
                    "repair_action": case.get('repair_action'),
                    "prevention": case.get('prevention'),
                    "source": "historical_case",
                    "case_id": case.get('id')
                })
        
        return hypotheses
    
    def _extract_features(self, alert_group: Dict[str, Any],
                         log_result: Dict[str, Any],
                         metric_result: Dict[str, Any]) -> Dict[str, Any]:
        """提取故障特征"""
        features = {
            'services': alert_group.get('services', []),
            'severity': alert_group.get('severity'),
            'error_patterns': list(log_result.get('analysis_result', {}).get('error_patterns', {}).get('summary', [])),
            'anomaly_score': log_result.get('analysis_result', {}).get('anomaly_score', 0),
            'exceeded_metrics': [
                name for name, metric in metric_result.get('metrics', {}).items()
                if metric.get('exceeded_threshold')
            ]
        }
        return features
    
    def _calculate_case_similarity(self, features1: Dict[str, Any],
                                  features2: Dict[str, Any]) -> float:
        """计算案例相似度"""
        score = 0.0
        total_weight = 0.0
        
        if features1.get('services') and features2.get('services'):
            total_weight += 0.3
            common_services = set(features1['services']) & set(features2['services'])
            score += 0.3 * (len(common_services) / len(features1['services']))
        
        if features1.get('severity') and features2.get('severity'):
            total_weight += 0.2
            if features1['severity'] == features2['severity']:
                score += 0.2
        
        if features1.get('error_patterns') and features2.get('error_patterns'):
            total_weight += 0.3
            patterns1 = {p.get('pattern') for p in features1['error_patterns']}
            patterns2 = {p.get('pattern') for p in features2['error_patterns']}
            if patterns1 and patterns2:
                jaccard = len(patterns1 & patterns2) / len(patterns1 | patterns2)
                score += 0.3 * jaccard
        
        if features1.get('exceeded_metrics') and features2.get('exceeded_metrics'):
            total_weight += 0.2
            metrics1 = set(features1['exceeded_metrics'])
            metrics2 = set(features2['exceeded_metrics'])
            if metrics1 and metrics2:
                jaccard = len(metrics1 & metrics2) / len(metrics1 | metrics2)
                score += 0.2 * jaccard
        
        return score / total_weight if total_weight > 0 else 0.0
    
    def _combine_hypotheses(self, hypotheses: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """组合相似假设"""
        if not hypotheses:
            return []
        
        combined = defaultdict(lambda: {'evidence': [], 'confidence': 0.0, 'count': 0})
        
        for hyp in hypotheses:
            cause = hyp.get('cause')
            combined[cause]['evidence'].extend(hyp.get('evidence', []))
            combined[cause]['confidence'] += hyp.get('confidence', 0)
            combined[cause]['count'] += 1
            combined[cause]['repair_action'] = hyp.get('repair_action')
            combined[cause]['prevention'] = hyp.get('prevention')
        
        result = []
        for cause, data in combined.items():
            confidence = min(data['confidence'] / data['count'] + 0.1 * (data['count'] - 1), 0.95)
            result.append({
                'cause': cause,
                'confidence': confidence,
                'evidence': list(set(data['evidence'])),
                'repair_action': data['repair_action'],
                'prevention': data['prevention']
            })
        
        return result
    
    def _rank_hypotheses(self, hypotheses: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """对假设进行排序"""
        return sorted(hypotheses, key=lambda x: x.get('confidence', 0), reverse=True)
    
    def _check_service_crash(self, log_result: Dict[str, Any]) -> bool:
        """检查服务是否崩溃"""
        key_events = log_result.get('analysis_result', {}).get('key_events', [])
        return any('crash' in e.get('event', '').lower() or 
                  e.get('level') == 'FATAL' for e in key_events)
    
    def _load_knowledge_base(self) -> Dict[str, Any]:
        """加载知识库"""
        if os.path.exists(self.knowledge_base_path):
            try:
                with open(self.knowledge_base_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                self.logger.error(f"Failed to load knowledge base: {str(e)}")
        
        return {
            "cases": [
                {
                    "id": "case_001",
                    "root_cause": "内存溢出",
                    "features": {
                        "services": ["test-service"],
                        "severity": "critical",
                        "error_patterns": [{"pattern": "out_of_memory"}],
                        "exceeded_metrics": ["memory_usage"]
                    },
                    "repair_action": "restart_service",
                    "prevention": "增加内存限制，优化内存使用"
                }
            ]
        }
