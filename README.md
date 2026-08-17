# AutoSRE - 多 Agent 自动化运维排障系统
# AutoSRE - Multi-Agent Automated SRE System

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.8+-green.svg)
![CI](https://github.com/xiaoxiaoma0201/autosre/actions/workflows/ci.yml/badge.svg)

[English](#english) | [中文](#中文)

---

<a name="english"></a>
## English

AutoSRE is an intelligent SRE (Site Reliability Engineering) system based on multi-agent collaboration. It automatically completes the full workflow from alert reception to root cause analysis, repair suggestions, and report generation.

### Key Features

- 🤖 **6+ Collaborative Agents** - Alert convergence, log analysis, metric query, root cause inference, repair execution, report generation
- 🧠 **LLM Deep Analysis** - Integrated with DeepSeek V4 Flash
- 📊 **Real Monitoring Integration** - Prometheus + Docker + Alertmanager
- 🔮 **Predictive Maintenance** - Fault prediction based on historical data
- 📚 **Self-Learning** - Knowledge base auto-update
- 🔐 **Security** - JWT + API Key + RBAC
- ⚡ **High Performance** - 100 alerts in 0.0008s
- 🐳 **Docker Ready** - One-click deployment

### Quick Start

```bash
git clone https://github.com/xiaoxiaoma0201/autosre.git
cd autosre
pip install -r requirements.txt
python api_server.py