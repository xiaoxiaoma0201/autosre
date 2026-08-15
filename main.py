#!/usr/bin/env python3
"""
AutoSRE 主入口 - 多 Agent 自动化运维排障系统
"""
import argparse
import json
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, Any, List
from loguru import logger

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agents.orchestrator import AutoSREOrchestrator
from agents.message_bus import MessageBus


def setup_logger(log_level: str = "INFO", log_file: str = "logs/autosre.log"):
    """配置日志"""
    os.makedirs("logs", exist_ok=True)
    
    logger.remove()  # 移除默认处理器
    logger.add(
        sys.stdout,
        level=log_level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan> - <level>{message}</level>"
    )
    logger.add(
        log_file,
        level=log_level,
        rotation="500 MB",
        retention="10 days",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name} - {message}"
    )


def load_config(config_path: str) -> Dict[str, Any]:
    """加载配置文件"""
    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def generate_test_alerts() -> List[Dict[str, Any]]:
    """生成测试告警"""
    now = datetime.now()
    alerts = [
        {
            "alertname": "HighMemoryUsage",
            "service": "test-service",
            "instance": "instance-1",
            "severity": "critical",
            "timestamp": (now - timedelta(minutes=5)).isoformat(),
            "annotations": {
                "summary": "Memory usage above 90%"
            },
            "labels": {
                "alertname": "HighMemoryUsage",
                "service": "test-service",
                "instance": "instance-1",
                "severity": "critical"
            }
        },
        {
            "alertname": "ServiceDown",
            "service": "test-service",
            "instance": "instance-1",
            "severity": "critical",
            "timestamp": (now - timedelta(minutes=3)).isoformat(),
            "annotations": {
                "summary": "Service is down"
            },
            "labels": {
                "alertname": "ServiceDown",
                "service": "test-service",
                "instance": "instance-1",
                "severity": "critical"
            }
        },
        {
            "alertname": "HighCPUUsage",
            "service": "test-service",
            "instance": "instance-2",
            "severity": "warning",
            "timestamp": (now - timedelta(minutes=2)).isoformat(),
            "annotations": {
                "summary": "CPU usage above 80%"
            },
            "labels": {
                "alertname": "HighCPUUsage",
                "service": "test-service",
                "instance": "instance-2",
                "severity": "warning"
            }
        }
    ]
    return alerts


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="AutoSRE - 多 Agent 自动化运维排障系统")
    parser.add_argument("--config", default="config/autosre_config.json", 
                       help="配置文件路径")
    parser.add_argument("--test", action="store_true", 
                       help="使用测试告警运行")
    parser.add_argument("--webhook", action="store_true", 
                       help="启动 webhook 服务器模式")
    parser.add_argument("--port", type=int, default=8080, 
                       help="Webhook 服务器端口")
    parser.add_argument("--log-level", default="INFO", 
                       help="日志级别 (DEBUG, INFO, WARNING, ERROR)")
    
    args = parser.parse_args()
    
    # 设置日志
    setup_logger(args.log_level)
    logger.info("Starting AutoSRE system...")
    
    # 加载配置
    config = load_config(args.config)
    config.update(vars(args))
    
    # 初始化编排器
    orchestrator = AutoSREOrchestrator(config)
    
    if args.test:
        # 测试模式
        logger.info("Running in test mode with sample alerts")
        test_alerts = generate_test_alerts()
        result = orchestrator.handle_incident(test_alerts)
        
        logger.info("=" * 60)
        logger.info("Incident handling completed")
        logger.info(f"Status: {result.get('status')}")
        if result.get('summary'):
            logger.info(f"Summary: {json.dumps(result['summary'], indent=2, ensure_ascii=False)}")
        logger.info("=" * 60)
        
    elif args.webhook:
        # Webhook 模式
        from flask import Flask, request, jsonify
        app = Flask(__name__)
        
        @app.route('/webhook', methods=['POST'])
        def webhook():
            """处理 Alertmanager webhook"""
            webhook_data = request.json
            logger.info(f"Received webhook: {json.dumps(webhook_data, indent=2)}")
            
            result = orchestrator.process_alert_webhook(webhook_data)
            return jsonify(result)
        
        @app.route('/health', methods=['GET'])
        def health():
            """健康检查"""
            return jsonify({"status": "healthy", "timestamp": datetime.now().isoformat()})
        
        logger.info(f"Starting webhook server on port {args.port}")
        app.run(host='0.0.0.0', port=args.port)
    
    else:
        # 交互模式
        logger.info("Entering interactive mode")
        logger.info("输入告警 JSON (每行一个) 输入 'quit' 退出 ")
        
        alerts = []
        while True:
            try:
                line = input().strip()
                if line.lower() == 'quit':
                    break
                if line:
                    alert = json.loads(line)
                    alerts.append(alert)
                else:
                    # 空行表示开始处理
                    if alerts:
                        result = orchestrator.handle_incident(alerts)
                        logger.info(f"处理结果: {json.dumps(result['summary'], indent=2, ensure_ascii=False)}")
                        alerts = []
            except json.JSONDecodeError:
                logger.error("无效的 JSON 格式")
            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"处理失败: {str(e)}")


if __name__ == "__main__":
    main()