"""
性能压测工具 - 测试系统处理能力
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
from datetime import datetime
from agents.alert_convergence import AlertConvergenceAgent
from agents.cache import LRUCache
from loguru import logger


def benchmark_alert_convergence():
    """压测告警收敛"""
    agent = AlertConvergenceAgent()
    
    # 生成测试告警
    alerts = []
    now = datetime.now()
    for i in range(100):
        alerts.append({
            "alertname": f"Alert{i % 5}",
            "service": f"svc-{i % 3}",
            "instance": f"inst-{i % 10}",
            "severity": "warning",
            "timestamp": now.isoformat()
        })
    
    # 测试性能
    start = time.time()
    result = agent.process({"alerts": alerts})
    elapsed = time.time() - start
    
    print(f"告警收敛性能: {len(alerts)} 条告警耗时 {elapsed:.4f} 秒")
    print(f"收敛结果: {result['total_groups']} 个告警组")
    return elapsed


def benchmark_cache():
    """压测缓存"""
    cache = LRUCache(capacity=1000, ttl=60)
    
    # 写入测试
    start = time.time()
    for i in range(10000):
        cache.set(f"key-{i}", f"value-{i}")
    write_elapsed = time.time() - start
    
    # 读取测试
    start = time.time()
    hits = 0
    for i in range(10000):
        if cache.get(f"key-{i}"):
            hits += 1
    read_elapsed = time.time() - start
    
    print(f"缓存写入: 10000 条耗时 {write_elapsed:.4f} 秒")
    print(f"缓存读取: 10000 条耗时 {read_elapsed:.4f} 秒, 命中 {hits}")
    return write_elapsed + read_elapsed


if __name__ == "__main__":
    print("=" * 50)
    print("AutoSRE 性能压测")
    print("=" * 50)
    
    print("\n[1] 告警收敛压测")
    benchmark_alert_convergence()
    
    print("\n[2] 缓存压测")
    benchmark_cache()
    
    print("\n" + "=" * 50)
    print("压测完成")
    print("=" * 50)