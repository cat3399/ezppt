from pathlib import Path
import sys
from typing import List, Optional
from sqlmodel import Session, and_, select, update

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.repository.db_utils import get_engine
from src.models.project_model import Project
from config.logging_config import logger


def db_add_project(project: Project) -> bool:
    engine = get_engine()
    try:
        with Session(engine) as sess:
            sess.add(project)
            sess.commit()
            return True
    except Exception as exc:
        logger.error(f"新增project时出错: {exc}")
        return False


def db_get_project_status(project_id: str) -> str:
    engine = get_engine()
    try:
        with Session(engine) as sess:
            stmt = select(Project).where(Project.project_id == project_id)
            result = sess.exec(stmt).first()
            if result:
                return result.status
            else:
                logger.warning(f"未找到id为 {project_id} 的project")
                return ""
    except Exception as exc:
        logger.error(f"查询project状态时出错: {exc}")
        return ""


def db_update_project(project_id: str, new_status: str = "", new_pdf_status: str = "", new_pptx_status: str = "") -> bool:
    engine = get_engine()
    try:
        with Session(engine) as sess:
            update_values = {}
            if new_status:
                update_values["status"] = new_status
            if new_pdf_status:
                update_values["pdf_status"] = new_pdf_status
            if new_pptx_status:
                update_values["pptx_status"] = new_pptx_status
            # 查询要修改的项目
            stmt = (
                update(Project)
                .where(
                    and_(Project.project_id == project_id) # 使用 and_ 主要是方防止PylancereportArgumentType提示
                )
                .values(**update_values)
            )
            result = sess.exec(stmt)
            sess.commit()
            if result.rowcount == 0:
                logger.warning(f"未找到id为 {project_id} 的project")
                return False
            return True
    except Exception as exc:
        logger.error(f"更新project状态时出错: {exc}")
        return False


def db_list_projects() -> List[Project]:
    engine = get_engine()
    try:
        with Session(engine) as sess:
            stmt = select(Project).order_by(Project.create_time.desc())
            results = sess.exec(stmt).all()
            return list(results)
    except Exception as exc:
        logger.error(f"查询项目列表时出错: {exc}")
        return []


def db_get_project(project_id: str) -> Optional[Project]:
    engine = get_engine()
    try:
        with Session(engine) as sess:
            stmt = select(Project).where(Project.project_id == project_id)
            result = sess.exec(stmt).first()
            if not result:
                logger.warning(f"未找到id为 {project_id} 的project")
            return result
    except Exception as exc:
        logger.error(f"查询project详情时出错: {exc}")
        return None
