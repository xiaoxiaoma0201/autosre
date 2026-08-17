"""
预测性维护 Agent - 基于历史数据预测潜在故障
"""
import json
import os
from typing import Dict, Any, List
from datetime import datetime, timedelta
from collections import Counter
from loguru import logger
from .base_agent import BaseAgent
from .message_bus import MessageType


class PredictiveAgent(BaseAgent):
    """预测性维护 Agent"""
    
    def __init__(self, name: str = "predictive_agent", message_bus=None):
        super().__init__(name, message_bus)
        self.learning_data_path = "config/agents/learning_data.json"
        
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """分析历史数据，预测潜在风险"""
        history = self._load_history()
        
        if not history:
            return {"predictions": [], "message": "历史数据不足"}
        
        predictions = self._analyze_patterns(history)
        
        result = {
            "predictions": predictions,
            "risk_level": self._calculate_risk_level(predictions),
            "timestamp": datetime.now().isoformat()
        }
        
        self.send_message(MessageType.ALERT_BATCH, result)
        return result
    
    def _load_history(self) -> List[Dict[str, Any]]:
        """加载历史学习数据"""
        if os.path.exists(self.learning_data_path):
            try:
                with open(self.learning_data_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return []
    
    def _analyze_patterns(self, history: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """分析故障模式"""
        predictions = []
        
        # 统计最常见的故障类型
        cause_counter = Counter()
        for incident in history:
            for cause in incident.get('top_causes', []):
                name = cause.get('cause', 'unknown')
                cause_counter[name] += 1
        
        # 找出高频故障
        total = len(history)
        for cause, count in cause_counter.most_common(5):
            frequency = count / total if total > 0 else 0
            if frequency > 0.3:  # 出现频率超过30%
                predictions.append({
                    "cause": cause,
                    "frequency": frequency,
                    "risk": "high" if frequency > 0.5 else "medium",
                    "suggestion": f"建议重点关注: {cause}，历史出现频率 {frequency:.0%}"
                })
        
        return predictions
    
    def _calculate_risk_level(self, predictions: List[Dict[str, Any]]) -> str:
        """计算整体风险等级"""
        if not predictions:
            return "low"
        
        high_risks = [p for p in predictions if p.get('risk') == 'high']
        if high_risks:
            return "high"
        
        medium_risks = [p for p in predictions if p.get('risk') == 'medium']
        if medium_risks:
            return "medium"
        
        return "low"