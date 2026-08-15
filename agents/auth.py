"""
API 认证模块 - JWT Token 认证
"""
import jwt
import json
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from loguru import logger


class AuthService:
    """认证服务"""
    
    def __init__(self, secret_key: str = "autosre-secret-key-2024", 
                 token_expiry: int = 3600):
        self.secret_key = secret_key
        self.token_expiry = token_expiry  # 秒
        self.api_keys = self._load_api_keys()
        
    def _load_api_keys(self) -> Dict[str, str]:
        """加载 API Keys"""
        try:
            with open("config/api_keys.json", 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            # 默认 API Keys
            default_keys = {
                "admin": "autosre-admin-2024",
                "viewer": "autosre-viewer-2024"
            }
            self._save_api_keys(default_keys)
            return default_keys
    
    def _save_api_keys(self, keys: Dict[str, str]):
        """保存 API Keys"""
        import os
        os.makedirs("config", exist_ok=True)
        with open("config/api_keys.json", 'w', encoding='utf-8') as f:
            json.dump(keys, f, indent=2)
    
    def create_token(self, username: str, role: str = "admin") -> str:
        """创建 JWT Token"""
        payload = {
            "username": username,
            "role": role,
            "exp": datetime.utcnow() + timedelta(seconds=self.token_expiry),
            "iat": datetime.utcnow()
        }
        token = jwt.encode(payload, self.secret_key, algorithm="HS256")
        return token
    
    def verify_token(self, token: str) -> Dict[str, Any]:
        """验证 JWT Token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=["HS256"])
            return {"valid": True, "payload": payload}
        except jwt.ExpiredSignatureError:
            return {"valid": False, "error": "Token expired"}
        except jwt.InvalidTokenError:
            return {"valid": False, "error": "Invalid token"}
    
    def verify_api_key(self, api_key: str) -> Dict[str, Any]:
        """验证 API Key"""
        for username, key in self.api_keys.items():
            if key == api_key:
                return {
                    "valid": True,
                    "username": username,
                    "role": "admin" if username == "admin" else "viewer"
                }
        return {"valid": False, "error": "Invalid API Key"}
    
    def add_api_key(self, username: str, key: str):
        """添加新的 API Key"""
        self.api_keys[username] = key
        self._save_api_keys(self.api_keys)
        logger.info(f"Added API key for user: {username}")
