from copy import deepcopy
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import traceback

project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from config.base_config import (
    OUTLINE_LLM_CONFIG,
    PPT_LLM_CONFIG,
    HTML_GENERATION_MAX_WORKERS,
)
from config.logging_config import logger
from src.agents.step_01_create_outline import create_outline
from src.agents.step_02_create_html import create_html
from src.agents.get_pic import get_pic
from src.models.outline_model import Outline
from src.repository import outline_repo, project_repo
from src.models.project_model import Status

# 大纲及最终产物根目录
PPT_OUTPUT_DIR = project_root / "data" / "projects"


def _get_project_dir(outline_config: Outline):
    """获取项目保存目录"""
    project_id = outline_config.project_id
    project = project_repo.db_get_project(project_id=project_id)
    if project is None:
        logger.error(f"未找到项目 {project_id}")
        raise ValueError(f"未找到项目 {project_id}")
    run_tag = project.project_name
    run_dir = PPT_OUTPUT_DIR / run_tag
    run_dir.mkdir(parents=True, exist_ok=True)
    html_save_dir = run_dir / "html_files"
    img_save_dir = run_dir / "images"
    outline_file = run_dir / "outline.json"
    return run_dir, html_save_dir, img_save_dir, outline_file


def _update_outline_config_html_content(
    outline_config: Outline, slide_id, html_content
) -> Outline:
    updated = False
    for chapter in outline_config.outline_json["chapters"]:
        for slide in chapter.get("slides", []):
            if str(slide["slide_id"]) == str(slide_id):
                slide["html_content"] = html_content
                updated = True
                break
        if updated:
            break
    return outline_config


def _create_html_with_image(
    outline_config: Outline, visual_suggestions: dict, target_id: str
) -> str:
    # if visual_suggestions[target_id] != {}:
    #     q = visual_suggestions[target_id]["search_keywords"]
    #     d = visual_suggestions[target_id]["image_description"]
    #     img_result = get_pic(query=q, description=d)
    #     images_temp = {
    #         Path("..", *(Path(k).parts[-2:])).as_posix(): v for k, v in img_result.items()
    #     }
    #     outline_config.images[target_id] = images_temp
    #     # print(outline_config.images)
    # else:
    #     pass
    html_content = create_html(
        outline_config=outline_config, target_id=target_id, llm_config=PPT_LLM_CONFIG
    )
    return html_content


def _generate_chapter_slide_html(outline_config: Outline, slide_id: str) -> str:
    """
    生成单个幻灯片的 HTML 内容。outline_config需要自行添加参考html的内容
    """
    # 从 outline_config 中查找该 slide 的信息
    visual_suggestions = {}
    for chapter in outline_config.outline_json["chapters"]:
        for slide in chapter.get("slides", []):
            if str(slide["slide_id"]) == str(slide_id):
                visual_suggestions = slide.get("visual_suggestions", {})
                break

    html_content = _create_html_with_image(
        outline_config=outline_config,
        visual_suggestions=visual_suggestions,
        target_id=slide_id,
    )

    return html_content


def _generate_chapter_slides_html(
    outline_config: Outline,
    chapter_order: int,
    html_save_dir: Path,
) -> Outline:
    """
    在一个独立的任务中，顺序生成一个完整章节的所有幻灯片。
    """
    logger.info(f"开始顺序生成章节 {chapter_order} 的所有幻灯片html内容...")
    slide_ids_for_chapter = outline_config.outline_json["chapters"][chapter_order - 1][
        "slides"
    ]
    for slide in slide_ids_for_chapter:
        slide_id = slide["slide_id"]
        try:
            html_content = _generate_chapter_slide_html(outline_config, slide_id)

            (html_save_dir / f"{slide_id}.html").write_text(
                html_content, encoding="utf-8"
            )
            logger.info(f"章节 {chapter_order} 内的幻灯片 {slide_id}.html 已生成")
            outline_repo.db_update_outline_slide(
                project_id=outline_config.project_id,
                slide_id=slide_id,
                html_content=html_content,
                new_status=Status.completed,
            )
            # 更新本线程内的上下文，为生成本章的下一页做准备
            outline_config = _update_outline_config_html_content(
                outline_config, slide_id, html_content
            )
        except Exception as e:
            logger.error(traceback.format_exc())
            logger.error(f"在生成章节 {chapter_order} 的幻灯片 {slide_id} 时失败: {e}")
            # 即使单页失败，也继续尝试生成本章的下一页
            continue
    return outline_config


