from pathlib import Path
import sys
from sqlmodel import SQLModel, create_engine
import json

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from config.logging_config import logger
from src.models.project_model import Project
from src.models.outline_model import Outline
from src.models.outline_slide_model import OutlineSlide

DB_PATH    = project_root / "data" / "ezppt.db"
SQLITE_URL = f"sqlite:///{DB_PATH}"

# 2. 定义一个我们自己的序列化函数
def custom_serializer(obj):
    """自定义 JSON 序列化器，确保中文不被转义"""
    return json.dumps(obj, ensure_ascii=False)

def init_db():
    """只在数据库文件不存在时创建文件并建表；否则什么都不做。"""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    need_init = not DB_PATH.exists()

    # 3. 在创建引擎时，传入自定义的序列化器
    engine = create_engine(
        SQLITE_URL,
        echo=False,
        connect_args={"check_same_thread": False},
        json_serializer=custom_serializer
    )
    SQLModel.metadata.create_all(engine)

    if need_init:
        logger.info("数据库初始化完成")
        print("数据库初始化成功")
    return str(DB_PATH)

def get_engine():
    """无副作用，单纯给调用方一个引擎实例。"""
    # 4. 同样，在获取引擎的函数中也要传入
    return create_engine(
        SQLITE_URL,
        echo=False,
        connect_args={"check_same_thread": False},
        json_serializer=custom_serializer
    )

if __name__ == "__main__":
    init_db()
