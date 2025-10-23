from pathlib import Path
import sys
import json
from typing import Optional
from sqlalchemy.engine import Engine
from sqlmodel import SQLModel, create_engine

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from config.logging_config import logger

DB_PATH = project_root / "data" / "ezppt.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)
SQLITE_URL = f"sqlite:///{DB_PATH}"


def custom_serializer(obj):
    """自定义 JSON 序列化器，确保中文不被转义"""
    return json.dumps(obj, ensure_ascii=False)


ENGINE: Engine = create_engine(
    SQLITE_URL,
    echo=False,
    connect_args={"check_same_thread": False},
    json_serializer=custom_serializer,
)


def init_db(engine: Optional[Engine] = None) -> str:
    """只在数据库文件不存在时创建文件并建表；否则什么都不做。"""
    target_engine = engine or ENGINE
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    need_init = not DB_PATH.exists()

    SQLModel.metadata.create_all(target_engine)

    if need_init:
        logger.info("数据库初始化完成")
    return str(DB_PATH)


def get_engine() -> Engine:
    """获取全局数据库引擎实例"""
    return ENGINE


if __name__ == "__main__":
    init_db()
