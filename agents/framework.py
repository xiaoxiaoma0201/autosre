"""
Agent 框架 - 可扩展的多 Agent 协作框架
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from loguru import logger
import asyncio
import uuid


class AgentStatus(Enum):
    """Agent 状态"""
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    WAITING = "waiting"


@dataclass
class AgentContext:
    """Agent 执行上下文"""
    incident_id: str
    data: Dict[str, Any] = field(default_factory=dict)
    results: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentResult:
    """Agent 执行结果"""
    success: bool
    data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    duration: float = 0.0


class BaseAgentV2(ABC):
    """可扩展的 Agent 基类"""
    
    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self.status = AgentStatus.IDLE
        self.context: Optional[AgentContext] = None
        self.logger = logger.bind(agent=name)
        
    @abstractmethod
    async def execute(self, context: AgentContext) -> AgentResult:
        """执行 Agent 逻辑"""
        pass
    
    def can_handle(self, context: AgentContext) -> bool:
        """判断是否可以处理该上下文"""
        return True
    
    async def run(self, context: AgentContext) -> AgentResult:
        """运行 Agent"""
        import time
        start_time = time.time()
        self.status = AgentStatus.RUNNING
        self.context = context
        self.logger.info(f"Agent {self.name} started")
        
        try:
            result = await self.execute(context)
            self.status = AgentStatus.COMPLETED if result.success else AgentStatus.FAILED
            result.duration = time.time() - start_time
            self.logger.info(f"Agent {self.name} completed in {result.duration:.2f}s")
            return result
        except Exception as e:
            self.status = AgentStatus.FAILED
            self.logger.error(f"Agent {self.name} failed: {str(e)}")
            return AgentResult(
                success=False,
                error=str(e),
                duration=time.time() - start_time
            )


class AgentPipeline:
    """Agent 流水线 - 管理多个 Agent 的执行"""
    
    def __init__(self):
        self.agents: List[BaseAgentV2] = []
        self.hooks: Dict[str, List[Callable]] = {
            "before_agent": [],
            "after_agent": [],
            "on_error": []
        }
        
    def add_agent(self, agent: BaseAgentV2) -> 'AgentPipeline':
        """添加 Agent"""
        self.agents.append(agent)
        return self
    
    def add_hook(self, event: str, callback: Callable) -> 'AgentPipeline':
        """添加钩子"""
        if event in self.hooks:
            self.hooks[event].append(callback)
        return self
    
    async def execute(self, context: AgentContext) -> List[AgentResult]:
        """执行流水线"""
        results = []
        
        for agent in self.agents:
            # 执行前置钩子
            for hook in self.hooks["before_agent"]:
                hook(agent, context)
            
            # 执行 Agent
            try:
                result = await agent.run(context)
                results.append(result)
                
                # 将结果合并到上下文
                context.results[agent.name] = result.data
                
            except Exception as e:
                logger.error(f"Pipeline error at {agent.name}: {str(e)}")
                for hook in self.hooks["on_error"]:
                    hook(agent, context, e)
            
            # 执行后置钩子
            for hook in self.hooks["after_agent"]:
                hook(agent, context, result)
        
        return results


class AgentFactory:
    """Agent 工厂 - 动态创建 Agent"""
    
    _registry: Dict[str, type] = {}
    
    @classmethod
    def register(cls, name: str):
        """注册 Agent 类"""
        def decorator(agent_class):
            cls._registry[name] = agent_class
            return agent_class
        return decorator
    
    @classmethod
    def create(cls, name: str, **kwargs) -> BaseAgentV2:
        """创建 Agent 实例"""
        if name not in cls._registry:
            raise ValueError(f"Unknown agent type: {name}")
        return cls._registry[name](**kwargs)
    
    @classmethod
    def list_agents(cls) -> List[str]:
        """列出所有注册的 Agent"""
        return list(cls._registry.keys())
