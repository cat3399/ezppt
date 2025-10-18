from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from typing import Any
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
from datetime import datetime
import sys
from pathlib import Path
import uuid

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from config.logging_config import logger
from config.base_config import (
    CONFIG_ITEMS,
    CONFIG_ITEM_MAP,
    get_effective_config,
    get_runtime_overrides,
    update_runtime_overrides,
)
from src.utils.help_utils import time_name
from src.models.project_model import Project, ProjectIn
from src.models.outline_model import Outline
from src.repository import project_repo, outline_repo
from src.repository.transaction_manager import delete_project_with_related
from src.agents.create_project import (
    create_project_execute,
    restart_project_execute,
    restart_slide_execute,
)
from src.models.project_model import Status
from src.html_convert_office.html2office import html2office

router = APIRouter()


class SaveFileRequest(BaseModel):
    project: str
    file: str
    content: str


class ConfigUpdateRequest(BaseModel):
    updates: dict[str, Any]


PROJECTS_ROOT = Path(__file__).resolve().parent.parent.parent / "data" / "projects"


def _is_safe_name(name: str) -> bool:
    if not name:
        return False
    if ".." in name:
        return False
    path = Path(name)
    return not path.is_absolute()


def _html_sort_key(filename: str):
    stem = filename[:-5] if filename.lower().endswith(".html") else filename
    parts = stem.split(".")
    max_order = 10 ** 9
    try:
        major = int(parts[0])
    except (ValueError, IndexError):
        major = max_order

    try:
        minor = int(parts[1]) if len(parts) > 1 else 0
    except ValueError:
        minor = max_order

    return (major, minor, filename)


def model_to_dict(instance):
    if instance is None:
        return {}
    if hasattr(instance, "model_dump"):
        return instance.model_dump()
    return instance.dict()


# 获取项目列表（包含进度信息）
@router.get("/api/projects")
def list_projects():
    project_items = project_repo.db_list_projects()
    summaries = []
    for project in project_items:
        slide_stats = outline_repo.db_get_slide_status(project.project_id)
        total = slide_stats.get("total", 0)
        completed = slide_stats.get("completed", 0)
        percentage = round(completed / total * 100, 2) if total else 0.0

        summaries.append(
            {
                "project_id": project.project_id,
                "project_name": project.project_name,
                "topic": project.topic,
                "audience": project.audience,
                "style": project.style,
                "page_num": project.page_num,
                "status": project.status,
                "enable_img_search": project.enable_img_search,
                "pdf_status": project.pdf_status,
                "pptx_status": project.pptx_status,
                "created_at": project.create_time.isoformat(),
                "outline_ready": slide_stats.get("total", 0) > 0,
                "slide_stats": {
                    **slide_stats,
                    "percentage": percentage,
                },
            }
        )

    return jsonable_encoder(summaries)


@router.get("/api/files")
def list_project_files(project: str = Query(..., min_length=1)):
    if not _is_safe_name(project):
        raise HTTPException(status_code=400, detail="无效的项目名称")

    html_dir = PROJECTS_ROOT / project / "html_files"

    if not html_dir.exists() or not html_dir.is_dir():
        raise HTTPException(status_code=404, detail="无法读取HTML文件目录")

    files = [
        entry.name
        for entry in html_dir.iterdir()
        if entry.is_file() and entry.suffix.lower() == ".html"
    ]

    files.sort(key=_html_sort_key)
    return files


# 创建新项目
@router.post("/api/projects")
def add_project(req: ProjectIn, background_tasks: BackgroundTasks):
    project_id = str(uuid.uuid4())
    now_time = datetime.now()
    project_name = req.topic.replace(" ", "_") + "_" + time_name()
    topic = req.topic
    audience = req.audience
    style = req.style
    page_num = req.page_num
    reference_content = req.reference_content
    enable_img_search = req.enable_img_search

    project = Project(
        project_id=project_id,
        project_name=project_name,
        topic=topic,
        audience=audience,
        style=style,
        page_num=page_num,
        enable_img_search=enable_img_search,
        status="pending",
        create_time=now_time,
    )

    outline_config = Outline(
        project_id=project_id,
        topic=topic,
        audience=audience,
        style=style,
        page_num=page_num,
        enable_img_search=enable_img_search,
        reference_content=reference_content
    )

    # 先保存要返回的值
    pid = project.project_id
    pname = project.project_name

    logger.info(f"接收到的数据: {req}")
    ok = project_repo.db_add_project(
        project=project
    )
    if ok:
        logger.info(f"项目 {pid} 写入数据库成功")
        background_tasks.add_task(create_project_execute, outline_config)
        pstatus = "start"
        return {
            "project_id": pid,
            "project_name": pname,
            "status": pstatus,
            "enable_img_search": enable_img_search,
        }
    raise HTTPException(status_code=500, detail="创建项目失败")

