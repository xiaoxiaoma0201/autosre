"""
Agent 基类 - 定义所有 Agent 的通用接口
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from loguru import logger
import uuid
from .message_bus import MessageBus, AgentMessage, MessageType


class BaseAgent(ABC):
    """所有 Agent 的基类"""
    
    def __init__(self, name: str, message_bus: Optional[MessageBus] = None):
        self.name = name
        self.message_bus = message_bus or MessageBus()
        self.logger = logger.bind(agent=name)
        
    def send_message(self, msg_type: MessageType, payload: Dict[str, Any], 
                     correlation_id: Optional[str] = None) -> AgentMessage:
        """发送消息到消息总线"""
        message = AgentMessage(
            msg_type=msg_type,
            sender=self.name,
            payload=payload,
            correlation_id=correlation_id or str(uuid.uuid4())
        )
        self.message_bus.publish(message)
        self.logger.info(f"Sent message: {msg_type.value}")
        return message
    
    def receive_message(self, message: AgentMessage) -> Dict[str, Any]:
        """接收消息"""
        self.logger.info(f"Received message from {message.sender}: {message.msg_type.value}")
        return message.payload
    
    @abstractmethod
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理输入数据，返回处理结果"""
        pass
    
    def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """运行 Agent"""
        self.logger.info(f"Agent {self.name} started")
        try:
            result = self.process(input_data)
            self.logger.info(f"Agent {self.name} completed")
            return result
        except Exception as e:
            self.logger.error(f"Agent {self.name} failed: {str(e)}")
            raise
