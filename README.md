# AutoSRE - 多 Agent 自动化运维排障系统

AutoSRE 是一个基于多 Agent 协作的智能运维排障系统。

## 核心特性

- 6 个协作 Agent（告警收敛、日志分析、指标查询、根因推理、修复执行、报告生成）
- LLM 深度分析（DeepSeek V4 Flash）
- Prometheus + Docker 真实集成
- 钉钉通知 + SQLite 存储
- Web 控制台 + API 认证

## 快速开始

pip install -r requirements.txt
python api_server.py

## 访问

- Web UI: http://localhost:9999
- API 文档: http://localhost:9999/docs

## 测试

python -m pytest tests/ -v