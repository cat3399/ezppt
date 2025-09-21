import sys
from pathlib import Path
from collections import Counter
from typing import Dict, List, Optional
from sqlmodel import Session, and_, delete, select, update

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.repository.db_utils import get_engine
from src.models.outline_model import Outline
from src.models.outline_slide_model import OutlineSlide
from config.logging_config import logger


def db_add_outline(outline_config: Outline) -> bool:
    """
    根据 create_outline 生成的 JSON，一次性创建 Outline 和所有的 OutlineSlide 记录
    """
    engine = get_engine()
    try:
        with Session(engine) as sess:
            sess.add(outline_config)
            sess.commit()
            logger.info(f"项目id: {outline_config.project_id}  的大纲已成功存入数据库")
            return True
    except Exception as exc:
        logger.error(
            f"为项目 {outline_config.project_id} 存入大纲和幻灯片时出错: {exc}"
        )
        return False


def db_del_outline(project_id: str) -> bool:
    engine = get_engine()
    try:
        with Session(engine) as sess:
            stmt = select(Outline).where(Outline.project_id == project_id)
            r = sess.exec(stmt).first()
            if r:
                sess.delete(r)
                sess.commit()
                logger.info(f"项目 {project_id} 的大纲已成功删除")
                return True
            else:
                logger.error(f"未找到项目 {project_id} 的大纲")
                return False
    except Exception as exc:
        logger.error(f"删除项目 {project_id} 的大纲时出错: {exc}")
        return False


def db_get_outline(project_id: str) -> Optional[Outline]:
    """获取一个项目的大纲"""
    engine = get_engine()
    try:
        with Session(engine) as sess:
            stmt = select(Outline).where(Outline.project_id == project_id)
            r = sess.exec(stmt).first()
            return r
    except Exception as exc:
        logger.error(f"获取项目 {project_id} 的大纲时出错: {exc}")
        return None


def db_add_outline_slides(project_id: str) -> bool:
    engine = get_engine()
    success_count = 0
    fail_count = 0

    try:
        with Session(engine) as sess:
            outline_config = db_get_outline(project_id=project_id)
            if not outline_config:
                return False
            outline_json = outline_config.outline_json
            chapters = outline_json.get("chapters", [])

            if chapters:
                for chapter in chapters:
                    chapter_id = int(chapter.get("chapter_id", ""))
                    chapter_title = chapter.get("chapter_title") or chapter.get("chapter_topic", "")
                    slides = chapter.get("slides", [])

                    if chapter_id and slides:
                        for slide in slides:
                            slide_id = slide.get("slide_id", "")
                            slide_content = str(slide.get("slide_content", []))
                            slide_order = int(
                                slide_id.split(".")[-1] if slide_id else ""
                            )
                            slide_topic = slide.get("slide_topic", "")
                            visual_suggestion = slide.get("visual_suggestion", {})

                            # logger.info(
                            #     f"project_id: {project_id}, slide_id: {slide_id}, "
                            #     f"chapter_id: {chapter_id}, slide_content: {slide_content}, "
                            #     f"chapter_title: {chapter_title}, slide_order: {slide_order}, "
                            #     f"slide_topic: {slide_topic}, visual_suggestion: {visual_suggestion}"
                            # )

                            if slide_id and slide_content and slide_order:
                                try:
                                    outline_slide = OutlineSlide(
                                        project_id=project_id,
                                        slide_id=slide_id,
                                        chapter_id=chapter_id,
                                        slide_content=slide_content,
                                        chapter_title=chapter_title,
                                        slide_order=slide_order,
                                        slide_topic=slide_topic,
                                        visual_suggestion=visual_suggestion,
                                        status="pending",
                                    )

                                    sess.add(outline_slide)
                                    sess.commit()
                                    success_count += 1

                                except Exception as e:
                                    sess.rollback()
                                    fail_count += 1
                                    logger.warning(
                                        f"插入幻灯片 {slide_id} 失败: {e}，继续处理下一张"
                                    )
                                    continue

            logger.info(
                f"项目 {project_id} 幻灯片处理完成：成功 {success_count} 张，失败 {fail_count} 张"
            )
            return success_count > 0

    except Exception as exc:
        logger.error(f"为项目 {project_id} 存入幻灯片时出错: {exc}")
        return False


