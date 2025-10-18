from contextlib import contextmanager
from typing import Generator, Optional

from sqlalchemy.engine import Engine
from sqlmodel import Session, delete, select

from config.logging_config import logger
from src.models.project_model import Project
from src.models.outline_model import Outline
from src.models.outline_slide_model import OutlineSlide
from src.repository.db_utils import get_engine


@contextmanager
def transaction_scope(engine: Optional[Engine] = None) -> Generator[Session, None, None]:
    """Provide a transactional scope around a series of operations."""
    target_engine = engine or get_engine()
    session = Session(target_engine)
    try:
        with session.begin():
            yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def delete_project_with_related(project_id: str, *, engine: Optional[Engine] = None) -> bool:
    target_engine = engine or get_engine()
    try:
        with transaction_scope(target_engine) as session:
            project = session.exec(
                select(Project).where(Project.project_id == project_id)
            ).first()
            if project is None:
                logger.warning("未找到项目 %s", project_id)
                return False

            session.exec(
                delete(OutlineSlide).where(OutlineSlide.project_id == project_id)
            )
            session.exec(
                delete(Outline).where(Outline.project_id == project_id)
            )
            session.delete(project)

        logger.info("项目 %s 及关联数据已删除", project_id)
        return True
    except Exception as exc:
        logger.error("删除项目 %s 时出错: %s", project_id, exc)
        return False
