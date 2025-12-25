"""
TheatreOS 快速测试模式
提供可调参数、快速事件触发、数据重置等功能
"""

from .test_config import (
    TestModeConfig,
    ConfigManager,
    config_manager,
    get_config,
    get_config_value,
    set_config_value,
    reset_config,
    PRODUCTION_CONFIG,
    QUICK_TEST_CONFIG,
    DEMO_CONFIG
)

from .stages_config import (
    SHANGHAI_STAGES,
    STORY_THREADS,
    QUICK_EVENTS
)

from .test_routes import router as test_router

__all__ = [
    'TestModeConfig',
    'ConfigManager',
    'config_manager',
    'get_config',
    'get_config_value',
    'set_config_value',
    'reset_config',
    'PRODUCTION_CONFIG',
    'QUICK_TEST_CONFIG',
    'DEMO_CONFIG',
    'SHANGHAI_STAGES',
    'STORY_THREADS',
    'QUICK_EVENTS',
    'test_router'
]
