"""
TheatreOS Service Registry
全局服务注册表 - 确保服务实例的单例模式，保持数据持久性
"""
from typing import Dict, Any, Optional
import threading

_lock = threading.Lock()
_services: Dict[str, Any] = {}


def get_service(service_name: str, factory_func=None, *args, **kwargs):
    """
    获取服务实例（单例模式）
    
    Args:
        service_name: 服务名称
        factory_func: 服务工厂函数（如果服务不存在则调用）
        *args, **kwargs: 传递给工厂函数的参数
    
    Returns:
        服务实例
    """
    global _services
    
    with _lock:
        if service_name not in _services:
            if factory_func is None:
                raise ValueError(f"Service {service_name} not found and no factory provided")
            _services[service_name] = factory_func(*args, **kwargs)
        
        return _services[service_name]


def register_service(service_name: str, service_instance: Any):
    """
    注册服务实例
    
    Args:
        service_name: 服务名称
        service_instance: 服务实例
    """
    global _services
    
    with _lock:
        _services[service_name] = service_instance


def clear_services():
    """清除所有服务实例（用于测试）"""
    global _services
    
    with _lock:
        _services.clear()


# 服务名称常量
TRACE_SERVICE = "trace_service"
CREW_SERVICE = "crew_service"
EVIDENCE_SERVICE = "evidence_service"
RUMOR_SERVICE = "rumor_service"
