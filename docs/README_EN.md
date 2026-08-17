# AutoSRE - Multi-Agent Automated SRE System

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.8+-green.svg)

> 📖 [中文版](../README.md)

AutoSRE is an intelligent SRE system based on multi-agent collaboration.

## Key Features

- 🤖 **6+ Collaborative Agents** - Alert convergence, log analysis, metric query, root cause inference, repair execution, report generation
- 🧠 **LLM Deep Analysis** - DeepSeek V4 Flash integration
- 📊 **Real Monitoring** - Prometheus + Docker + Alertmanager
- 🔮 **Predictive Maintenance** - Fault prediction
- 📚 **Self-Learning** - Knowledge base auto-update
- 🔐 **Security** - JWT + API Key + RBAC
- ⚡ **High Performance** - 100 alerts in 0.0008s

## Quick Start

```bash
git clone https://github.com/xiaoxiaoma0201/autosre.git
cd autosre
pip install -r requirements.txt
python api_server.py