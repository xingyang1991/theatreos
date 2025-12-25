"""
TheatreOS Database Session Manager
数据库会话管理器 - 统一管理数据库连接和会话
"""

import os
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool

from kernel.src.models import Base


# 数据库配置
DATABASE_CONFIG = {
    "sqlite": {
        "url": "sqlite:///./theatreos.db",
        "connect_args": {"check_same_thread": False}
    },
    "mysql": {
        "url": os.environ.get(
            "DATABASE_URL",
            "mysql+pymysql://root:password@localhost:3306/theatreos"
        ),
        "pool_size": 10,
        "max_overflow": 20,
        "pool_pre_ping": True
    },
    "postgresql": {
        "url": os.environ.get(
            "DATABASE_URL",
            "postgresql://postgres:password@localhost:5432/theatreos"
        ),
        "pool_size": 10,
        "max_overflow": 20,
        "pool_pre_ping": True
    }
}

# 当前使用的数据库类型
DB_TYPE = os.environ.get("DB_TYPE", "sqlite")


class DatabaseManager:
    """数据库管理器"""
    
    _instance = None
    _engine = None
    _session_factory = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._engine is None:
            self._initialize()
    
    def _initialize(self):
        """初始化数据库连接"""
        config = DATABASE_CONFIG.get(DB_TYPE, DATABASE_CONFIG["sqlite"])
        
        if DB_TYPE == "sqlite":
            self._engine = create_engine(
                config["url"],
                connect_args=config.get("connect_args", {}),
                echo=os.environ.get("SQL_ECHO", "false").lower() == "true"
            )
        else:
            self._engine = create_engine(
                config["url"],
                poolclass=QueuePool,
                pool_size=config.get("pool_size", 5),
                max_overflow=config.get("max_overflow", 10),
                pool_pre_ping=config.get("pool_pre_ping", True),
                echo=os.environ.get("SQL_ECHO", "false").lower() == "true"
            )
        
        self._session_factory = sessionmaker(
            bind=self._engine,
            autocommit=False,
            autoflush=False
        )
        
        # 创建所有表
        Base.metadata.create_all(bind=self._engine)
    
    @property
    def engine(self):
        return self._engine
    
    def get_session(self) -> Session:
        """获取数据库会话"""
        return self._session_factory()
    
    @contextmanager
    def session_scope(self):
        """提供事务性会话上下文管理器"""
        session = self.get_session()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    def close(self):
        """关闭数据库连接"""
        if self._engine:
            self._engine.dispose()


# 全局数据库管理器实例
db_manager = DatabaseManager()


def get_db() -> Session:
    """FastAPI依赖注入：获取数据库会话"""
    db = db_manager.get_session()
    try:
        yield db
    finally:
        db.close()


def get_db_session() -> Session:
    """直接获取数据库会话（非依赖注入场景）"""
    return db_manager.get_session()
