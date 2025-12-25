"""
TheatreOS DashScope (通义千问) AI Adapter
通义千问AI服务适配器 - 兼容OpenAI接口
"""

import os
import json
from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

# 通义千问使用OpenAI兼容接口
try:
    from openai import OpenAI
    DASHSCOPE_AVAILABLE = True
except ImportError:
    DASHSCOPE_AVAILABLE = False
    OpenAI = None


# DashScope配置
DASHSCOPE_CONFIG = {
    "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "model": os.environ.get("DASHSCOPE_MODEL", "qwen-plus"),  # qwen-turbo, qwen-plus, qwen-max
    "max_tokens": 2000,
    "temperature": 0.8,
    "timeout": 60,
    "retry_count": 3,
}

# 可用模型
AVAILABLE_MODELS = {
    "qwen-turbo": "通义千问-Turbo（快速响应）",
    "qwen-plus": "通义千问-Plus（均衡性能）",
    "qwen-max": "通义千问-Max（最强能力）",
    "qwen-max-longcontext": "通义千问-Max长文本版",
}


class DashScopeClient:
    """通义千问客户端"""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.environ.get("DASHSCOPE_API_KEY")
        self.client = None
        self.available = False
        
        if DASHSCOPE_AVAILABLE and self.api_key:
            try:
                self.client = OpenAI(
                    api_key=self.api_key,
                    base_url=DASHSCOPE_CONFIG["base_url"]
                )
                self.available = True
                print(f"DashScope client initialized with model: {DASHSCOPE_CONFIG['model']}")
            except Exception as e:
                print(f"Failed to initialize DashScope client: {e}")
                self.available = False
        else:
            if not DASHSCOPE_AVAILABLE:
                print("OpenAI package not available for DashScope")
            if not self.api_key:
                print("DASHSCOPE_API_KEY not set")
    
    def chat(
        self,
        messages: List[Dict[str, str]],
        model: str = None,
        max_tokens: int = None,
        temperature: float = None,
        **kwargs
    ) -> Dict[str, Any]:
        """发送聊天请求"""
        if not self.client:
            raise RuntimeError("DashScope client not initialized")
        
        model = model or DASHSCOPE_CONFIG["model"]
        max_tokens = max_tokens or DASHSCOPE_CONFIG["max_tokens"]
        temperature = temperature or DASHSCOPE_CONFIG["temperature"]
        
        start_time = datetime.utcnow()
        
        response = self.client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            timeout=DASHSCOPE_CONFIG["timeout"]
        )
        
        latency_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        
        return {
            "content": response.choices[0].message.content,
            "tokens_used": response.usage.total_tokens if response.usage else 0,
            "latency_ms": latency_ms,
            "model": model,
            "finish_reason": response.choices[0].finish_reason
        }
    
    def generate_text(
        self,
        prompt: str,
        system_prompt: str = None,
        **kwargs
    ) -> Dict[str, Any]:
        """生成文本（简化接口）"""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        return self.chat(messages, **kwargs)
    
    def test_connection(self) -> Dict[str, Any]:
        """测试连接"""
        try:
            result = self.generate_text(
                prompt="请用一句话介绍你自己。",
                max_tokens=100
            )
            return {
                "success": True,
                "model": result.get("model"),
                "response": result.get("content", "")[:100],
                "latency_ms": result.get("latency_ms")
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }


# 全局客户端实例
_dashscope_client: Optional[DashScopeClient] = None


def get_dashscope_client() -> DashScopeClient:
    """获取DashScope客户端单例"""
    global _dashscope_client
    if _dashscope_client is None:
        _dashscope_client = DashScopeClient()
    return _dashscope_client


def init_dashscope(api_key: str = None) -> DashScopeClient:
    """初始化DashScope客户端"""
    global _dashscope_client
    _dashscope_client = DashScopeClient(api_key)
    return _dashscope_client
