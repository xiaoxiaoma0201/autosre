"""
AutoSRE Web API 服务
"""
from fastapi import FastAPI, HTTPException, BackgroundTasks, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime
import uvicorn
import json
import os

from agents.orchestrator import AutoSREOrchestrator
from agents.database import Database
from agents.auth import AuthService
from agents.metric_querier import MetricQuerierAgent
from agents.rbac import RBAC, Permission
from loguru import logger

# 初始化 FastAPI
app = FastAPI(title="AutoSRE API", version="1.1.0")

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 初始化服务
config = json.loads(open("config/autosre_config.json").read()) if os.path.exists("config/autosre_config.json") else {}
orchestrator = AutoSREOrchestrator(config)
metric_agent = MetricQuerierAgent()
database = Database()
auth_service = AuthService()
rbac = RBAC()

async def verify_api_key(x_api_key: str = Header(None)):
    """验证 API Key - 使用 RBAC"""
    if not x_api_key:
        raise HTTPException(status_code=401, detail="Missing API Key")
    
    # 使用 RBAC 检查权限
    if not rbac.check_permission(x_api_key, Permission.VIEW):
        raise HTTPException(status_code=401, detail="Invalid API Key")
    
    user = rbac.get_user_by_api_key(x_api_key)
    return user

async def verify_execute_permission(auth: dict = Depends(verify_api_key)):
    """验证执行权限"""
    api_key = auth.get('api_key', '') if isinstance(auth, dict) else ''
    if not api_key:
        raise HTTPException(status_code=401, detail="Invalid authentication")
    
    if not rbac.check_permission(api_key, Permission.EXECUTE):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    return auth

# 数据模型
class Alert(BaseModel):
    alertname: str
    service: str
    instance: str
    severity: str = "warning"
    timestamp: Optional[str] = None
    annotations: Optional[Dict[str, str]] = {}
    labels: Optional[Dict[str, str]] = {}

class AlertBatch(BaseModel):
    alerts: List[Alert]

class IncidentResponse(BaseModel):
    incident_id: str
    status: str
    summary: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

@app.get("/")
async def root():
    """返回 Web UI"""
    web_ui_path = "web_ui.html"
    if os.path.exists(web_ui_path):
        from fastapi.responses import FileResponse
        return FileResponse(web_ui_path)
    return {"service": "AutoSRE", "status": "running"}

@app.post("/api/v1/login")
async def login(username: str, password: str):
    """登录获取 Token"""
    if username == "admin" and password == "admin123":
        token = auth_service.create_token(username, "admin")
        return {"token": token, "token_type": "bearer"}
    raise HTTPException(status_code=401, detail="Invalid credentials")

@app.get("/health")
async def health():
    """健康检查"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.1.0"
    }

@app.post("/api/v1/incidents", response_model=IncidentResponse)
async def create_incident(alert_batch: AlertBatch, background_tasks: BackgroundTasks, auth: dict = Depends(verify_execute_permission)):
    """创建故障处理任务（需要执行权限）"""
    try:
        alerts = [alert.dict() for alert in alert_batch.alerts]
        background_tasks.add_task(orchestrator.handle_incident, alerts)
        return {
            "incident_id": "pending",
            "status": "processing",
            "summary": {"received_alerts": len(alerts)}
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/incidents/sync", response_model=IncidentResponse)
async def handle_incident_sync(alert_batch: AlertBatch, auth: dict = Depends(verify_execute_permission)):
    """同步处理故障（需要执行权限）"""
    try:
        alerts = [alert.dict() for alert in alert_batch.alerts]
        result = orchestrator.handle_incident(alerts)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/metrics")
async def get_metrics(auth: dict = Depends(verify_api_key)):
    """获取当前指标"""
    try:
        from datetime import timedelta
        alert_group = {
            "group_id": "api_query",
            "start_time": (datetime.now() - timedelta(minutes=5)).isoformat(),
            "end_time": datetime.now().isoformat()
        }
        result = metric_agent.process({"alert_group": alert_group})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/stats")
async def get_stats(auth: dict = Depends(verify_api_key)):
    """获取统计信息"""
    try:
        return database.get_incident_stats()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/incidents/recent")
async def get_recent_incidents(auth: dict = Depends(verify_api_key)):
    """获取最近的故障记录"""
    try:
        return database.get_recent_incidents(10)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/reports")
async def list_reports(auth: dict = Depends(verify_api_key)):
    """列出所有报告"""
    reports = []
    reports_dir = "reports"
    if os.path.exists(reports_dir):
        for filename in os.listdir(reports_dir):
            if filename.endswith("_report.md"):
                filepath = os.path.join(reports_dir, filename)
                reports.append({
                    "filename": filename,
                    "created_at": datetime.fromtimestamp(os.path.getmtime(filepath)).isoformat(),
                    "size": os.path.getsize(filepath)
                })
    return {"reports": reports}

@app.get("/api/v1/reports/{filename}")
async def get_report(filename: str, auth: dict = Depends(verify_api_key)):
    """获取报告内容"""
    filepath = os.path.join("reports", filename)
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        return {"filename": filename, "content": content}
    raise HTTPException(status_code=404, detail="Report not found")

@app.get("/api/v1/users")
async def list_users(auth: dict = Depends(verify_api_key)):
    """列出所有用户（需要管理权限）"""
    try:
        return rbac.list_users()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=9999)