# 删除某个项目
@router.delete("/api/projects/{project_id}")
def delete_project(project_id: str):
    ok = delete_project_with_related(project_id)
    if not ok:
        raise HTTPException(status_code=404, detail="项目不存在或删除失败")
    return {"message": "项目删除成功"}

@router.post("/api/save")
def save_project_file(req: SaveFileRequest):
    if not _is_safe_name(req.project) or not _is_safe_name(req.file):
        raise HTTPException(status_code=400, detail="无效的文件或项目名")

    target_dir = PROJECTS_ROOT / req.project / "html_files"
    if not target_dir.exists() or not target_dir.is_dir():
        raise HTTPException(status_code=404, detail="无法读取HTML文件目录")

    target_path = target_dir / req.file
    if target_path.suffix.lower() != ".html":
        raise HTTPException(status_code=400, detail="仅允许保存HTML文件")

    try:
        target_path.write_text(req.content, encoding="utf-8")
    except Exception as exc:
        logger.error("无法保存文件 %s: %s", target_path, exc)
        raise HTTPException(status_code=500, detail="保存文件失败") from exc

    return {"message": "文件保存成功"}


@router.get("/api/config")
def get_config_items():
    meta = [
        {
            "key": item["key"],
            "label": item.get("label") or item["key"],
            "type": item.get("type", "text"),
            "group": item.get("group") or "未分组",
            "description": item.get("description", ""),
            "placeholder": item.get("placeholder", ""),
        }
        for item in CONFIG_ITEMS
    ]
    return {
        "meta": meta,
        "values": get_effective_config(),
        "overrides": get_runtime_overrides(),
    }


@router.post("/api/config")
def update_config_items(payload: ConfigUpdateRequest):
    updates = payload.updates or {}
    sanitized_updates: dict[str, Any] = {}
    errors = []
    for key, value in updates.items():
        if key not in CONFIG_ITEM_MAP:
            continue
        item = CONFIG_ITEM_MAP[key]
        if item.get("type") == "number":
            try:
                sanitized_updates[key] = int(value)
            except (TypeError, ValueError):
                errors.append(f"{item.get('label', key)} 必须为整数")
        else:
            if value is None or value == "":
                continue
            sanitized_updates[key] = str(value)

    if errors:
        raise HTTPException(status_code=400, detail="; ".join(errors))

    if not sanitized_updates:
        return {
            "message": "未检测到可保存的配置",
            "values": get_effective_config(),
            "overrides": get_runtime_overrides(),
            "meta": [
                {
                    "key": item["key"],
                    "label": item.get("label") or item["key"],
                    "type": item.get("type", "text"),
                    "group": item.get("group") or "未分组",
                    "description": item.get("description", ""),
                    "placeholder": item.get("placeholder", ""),
                }
                for item in CONFIG_ITEMS
            ],
        }

    update_runtime_overrides(sanitized_updates)
    return {
        "message": "配置更新成功",
        "values": get_effective_config(),
        "overrides": get_runtime_overrides(),
        "meta": [
            {
                "key": item["key"],
                "label": item.get("label") or item["key"],
                "type": item.get("type", "text"),
                "group": item.get("group") or "未分组",
                "description": item.get("description", ""),
                "placeholder": item.get("placeholder", ""),
            }
            for item in CONFIG_ITEMS
        ],
    }


@router.get("/api/projects/{project_id}/status")
def get_project_status(project_id: str):
    project_status = project_repo.db_get_project_status(project_id)
    if not project_status:
        raise HTTPException(status_code=404, detail="项目不存在")
    return {"project_id": project_id, "status": project_status}


@router.get("/api/projects/{project_id}")
def get_project_detail(project_id: str):
    project = project_repo.db_get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    slide_stats = outline_repo.db_get_slide_status(project_id)
    total = slide_stats.get("total", 0)
    completed = slide_stats.get("completed", 0)
    percentage = round(completed / total * 100, 2) if total else 0.0

    outline = outline_repo.db_get_outline(project_id)

    payload = {
        "project": {
            "project_id": project.project_id,
            "project_name": project.project_name,
            "topic": project.topic,
            "audience": project.audience,
            "style": project.style,
            "page_num": project.page_num,
            "status": project.status,
            "enable_img_search": project.enable_img_search,
            "pdf_status": project.pdf_status,
            "pptx_status": project.pptx_status,
            "created_at": project.create_time.isoformat(),
        },
        "slide_stats": {**slide_stats, "percentage": percentage},
        "outline_ready": outline is not None,
    }

    if outline:
        payload["outline_summary"] = {
            "global_visual_suggestion": outline.global_visual_suggestion,
            "has_images": bool(outline.images),
        }

    return jsonable_encoder(payload)


