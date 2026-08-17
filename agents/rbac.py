"""
RBAC 权限控制模块
"""
from typing import Dict, Any, List
from enum import Enum
from loguru import logger


class Role(Enum):
    """角色枚举"""
    ADMIN = "admin"
    OPERATOR = "operator"
    VIEWER = "viewer"


class Permission(Enum):
    """权限枚举"""
    VIEW = "view"
    CREATE = "create"
    EXECUTE = "execute"
    DELETE = "delete"
    MANAGE = "manage"


class RBAC:
    """RBAC 权限管理器"""
    
    # 角色权限映射
    role_permissions = {
        Role.ADMIN: {
            Permission.VIEW,
            Permission.CREATE,
            Permission.EXECUTE,
            Permission.DELETE,
            Permission.MANAGE
        },
        Role.OPERATOR: {
            Permission.VIEW,
            Permission.CREATE,
            Permission.EXECUTE
        },
        Role.VIEWER: {
            Permission.VIEW
        }
    }
    
    def __init__(self):
        self.users: Dict[str, Dict[str, Any]] = {}
        self._load_default_users()
    
    def _load_default_users(self):
        """加载默认用户"""
        self.users = {
            "admin": {
                "role": Role.ADMIN,
                "api_key": "autosre-admin-2024"
            },
            "operator": {
                "role": Role.OPERATOR,
                "api_key": "autosre-operator-2024"
            },
            "viewer": {
                "role": Role.VIEWER,
                "api_key": "autosre-viewer-2024"
            }
        }
    
    def check_permission(self, api_key: str, permission: Permission) -> bool:
        """检查权限"""
        user = self.get_user_by_api_key(api_key)
        if not user:
            return False
        
        role = user.get('role')
        allowed = self.role_permissions.get(role, set())
        return permission in allowed
    
    def get_user_by_api_key(self, api_key: str) -> Dict[str, Any]:
        """通过 API key 获取用户"""
        for username, info in self.users.items():
            if info.get('api_key') == api_key:
                return {
                    "username": username,
                    "role": info.get('role')
                }
        return None
    
    def add_user(self, username: str, role: Role, api_key: str):
        """添加用户"""
        self.users[username] = {
            "role": role,
            "api_key": api_key
        }
        logger.info(f"添加用户: {username} ({role.value})")
    
    def remove_user(self, username: str):
        """删除用户"""
        if username in self.users:
            del self.users[username]
            logger.info(f"删除用户: {username}")
    
    def list_users(self) -> List[Dict[str, Any]]:
        """列出所有用户"""
        return [
            {"username": u, "role": i['role'].value}
            for u, i in self.users.items()
        ]