from pathlib import Path
import sys
from typing import List, Optional, Sequence

from sqlalchemy.engine import Engine
from sqlmodel import Session, and_, delete, select, update

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.repository.db_utils import get_engine
from src.models.project_model import Project, Status
from config.logging_config import logger


def db_add_project(project: Project, *, engine: Optional[Engine] = None) -> bool:
    engine = engine or get_engine()
    try:
        with Session(engine) as sess:
            sess.add(project)
            sess.commit()
            logger.info(f"已新增project: {project}")
            return True
    except Exception as exc:
        logger.error(f"新增project时出错: {exc}")
        return False


def db_del_project(project_id: str, *, engine: Optional[Engine] = None) -> bool:
    engine = engine or get_engine()
    try:
        with Session(engine) as sess:
            stmt = delete(Project).where(Project.project_id == project_id)
            result = sess.exec(stmt)
            sess.commit()
            if result.rowcount == 0:
                logger.warning(f"未找到id为 {project_id} 的project")
                return False
            logger.info(f"已删除id为 {project_id} 的project")
            return True
    except Exception as exc:
        logger.error(f"删除project时出错: {exc}")
        return False


def db_get_project_status(project_id: str, *, engine: Optional[Engine] = None) -> str:
    engine = engine or get_engine()
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


def db_update_project(
    project_id: str,
    new_status: str = "",
    new_pdf_status: str = "",
    new_pptx_status: str = "",
    *,
    engine: Optional[Engine] = None,
) -> bool:
    engine = engine or get_engine()
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
                    and_(
                        Project.project_id == project_id
                    )  # 使用 and_ 主要是方防止PylancereportArgumentType提示
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


def db_try_start_pdf_export(
    project_id: str,
    allowed_statuses: Sequence[str] = (Status.pending, Status.failed),
    *,
    engine: Optional[Engine] = None,
) -> bool:
    engine = engine or get_engine()
    if not allowed_statuses:
        return False
    try:
        with Session(engine) as sess:
            stmt = (
                update(Project)
                .where(
                    and_(
                        Project.project_id == project_id,
                        Project.pdf_status.in_(allowed_statuses),
                    )
                )
                .values(pdf_status=Status.generating)
            )
            result = sess.exec(stmt)
            sess.commit()
            return result.rowcount > 0
    except Exception as exc:
        logger.error(f"更新project PDF状态时出错: {exc}")
        return False


def db_try_start_pptx_export(
    project_id: str,
    allowed_statuses: Sequence[str] = (Status.pending, Status.failed),
    *,
    engine: Optional[Engine] = None,
) -> bool:
    engine = engine or get_engine()
    if not allowed_statuses:
        return False
    try:
        with Session(engine) as sess:
            stmt = (
                update(Project)
                .where(
                    and_(
                        Project.project_id == project_id,
                        Project.pptx_status.in_(allowed_statuses),
                    )
                )
                .values(pptx_status=Status.generating)
            )
            result = sess.exec(stmt)
            sess.commit()
            return result.rowcount > 0
    except Exception as exc:
        logger.error(f"更新project PPTX状态时出错: {exc}")
        return False


def db_list_projects(*, engine: Optional[Engine] = None) -> List[Project]:
    engine = engine or get_engine()
    try:
        with Session(engine) as sess:
            stmt = select(Project).order_by(Project.create_time.desc())
            results = sess.exec(stmt).all()
            return list(results)
    except Exception as exc:
        logger.error(f"查询项目列表时出错: {exc}")
        return []


def db_get_project(
    project_id: str, *, engine: Optional[Engine] = None
) -> Optional[Project]:
    engine = engine or get_engine()
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
