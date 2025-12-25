"""
TheatreOS Configuration Settings
M1: "心跳" - Core Engine Configuration
"""
import os
from datetime import timezone

# =============================================================================
# Database Configuration
# =============================================================================
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://theatreos:theatreos@localhost:5432/theatreos"
)

# =============================================================================
# Server Configuration
# =============================================================================
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))
DEBUG = os.getenv("DEBUG", "true").lower() == "true"

# =============================================================================
# Theatre Kernel Configuration
# =============================================================================
# Tick interval in seconds (default: 1 hour = 3600 seconds)
TICK_INTERVAL_SECONDS = int(os.getenv("TICK_INTERVAL_SECONDS", "3600"))

# For demo/testing: use shorter tick interval (e.g., 60 seconds = 1 minute)
DEMO_TICK_INTERVAL_SECONDS = int(os.getenv("DEMO_TICK_INTERVAL_SECONDS", "60"))

# World state version conflict retry settings
APPLY_DELTA_MAX_RETRIES = 3
APPLY_DELTA_RETRY_DELAY_MS = 100

# Snapshot retention (days)
SNAPSHOT_RETENTION_DAYS = 7

# =============================================================================
# Scheduler Configuration
# =============================================================================
# How far ahead to generate HourPlans (in hours)
SCHEDULE_LOOKAHEAD_HOURS = 2

# Default parallel scenes per slot
DEFAULT_PARALLEL_SCENES = 8

# Golden hours (local time) - higher activity expected
GOLDEN_HOURS = [12, 13, 19, 20, 21, 22, 23, 0]

# Gate resolve minute within each slot (e.g., T+12)
GATE_RESOLVE_MINUTE = 12

# Slot duration in minutes
SLOT_DURATION_MINUTES = 15

# =============================================================================
# Content Factory Configuration (M2 Preview)
# =============================================================================
# Generation deadline before slot start (minutes)
GENERATION_DEADLINE_MINUTES = 5

# Media levels for degradation
MEDIA_LEVELS = ["L0", "L1", "L2", "L3", "L4"]

# =============================================================================
# Event Bus Configuration (Kafka - for future use)
# =============================================================================
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
KAFKA_ENABLED = os.getenv("KAFKA_ENABLED", "false").lower() == "true"

# =============================================================================
# Default Theme Pack (M1: Static Theme)
# =============================================================================
DEFAULT_THEME_ID = "hp_shanghai_s1"
DEFAULT_THEME_VERSION = "1.0.0"
DEFAULT_CITY = "shanghai"
DEFAULT_TIMEZONE = "Asia/Shanghai"

# =============================================================================
# API Rate Limiting
# =============================================================================
RATE_LIMIT_REQUESTS_PER_MINUTE = 60

# =============================================================================
# Logging Configuration
# =============================================================================
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


# =============================================================================
# AI Service Configuration (通义千问 / DashScope)
# =============================================================================
AI_PROVIDER = os.getenv("AI_PROVIDER", "dashscope")  # openai or dashscope

# DashScope (通义千问) Configuration
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY", "")
DASHSCOPE_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
DASHSCOPE_MODEL = os.getenv("DASHSCOPE_MODEL", "qwen-plus")  # qwen-turbo, qwen-plus, qwen-max

# OpenAI Configuration (fallback)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")

# AI Generation Settings
AI_MAX_TOKENS = int(os.getenv("AI_MAX_TOKENS", "2000"))
AI_TEMPERATURE = float(os.getenv("AI_TEMPERATURE", "0.8"))
AI_TIMEOUT_SECONDS = int(os.getenv("AI_TIMEOUT_SECONDS", "60"))
AI_RETRY_COUNT = int(os.getenv("AI_RETRY_COUNT", "3"))