def db_del_outline_slide(project_id: str, slide_id: str) -> bool:
    engine = get_engine()
    try:
        with Session(engine) as sess:
            stmt = select(OutlineSlide).where(
                OutlineSlide.project_id == project_id, OutlineSlide.slide_id == slide_id
            )
            r = sess.exec(stmt).first()
            if r:
                sess.delete(r)
                sess.commit()
                logger.info(f"项目 {project_id} 的幻灯片 {slide_id} 已成功删除")
                return True
            else:
                logger.error(f"未找到项目 {project_id} 的幻灯片 {slide_id}")
                return False
    except Exception as exc:
        logger.error(f"删除项目 {project_id} 的幻灯片 {slide_id} 时出错: {exc}")
        return False

def db_del_outline_slides(project_id: str) -> bool:
    """删除项目的所有幻灯片"""
    engine = get_engine()
    try:
        with Session(engine) as sess:
            stmt = delete(OutlineSlide).where(OutlineSlide.project_id == project_id)
            sess.exec(stmt)
            sess.commit()
            logger.info(f"项目 {project_id} 的所有幻灯片已成功删除")
            return True
    except Exception as exc:
        logger.error(f"删除项目 {project_id} 的所有幻灯片时出错: {exc}")
        return False

def db_list_outline_slides(project_id: str) -> List[OutlineSlide]:
    engine = get_engine()
    try:
        with Session(engine) as sess:
            stmt = (
                select(OutlineSlide)
                .where(OutlineSlide.project_id == project_id)
                .order_by(OutlineSlide.chapter_id, OutlineSlide.slide_order, OutlineSlide.slide_id)
            )
            results = sess.exec(stmt).all()
            return list(results)
    except Exception as exc:
        logger.error(f"获取项目 {project_id} 的幻灯片列表时出错: {exc}")
        return []


def db_get_outline_slide(project_id: str, slide_id: str) -> Optional[OutlineSlide]:
    engine = get_engine()
    try:
        with Session(engine) as sess:
            stmt = select(OutlineSlide).where(
                and_(
                    OutlineSlide.project_id == project_id,
                    OutlineSlide.slide_id == slide_id,
                )
            )
            result = sess.exec(stmt).first()
            if not result:
                logger.warning(f"未找到项目 {project_id} 的幻灯片 {slide_id}")
            return result
    except Exception as exc:
        logger.error(f"查询项目 {project_id} 的幻灯片 {slide_id} 时出错: {exc}")
        return None


def db_get_slide_status(project_id: str) -> Dict[str, int]:
    slides = db_list_outline_slides(project_id=project_id)
    counter = Counter(slide.status for slide in slides)
    total = len(slides)
    return {
        "total": total,
        "pending": counter.get("pending", 0),
        "generating": counter.get("generating", 0),
        "completed": counter.get("completed", 0),
        "failed": counter.get("failed", 0),
    }


def db_update_outline_slide(
    project_id: str,
    slide_id: str,
    *,
    new_status: str = "",
    html_content: str = "",
) -> bool:
    """更新某个幻灯片的字段"""
    engine = get_engine()
    try:
        with Session(engine) as sess:
            # 构建更新字典
            update_values = {}
            if new_status:
                update_values["status"] = new_status
            if html_content:
                update_values["html_content"] = html_content

            # 如果没有要更新的内容，直接返回
            if not update_values:
                return True

            # 使用 update 语句
            stmt = (
                update(OutlineSlide)
                .where(
                    and_(
                        OutlineSlide.project_id == project_id,
                        OutlineSlide.slide_id == slide_id,
                    )
                )
                .values(**update_values)
            )
            result = sess.exec(stmt)
            sess.commit()

            # 通过 rowcount 检查是否有记录被更新
            if result.rowcount == 0:
                logger.error(f"未找到项目 {project_id} 的幻灯片 {slide_id}")
                return False

            return True
    except Exception as exc:
        logger.error(f"更新项目 {project_id} 的幻灯片 {slide_id} 状态时出错: {exc}")
        return False