def create_project_execute(outline_config: Outline):
    # 环境准备
    _, html_save_dir, img_save_dir, outline_file = _get_project_dir(outline_config)
    html_save_dir.mkdir(parents=True, exist_ok=True)
    img_save_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"HTML 文件保存位置：{html_save_dir}")
    logger.info(f"大纲保存位置：{outline_file}")

    # 提前提取后续需要的数据
    project_id = outline_config.project_id
    global_visual_suggestion = outline_config.outline_json.get(
        "global_visual_suggestion", {}
    )
    outline_config.global_visual_suggestion = global_visual_suggestion

    # 生成并保存大纲到数据库
    outline_config = create_outline(
        outline_config=outline_config, llm_config=OUTLINE_LLM_CONFIG
    )

    ok = outline_repo.db_add_outline(outline_config=outline_config)
    if not ok:
        logger.error(f"无法将项目{project_id}大纲保存到数据库! 建议重建项目")
        raise Exception(f"无法将项目{project_id}大纲保存到数据库! 建议重建项目")
    ok = outline_repo.db_add_outline_slides(project_id=project_id)
    if not ok:
        logger.error(f"无法将项目{project_id}幻灯片保存到数据库! 建议重建项目")
        raise Exception(f"无法将项目{project_id}幻灯片保存到数据库! 建议重建项目")
    project_repo.db_update_project(project_id=project_id, new_status=Status.generating)
    logger.info(f"项目 {project_id} 的状态已更新为 '{Status.generating}'")
    outline_config_tmp = outline_repo.db_get_outline(project_id=project_id)
    if not outline_config_tmp:
        logger.error(f"无法从数据库中获取项目 {project_id} 的大纲")
        raise Exception(f"无法从数据库中获取项目 {project_id} 的大纲")
    outline_config_tmp = _generate_chapter_slides_html(
        outline_config=outline_config_tmp,
        chapter_order=1,
        html_save_dir=html_save_dir,
    )
    chapters_map = outline_config_tmp.outline_json["chapters"]
    with ThreadPoolExecutor(max_workers=HTML_GENERATION_MAX_WORKERS) as pool:
        # 每个 Future 对应一个章节的生成任务
        futures = {
            pool.submit(
                _generate_chapter_slides_html,
                outline_config=deepcopy(outline_config_tmp),  # 传入包含第一章上下文的副本
                chapter_order=int(chapter["chapter_id"]),
                html_save_dir=html_save_dir,
            ): chapter["chapter_id"]
            for chapter in chapters_map
            if int(chapter["chapter_id"]) > 1
        }
        for fut in futures:
            chapter_id = futures[fut]
            try:
                fut.result()  # 等待该章节全部生成完毕
                logger.info(f"章节 {chapter_id} 已全部生成完毕。")
            except Exception as e:
                logger.error(f"生成章节 {chapter_id} 时发生严重错误: {e}")
    logger.info("所有幻灯片内容均已生成完毕。")
    project_repo.db_update_project(project_id=project_id, new_status=Status.completed)
    logger.info(f"项目 {project_id} 的状态已更新为 '{Status.completed}'")


def restart_project_execute(project_id):
    outline_config = outline_repo.db_get_outline(project_id)
    if outline_config is None:
        logger.error(f"未找到项目 {project_id} 的大纲")
        return
    clean_outline_config = Outline(
        project_id=project_id,
        topic=outline_config.topic,
        audience=outline_config.audience,
        style=outline_config.style,
        page_num=outline_config.page_num,
        reference_content=outline_config.reference_content,
    )
    _, html_save_dir, _, _ = _get_project_dir(outline_config)
    # 删除html_save_dir中的所有html文件
    for file in html_save_dir.iterdir():
        if file.is_file() and file.suffix == ".html":
            file.unlink()
    project_repo.db_update_project(
        project_id=project_id,
        new_status=Status.generating,
        new_pdf_status=Status.pending,
        new_pptx_status=Status.pending,
    )
    outline_repo.db_del_outline(project_id)
    outline_repo.db_del_outline_slides(project_id)
    create_project_execute(clean_outline_config)


def restart_slide_execute(project_id, slide_id):
    try:
        outline_config = outline_repo.db_get_outline(project_id)
        if outline_config is None:
            logger.error(f"未找到项目 {project_id} 的大纲")
            return
        _, html_save_dir, _, _ = _get_project_dir(outline_config)
        chapter_id = str(slide_id.split(".")[0])
        slide_order = int(slide_id.split(".")[1])
        reference_slides_list = [f"{chapter_id}.{i}" for i in range(1, slide_order)]
        logger.info(f"重新生成幻灯片 {slide_id}，参考幻灯片id列表: {reference_slides_list}")
        for reference_slide_id in reference_slides_list:
            reference_slide = outline_repo.db_get_outline_slide(
                project_id, reference_slide_id
            )
            if reference_slide is None:
                continue
            reference_slide_html_content = reference_slide.html_content
            outline_config = _update_outline_config_html_content(
                outline_config, reference_slide_id, reference_slide_html_content
            )

        slide_html_content = _generate_chapter_slide_html(outline_config, slide_id)
        if slide_html_content is None:
            logger.error(f"重新生成生成项目 {project_id} 的幻灯片 {slide_id} 的 HTML 内容失败")
            return
        (html_save_dir / f"{slide_id}.html").write_text(
            slide_html_content, encoding="utf-8"
        )
        outline_repo.db_update_outline_slide(
            project_id=project_id,
            slide_id=slide_id,
            html_content=slide_html_content,
            new_status=Status.completed,
        )
        logger.info(f"重新生成生成项目 {project_id} 的幻灯片 {slide_id} 的 HTML 内容成功")
    except Exception as e:
        logger.error(f"重新生成生成项目 {project_id} 的幻灯片 {slide_id} 的 HTML 内容失败: {e}")
        outline_repo.db_update_outline_slide(project_id=project_id, slide_id=slide_id, new_status=Status.failed)
        logger.error(traceback.format_exc())


# if __name__ == "__main__":
#     topic = "tpu的发展历史"
#     audience = "大众"
#     style = "简洁明了"
#     page_num = 20

#     outline_config = Outline(
#         topic=topic, audience=audience, style=style, page_num=page_num
#     )

#     outline_json = create_project_execute(outline_config)

#     # 打印调试
#     # print(json.dumps(outline_json, ensure_ascii=False, indent=4))
