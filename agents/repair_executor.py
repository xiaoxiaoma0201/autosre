"""
修复执行 Agent - 根据根因执行预定义修复动作
"""
from typing import Dict, Any, Optional
from datetime import datetime
from enum import Enum
from .base_agent import BaseAgent
from .message_bus import MessageType


class RepairAction(Enum):
    """修复动作枚举"""
    RESTART_SERVICE = "restart_service"
    CLEAN_DISK = "clean_disk"
    SCALE_UP = "scale_up"
    ROLLBACK = "rollback"
    CLEAR_CONNECTIONS = "clear_connections"
    NONE = "none"


class RepairExecutorAgent(BaseAgent):
    """修复执行 Agent"""
    
    def __init__(self, name: str = "repair_executor", message_bus=None,
                 docker_compose_path: str = ".", auto_execute: bool = False):
        super().__init__(name, message_bus)
        self.docker_compose_path = docker_compose_path
        self.auto_execute = auto_execute
        
        self.repair_actions = {
            RepairAction.RESTART_SERVICE.value: self._restart_service,
            RepairAction.CLEAN_DISK.value: self._clean_disk,
            RepairAction.SCALE_UP.value: self._scale_up,
            RepairAction.ROLLBACK.value: self._rollback,
            RepairAction.CLEAR_CONNECTIONS.value: self._clear_connections,
        }
        
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理修复执行"""
        root_cause = input_data.get("root_cause", {})
        if not root_cause:
            return {"error": "No root cause provided"}
        
        top_hypothesis = root_cause.get("top_hypothesis", {})
        confidence = root_cause.get("confidence", 0)
        
        if confidence < 0.6:
            return {
                "executed": False,
                "reason": f"置信度不足 ({confidence:.2f} < 0.6)，跳过自动修复",
                "timestamp": datetime.now().isoformat()
            }
        
        repair_action = top_hypothesis.get("repair_action", RepairAction.NONE.value)
        
        if not self.auto_execute:
            return {
                "executed": False,
                "reason": f"需要人工确认修复动作: {repair_action}",
                "suggested_action": repair_action,
                "root_cause": top_hypothesis.get("cause"),
                "confidence": confidence,
                "timestamp": datetime.now().isoformat()
            }
        
        try:
            result = self._execute_repair(repair_action, top_hypothesis)
            return {
                "executed": True,
                "action": repair_action,
                "result": result,
                "root_cause": top_hypothesis.get("cause"),
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "executed": False,
                "action": repair_action,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def _execute_repair(self, action: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """执行修复动作"""
        if action not in self.repair_actions:
            return {"success": False, "error": f"Unknown repair action: {action}"}
        
        self.logger.info(f"Executing repair action: {action}")
        try:
            result = self.repair_actions[action](context)
            self.logger.info(f"Repair action {action} completed successfully")
            
            self.send_message(MessageType.REPAIR_RESULT, {
                "action": action,
                "success": True,
                "result": result,
                "timestamp": datetime.now().isoformat()
            })
            
            return {"success": True, "result": result}
        except Exception as e:
            self.logger.error(f"Repair action {action} failed: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def _restart_service(self, context: Dict[str, Any]) -> str:
        """重启服务"""
        service_name = context.get("service", "")
        if service_name:
            return f"Service {service_name} restarted successfully (simulated)"
        return "Service restarted (simulated)"
    
    def _clean_disk(self, context: Dict[str, Any]) -> str:
        """清理磁盘"""
        logs_path = context.get("logs_path", "/var/log")
        return f"Cleaned up old log files in {logs_path} (simulated)"
    
    def _scale_up(self, context: Dict[str, Any]) -> str:
        """扩容"""
        service_name = context.get("service", "")
        replicas = context.get("replicas", 3)
        return f"Service {service_name} scaled to {replicas} replicas (simulated)"
    
    def _rollback(self, context: Dict[str, Any]) -> str:
        """回滚版本"""
        version = context.get("target_version", "previous")
        return f"Rolled back to {version} version (simulated)"
    
    def _clear_connections(self, context: Dict[str, Any]) -> str:
        """清理数据库连接"""
        db_name = context.get("database", "default")
        return f"Cleared database connections for {db_name} (simulated)"
