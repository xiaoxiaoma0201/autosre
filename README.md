# AutoSRE - 多 Agent 自动化运维排障系统

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.8+-green.svg)
![CI](https://github.com/xiaoxiaoma0201/autosre/actions/workflows/ci.yml/badge.svg)

> 📖 [English Version](docs/README_EN.md)

AutoSRE 是一个基于多 Agent 协作的智能运维排障系统，自动完成从告警接收到根因分析、修复建议、报告生成的全流程闭环。

## 核心特性

- 🤖 **6+ 协作 Agent** - 告警收敛、日志分析、指标查询、根因推理、修复执行、报告生成
- 🧠 **LLM 深度分析** - 集成 DeepSeek V4 Flash
- 📊 **真实监控集成** - Prometheus + Docker + Alertmanager
- 🔮 **预测性维护** - 基于历史数据预测潜在故障
- 📚 **自学习** - 知识库自动更新
- 🔐 **安全** - JWT + API Key + RBAC
- ⚡ **高性能** - 100 条告警仅 0.0008 秒
- 🐳 **Docker 部署** - 一键启动

## 快速开始

```bash
git clone https://github.com/xiaoxiaoma0201/autosre.git
cd autosre
pip install -r requirements.txt
python api_server.py