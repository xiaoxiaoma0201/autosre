"""
LLM 分析模块 - 集成 DeepSeek V4 Flash
"""
import json
from typing import Dict, Any, Optional
from loguru import logger


class LLMAnalyzer:
    """LLM 分析器 - 使用 DeepSeek V4 Flash"""
    
    def __init__(self, api_key: Optional[str] = None, 
                 model: str = "deepseek-v4-flash",
                 base_url: str = "https://api.deepseek.com"):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self.enabled = api_key is not None
        
        if self.enabled:
            logger.info(f"DeepSeek LLM 已启用: {model}")
        else:
            logger.info("LLM 未启用（未配置 API key）")
    
    def analyze_incident(self, incident_data: Dict[str, Any]) -> Dict[str, Any]:
        """使用 LLM 分析故障"""
        if not self.enabled:
            return {
                "enabled": False,
                "message": "LLM 未启用"
            }
        
        try:
            prompt = self._build_prompt(incident_data)
            analysis = self._call_deepseek(prompt)
            
            return {
                "enabled": True,
                "analysis": analysis,
                "model": self.model
            }
        except Exception as e:
            logger.error(f"LLM 分析失败: {str(e)}")
            return {
                "enabled": True,
                "error": str(e)
            }
    
    def _build_prompt(self, incident_data: Dict[str, Any]) -> str:
        """构建分析提示词"""
        alerts = incident_data.get('alerts', [])
        metrics = incident_data.get('metrics', {})
        root_cause = incident_data.get('root_cause', {})
        
        prompt = f"""你是一个资深的 SRE 专家。请分析以下系统故障：

## 告警信息
{json.dumps(alerts, ensure_ascii=False, indent=2)}

## 指标异常
{json.dumps(metrics, ensure_ascii=False, indent=2)}

## 当前根因分析
{json.dumps(root_cause, ensure_ascii=False, indent=2)}

请提供：
1. **根因分析**：更准确的根因判断
2. **修复步骤**：具体的修复操作
3. **预防措施**：长期预防建议
4. **风险评估**：故障影响和风险等级
"""
        return prompt
    
    def _call_deepseek(self, prompt: str) -> str:
        """调用 DeepSeek API（使用 requests 直接调用）"""
        import requests
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "你是 SRE 专家，擅长分析系统故障。"},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3,
            "max_tokens": 8000
        }
        
        response = requests.post(
            f"{self.base_url}/v1/chat/completions",
            headers=headers,
            json=data,
            timeout=120
        )
        
        if response.status_code == 200:
            result = response.json()
            return result['choices'][0]['message']['content']
        else:
            error_msg = response.json().get('error', {}).get('message', response.text)
            raise Exception(f"DeepSeek API 错误 ({response.status_code}): {error_msg}")
    
    def enhance_root_cause(self, root_cause: Dict[str, Any], 
                          incident_data: Dict[str, Any]) -> Dict[str, Any]:
        """使用 LLM 增强根因分析"""
        if not self.enabled:
            return root_cause
        
        try:
            analysis = self.analyze_incident(incident_data)
            if analysis.get('enabled') and analysis.get('analysis'):
                root_cause['llm_analysis'] = analysis['analysis']
                logger.info("LLM 已增强根因分析")
        except Exception as e:
            logger.warning(f"LLM 增强失败: {str(e)}")
        
        return root_cause
