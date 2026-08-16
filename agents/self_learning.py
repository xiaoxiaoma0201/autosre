"""
知识库自学习模块 - 从历史故障中自动学习
"""
import json
import os
from typing import Dict, Any, List, Optional
from datetime import datetime
from loguru import logger


class SelfLearning:
    """知识库自学习引擎"""
    
    def __init__(self, learning_data_path: str = "config/agents/learning_data.json"):
        self.learning_data_path = learning_data_path
        self.learning_data = self._load()
        
    def _load(self) -> List[Dict[str, Any]]:
        """加载学习数据"""
        if os.path.exists(self.learning_data_path):
            try:
                with open(self.learning_data_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return []
    
    def _save(self):
        """保存学习数据"""
        os.makedirs(os.path.dirname(self.learning_data_path), exist_ok=True)
        with open(self.learning_data_path, 'w', encoding='utf-8') as f:
            json.dump(self.learning_data, f, indent=2, ensure_ascii=False)
    
    def learn_from_incident(self, incident_result: Dict[str, Any]) -> bool:
        """从故障处理结果中学习"""
        try:
            summary = incident_result.get('summary', {})
            
            # 提取学习样本
            sample = {
                "timestamp": datetime.now().isoformat(),
                "total_alerts": summary.get('total_alerts', 0),
                "alert_groups": summary.get('alert_groups', 0),
                "top_causes": summary.get('top_causes', []),
                "success": incident_result.get('status') == 'completed'
            }
            
            # 添加到学习数据
            self.learning_data.append(sample)
            
            # 限制学习数据大小（最多保留1000条）
            if len(self.learning_data) > 1000:
                self.learning_data = self.learning_data[-1000:]
            
            self._save()
            logger.info(f"已学习新故障案例，当前样本数: {len(self.learning_data)}")
            return True
        except Exception as e:
            logger.error(f"学习失败: {str(e)}")
            return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取学习统计"""
        total = len(self.learning_data)
        success = sum(1 for d in self.learning_data if d.get('success'))
        
        # 统计最常见的根因
        cause_counter = {}
        for d in self.learning_data:
            for cause in d.get('top_causes', []):
                name = cause.get('cause', 'unknown')
                cause_counter[name] = cause_counter.get(name, 0) + 1
        
        top_causes = sorted(cause_counter.items(), key=lambda x: x[1], reverse=True)[:5]
        
        return {
            "total_samples": total,
            "success_rate": success / total if total > 0 else 0,
            "top_causes": [{"cause": c, "count": n} for c, n in top_causes]
        }
    
    def find_similar_cases(self, alertname: str, limit: int = 3) -> List[Dict[str, Any]]:
        """查找相似的历史案例"""
        similar = []
        for d in self.learning_data:
            for cause in d.get('top_causes', []):
                if alertname.lower() in cause.get('cause', '').lower():
                    similar.append(d)
                    break
        return similar[-limit:]