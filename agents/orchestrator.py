"""
协调器 - 编排所有 Agent 完成完整的排障流程
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid
from loguru import logger
from .message_bus import MessageBus
from .alert_convergence import AlertConvergenceAgent
from .log_analyzer import LogAnalyzerAgent
from .metric_querier import MetricQuerierAgent
from .root_cause import RootCauseAgent
from .repair_executor import RepairExecutorAgent
from .report_generator import ReportGeneratorAgent
from .database import Database
from .self_learning import SelfLearning
from .notification import NotificationService


class AutoSREOrchestrator:
    """AutoSRE 编排器"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.message_bus = MessageBus()
        
        self.alert_agent = AlertConvergenceAgent(
            message_bus=self.message_bus,
            time_window=self.config.get('alert_time_window', 300),
            similarity_threshold=self.config.get('similarity_threshold', 0.6)
        )
        
        self.log_agent = LogAnalyzerAgent(
            message_bus=self.message_bus
        )
        
        self.metric_agent = MetricQuerierAgent(
            message_bus=self.message_bus,
            prometheus_url=self.config.get('prometheus_url', 'http://localhost:9090')
        )
        
        self.root_cause_agent = RootCauseAgent(
            message_bus=self.message_bus,
            knowledge_base_path=self.config.get('knowledge_base_path', 'config/agents/knowledge_base.json')
        )
        
        self.repair_agent = RepairExecutorAgent(
            message_bus=self.message_bus,
            docker_compose_path=self.config.get('docker_compose_path', '.'),
            auto_execute=self.config.get('auto_execute', False)
        )
        
        self.report_agent = ReportGeneratorAgent(
            message_bus=self.message_bus,
            report_dir=self.config.get('report_dir', 'reports')
        )
        
        # 初始化数据库
        try:
            from .database import Database
            self.database = Database(self.config.get('db_path', 'autosre.db'))
        except Exception as e:
            logger.warning(f"Database init failed: {str(e)}")
            self.database = None
        
        # 初始化通知服务
        self.notification = None
        try:
            from .notification import NotificationService
            self.notification = NotificationService(self.config)
        except Exception as e:
            logger.warning(f"Notification init failed: {str(e)}")
        
                # 初始化自学习
        self.learning = SelfLearning()
        logger.info("AutoSRE Orchestrator initialized")
    
    def handle_incident(self, alerts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """处理一次完整的故障事件"""
        incident_id = str(uuid.uuid4())
        logger.info(f"Starting incident handling: {incident_id}")
        
        try:
            # 1. 告警收敛
            logger.info("Step 1: Alert convergence")
            convergence_result = self.alert_agent.process({"alerts": alerts})
            alert_groups = convergence_result.get("alert_groups", [])
            
            if not alert_groups:
                logger.warning("No alert groups found")
                result = {
                    "incident_id": incident_id,
                    "status": "no_alerts",
                    "summary": {"total_alerts": 0, "alert_groups": 0},
                    "results": []
                }
                return result
            
            # 处理每个告警组
            all_results = []
            for alert_group in alert_groups:
                logger.info(f"Processing alert group: {alert_group.get('group_id')}")
                
                # 2. 日志分析
                logger.info("Step 2: Log analysis")
                log_result = self.log_agent.process({"alert_group": alert_group})
                
                # 3. 指标查询
                logger.info("Step 3: Metric query")
                metric_result = self.metric_agent.process({"alert_group": alert_group})
                
                # 4. 根因推理
                logger.info("Step 4: Root cause analysis")
                root_cause = self.root_cause_agent.process({
                    "alert_group": alert_group,
                    "log_result": log_result,
                    "metric_result": metric_result
                })
                
                # 5. 修复执行
                logger.info("Step 5: Repair execution")
                repair_result = self.repair_agent.process({
                    "root_cause": root_cause,
                    "alert_group": alert_group
                })
                
                # 6. 生成报告
                logger.info("Step 6: Report generation")
                report_result = self.report_agent.process({
                    "incident_id": incident_id,
                    "alert_group": alert_group,
                    "log_result": log_result,
                    "metric_result": metric_result,
                    "root_cause": root_cause,
                    "repair_result": repair_result
                })
                
                group_result = {
                    "group_id": alert_group.get("group_id"),
                    "alert_group": alert_group,
                    "log_result": log_result,
                    "metric_result": metric_result,
                    "root_cause": root_cause,
                    "repair_result": repair_result,
                    "report_result": report_result
                }
                all_results.append(group_result)
            
            # 汇总结果
            summary = self._generate_summary(incident_id, all_results)
            
            logger.info(f"Incident handling completed: {incident_id}")
            
            final_result = {
                "incident_id": incident_id,
                "status": "completed",
                "summary": summary,
                "results": all_results
            }
            
                        # 知识库自学习
            try:
                self.learning.learn_from_incident(final_result)
                logger.info("已从本次故障中学习")
            except Exception as e:
                logger.warning(f"自学习失败: {str(e)}")
            
            # 发送钉钉通知
            if self.notification:
                try:
                    self.notification.send_incident_notification(final_result)
                    logger.info("钉钉通知已发送")
                except Exception as e:
                    logger.warning(f"发送钉钉通知失败: {str(e)}")
            
            # 保存到数据库
            if self.database:
                try:
                    self.database.save_incident(final_result)
                    logger.info(f"Incident saved to database: {incident_id}")
                except Exception as e:
                    logger.warning(f"Failed to save incident: {str(e)}")
            
            return final_result
            
        except Exception as e:
            logger.error(f"Incident handling failed: {str(e)}")
            result = {
                "incident_id": incident_id,
                "status": "failed",
                "error": str(e),
                "summary": {"total_alerts": len(alerts), "alert_groups": 0},
                "results": []
            }
            return result
    
    def _generate_summary(self, incident_id: str, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """生成处理摘要"""
        total_alerts = sum(r['alert_group'].get('alert_count', 0) for r in results)
        total_groups = len(results)
        repaired = sum(1 for r in results if r['repair_result'].get('executed', False))
        
        top_causes = []
        for r in results:
            root_cause = r.get('root_cause', {})
            top_hypothesis = root_cause.get('top_hypothesis') or {}
            if top_hypothesis.get('cause'):
                top_causes.append({
                    'group_id': r['group_id'],
                    'cause': top_hypothesis.get('cause', 'unknown'),
                    'confidence': root_cause.get('confidence', 0)
                })
        
        return {
            'incident_id': incident_id,
            'total_alerts': total_alerts,
            'alert_groups': total_groups,
            'repaired_groups': repaired,
            'top_causes': top_causes,
            'reports_generated': len(results),
            'timestamp': datetime.now().isoformat()
        }
