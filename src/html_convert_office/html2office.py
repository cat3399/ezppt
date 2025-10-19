import sys
from pathlib import Path
import asyncio
import shutil
import traceback

project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from config.logging_config import logger
import config.base_config as base_config
from html_convert_office.html2pdf import generate_multiple_pdfs, merge_pdfs
from html_convert_office.pdf2pptx import convert_pdf_to_pptx
from src.repository import project_repo
from src.models.project_model import Status


def html2office(
    project_id: str,
    to_pdf: bool = True,
    to_pptx: bool = True,
    max_concurrent_tasks: int | None = None,
    timeout: int = 60,
):
    try:
        project = project_repo.db_get_project(project_id)
        if project is None:
            logger.error(f"项目ID {project_id} 不存在")
            return

        project_name = project.project_name
        project_base_path = project_root / "data" / "projects" / project_name
        temp_pdf_path = project_root / "data" / "temp" / project_name
        temp_pdf_path.mkdir(parents=True, exist_ok=True)

        merged_pdf_path = project_base_path / str(project_name + ".pdf")
        output_pptx_path = project_base_path / str(project_name + ".pptx")
        html_files_dir_path = project_base_path / "html_files"

        html_file_names = sorted(
            [
                f.name
                for f in html_files_dir_path.iterdir()
                if f.is_file() and f.suffix == ".html"
            ],
            key=lambda x: (int(x.split(".")[0]), int(x.split(".")[1])),
        )

        pdf_file_names = [f.rsplit(".", maxsplit=1)[0] + ".pdf" for f in html_file_names]
        logger.info(f"HTML文件列表: {html_file_names}")
        logger.info(f"PDF文件列表: {pdf_file_names}")

        pdf_conversion_tasks = [
            (str(html_files_dir_path / html_file), str(temp_pdf_path / pdf_file))
            for html_file, pdf_file in zip(html_file_names, pdf_file_names)
        ]

        effective_limit = max_concurrent_tasks or base_config.PPT_API_LIMIT

        if to_pdf or to_pptx:
            if not merged_pdf_path.exists():
                ok = asyncio.run(
                    generate_multiple_pdfs(
                        pdf_conversion_tasks,
                        max_concurrent_tasks=effective_limit,
                        timeout=timeout,
                    )
                )
                if ok:
                    merge_pdfs(
                    [str(temp_pdf_path / pdf_file) for pdf_file in pdf_file_names],
                    str(merged_pdf_path),
                )
                    project_repo.db_update_project(project_id, new_pdf_status=Status.completed)
                else:
                    project_repo.db_update_project(project_id, new_pdf_status=Status.failed)
            else:
                logger.info(f"PDF文件已存在: {merged_pdf_path}")
                project_repo.db_update_project(project_id, new_pdf_status=Status.completed)
            shutil.rmtree(temp_pdf_path, ignore_errors=True)
        if to_pptx:
            ok = convert_pdf_to_pptx(
                pdf_path=str(merged_pdf_path), pptx_path=str(output_pptx_path)
            )
            if not ok:
                project_repo.db_update_project(project_id, new_pptx_status=Status.failed)
            else:
                project_repo.db_update_project(project_id, new_pdf_status=Status.completed)
                project_repo.db_update_project(project_id, new_pptx_status=Status.completed)
    except Exception as e:
        if to_pptx:
            project_repo.db_update_project(project_id, new_pptx_status=Status.failed)
            project_repo.db_update_project(project_id, new_pdf_status=Status.failed)
        else:
            project_repo.db_update_project(project_id, new_pdf_status=Status.failed)
        logger.error(f"转换失败: {e}")
        logger.error(traceback.format_exc())
    finally:
        shutil.rmtree(temp_pdf_path, ignore_errors=True)



# if __name__ == "__main__":
#     html2office("44433ab3-c3e3-485a-abfb-a5c4b478e9ea")
