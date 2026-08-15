"""
消息总线 - 定义 Agent 间通信的数据格式和协议
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from enum import Enum
from datetime import datetime
import json
import uuid


class MessageType(Enum):
    """消息类型枚举"""
    ALERT_BATCH = "alert_batch"
    ALERT_CONVERGED = "alert_converged"
    LOG_ANALYSIS_RESULT = "log_analysis_result"
    METRIC_QUERY_RESULT = "metric_query_result"
    ROOT_CAUSE_HYPOTHESIS = "root_cause_hypothesis"
    REPAIR_ACTION = "repair_action"
    REPAIR_RESULT = "repair_result"
    REPORT_GENERATED = "report_generated"
    ERROR = "error"
    HEARTBEAT = "heartbeat"


@dataclass
class AgentMessage:
    """Agent 间通信的消息格式"""
    msg_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    msg_type: MessageType = MessageType.HEARTBEAT
    sender: str = "unknown"
    timestamp: datetime = field(default_factory=datetime.now)
    payload: Dict[str, Any] = field(default_factory=dict)
    correlation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "msg_id": self.msg_id,
            "msg_type": self.msg_type.value,
            "sender": self.sender,
            "timestamp": self.timestamp.isoformat(),
            "payload": self.payload,
            "correlation_id": self.correlation_id,
            "metadata": self.metadata
        }
    
    def to_json(self) -> str:
        """转换为 JSON 字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AgentMessage':
        """从字典创建消息对象"""
        return cls(
            msg_id=data.get("msg_id", str(uuid.uuid4())),
            msg_type=MessageType(data.get("msg_type", "heartbeat")),
            sender=data.get("sender", "unknown"),
            timestamp=datetime.fromisoformat(data.get("timestamp", datetime.now().isoformat())),
            payload=data.get("payload", {}),
            correlation_id=data.get("correlation_id", str(uuid.uuid4())),
            metadata=data.get("metadata", {})
        )


class MessageBus:
    """消息总线 - 管理 Agent 间的消息传递"""
    
    def __init__(self):
        self.messages: List[AgentMessage] = []
        self.subscribers: Dict[MessageType, List[callable]] = {}
        
    def publish(self, message: AgentMessage):
        """发布消息"""
        self.messages.append(message)
        if message.msg_type in self.subscribers:
            for callback in self.subscribers[message.msg_type]:
                callback(message)
                
    def subscribe(self, msg_type: MessageType, callback: callable):
        """订阅特定类型的消息"""
        if msg_type not in self.subscribers:
            self.subscribers[msg_type] = []
        self.subscribers[msg_type].append(callback)
        
    def get_messages_by_correlation(self, correlation_id: str) -> List[AgentMessage]:
        """根据关联 ID 获取消息"""
        return [msg for msg in self.messages if msg.correlation_id == correlation_id]
    
    def get_messages_by_type(self, msg_type: MessageType) -> List[AgentMessage]:
        """根据类型获取消息"""
        return [msg for msg in self.messages if msg.msg_type == msg_type]
    
    def clear(self):
        """清空消息历史"""
        self.messages.clear()