@router.get("/api/projects/{project_id}/outline")
def get_project_outline(project_id: str):
    outline = outline_repo.db_get_outline(project_id)
    if not outline:
        raise HTTPException(status_code=404, detail="未找到项目大纲")

    data = model_to_dict(outline)
    return jsonable_encoder(data)


@router.get("/api/projects/{project_id}/slides")
def get_project_slides(project_id: str):
    project = project_repo.db_get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    slides = outline_repo.db_list_outline_slides(project_id)
    items = []
    for slide in slides:
        chapter_title = slide.chapter_title or (f"第 {slide.chapter_id} 章" if slide.chapter_id else "")
        items.append(
            {
                "slide_id": slide.slide_id,
                "chapter_id": slide.chapter_id,
                "chapter_title": chapter_title,
                "slide_order": slide.slide_order,
                "slide_topic": slide.slide_topic,
                "status": slide.status,
                "html_ready": bool(slide.html_content),
            }
        )

    return jsonable_encoder({
        "project_id": project_id,
        "project_name": project.project_name,
        "slides": items,
    })


@router.get("/api/projects/{project_id}/slides/{slide_id}")
def get_project_slide_detail(project_id: str, slide_id: str):
    slide = outline_repo.db_get_outline_slide(project_id, slide_id)
    if not slide:
        raise HTTPException(status_code=404, detail="未找到指定幻灯片")

    data = model_to_dict(slide)
    return jsonable_encoder(data)

@router.post("/api/projects/{project_id}/restart")
def restart_project(project_id: str, background_tasks: BackgroundTasks):
    project = project_repo.db_get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    ok = project_repo.db_update_project(project_id, Status.generating)
    if not ok:
        raise HTTPException(status_code=500, detail="无法更新项目状态")

    background_tasks.add_task(restart_project_execute, project_id)
    return {"project_id": project_id, "status": Status.generating}


@router.post("/api/projects/{project_id}/slides/{slide_id}/restart")
def restart_slide(project_id: str, slide_id: str, background_tasks: BackgroundTasks):
    slide = outline_repo.db_get_outline_slide(project_id, slide_id)
    if not slide:
        raise HTTPException(status_code=404, detail="未找到指定幻灯片")

    ok_slide = outline_repo.db_update_outline_slide(
        project_id=project_id, slide_id=slide_id, new_status=Status.generating
    )
    if not ok_slide:
        raise HTTPException(status_code=500, detail="无法更新幻灯片状态")

    ok_project = project_repo.db_update_project(project_id, Status.generating)
    if not ok_project:
        raise HTTPException(status_code=500, detail="无法更新项目状态")
    background_tasks.add_task(restart_slide_execute, project_id, slide_id)
    return {
        "project_id": project_id,
        "slide_id": slide_id,
        "status": Status.generating,
    }

@router.get("/api/projects/{project_id}/export/pdf")
def export_project_to_pdf(project_id: str, background_tasks: BackgroundTasks):
    project = project_repo.db_get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    if project.status != Status.completed:
        raise HTTPException(status_code=400, detail="项目未完成,不能导出PDF!")
    if project.pdf_status == Status.completed:
        return {"project_id": project_id, "status": Status.completed}
    if project.pdf_status == Status.generating:
        return {"project_id": project_id, "status": Status.generating}

    started = project_repo.db_try_start_pdf_export(project_id)
    if not started:
        return {"project_id": project_id, "status": Status.generating}

    logger.info(f"开始导出项目 {project_id} 到 PDF")
    background_tasks.add_task(html2office, project_id=project_id, to_pdf = True, to_pptx = False)
    return {"project_id": project_id, "status": Status.generating}

@router.get("/api/projects/{project_id}/export/pptx")
def export_project_to_pptx(project_id: str, background_tasks: BackgroundTasks):
    project = project_repo.db_get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    if project.status != Status.completed:
        raise HTTPException(status_code=400, detail="项目未完成,不能导出PPTX!")
    if project.pptx_status == Status.completed:
        return {"project_id": project_id, "status": Status.completed}
    if project.pptx_status == Status.generating:
        return {"project_id": project_id, "status": Status.generating}

    started = project_repo.db_try_start_pptx_export(project_id)
    if not started:
        return {"project_id": project_id, "status": Status.generating}

    logger.info(f"开始导出项目 {project_id} 到 PPTX")
    background_tasks.add_task(html2office, project_id=project_id, to_pdf = True, to_pptx = True)
    return {"project_id": project_id, "status": Status.generating}
