"""
TheatreOS Database Initialization
数据库初始化和表创建
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from kernel.src.models import Base
from kernel.src.database_sqlite import DATABASE_URL


def init_all_tables():
    """初始化所有数据库表"""
    engine = create_engine(DATABASE_URL, echo=False)
    
    # 创建所有表
    Base.metadata.create_all(engine)
    
    print("✅ All database tables created successfully!")
    return engine


def get_session_factory():
    """获取Session工厂"""
    engine = create_engine(DATABASE_URL, echo=False)
    return sessionmaker(bind=engine)


if __name__ == "__main__":
    init_all_tables()
