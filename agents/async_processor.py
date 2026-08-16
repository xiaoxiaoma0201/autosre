"""
异步处理模块 - 并发处理多个告警组
"""
import asyncio
from typing import List, Dict, Any
from loguru import logger


class AsyncProcessor:
    """异步处理器"""
    
    def __init__(self, max_concurrency: int = 5):
        self.max_concurrency = max_concurrency
        self.semaphore = asyncio.Semaphore(max_concurrency)
        
    async def process_with_semaphore(self, func, *args, **kwargs):
        """使用信号量限制并发"""
        async with self.semaphore:
            return await func(*args, **kwargs)
    
    async def process_multiple(self, orchestrator, alert_groups: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """并发处理多个告警组"""
        tasks = []
        for group in alert_groups:
            task = self.process_with_semaphore(
                self._process_single_group,
                orchestrator,
                group
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理异常
        processed = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"告警组 {i} 处理失败: {str(result)}")
                processed.append({"status": "failed", "error": str(result)})
            else:
                processed.append(result)
        
        return processed
    
    async def _process_single_group(self, orchestrator, alert_group: Dict[str, Any]) -> Dict[str, Any]:
        """处理单个告警组"""
        group_id = alert_group.get('group_id', 'unknown')
        logger.info(f"异步处理告警组: {group_id}")
        
        # 这里调用编排器的同步处理逻辑
        # 由于编排器是同步的，这里用 run_in_executor 包装
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            orchestrator.handle_incident,
            alert_group.get('alerts', [])
        )
        
        return {
            "group_id": group_id,
            "status": result.get('status', 'unknown'),
            "summary": result.get('summary', {})
        }