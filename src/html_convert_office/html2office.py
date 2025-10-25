import sys
from pathlib import Path
import asyncio
import shutil
import traceback
import multiprocessing

# --- 其他代码保持不变 ---
# (项目根目录设置, imports等)
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
    temp_pdf_path = None
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

        pdf_file_names = [
            f.rsplit(".", maxsplit=1)[0] + ".pdf" for f in html_file_names
        ]
        logger.info(f"HTML文件列表: {html_file_names}")
        logger.info(f"PDF文件列表: {pdf_file_names}")

        pdf_conversion_tasks = [
            (str(html_files_dir_path / html_file), str(temp_pdf_path / pdf_file))
            for html_file, pdf_file in zip(html_file_names, pdf_file_names)
        ]

        effective_limit = max_concurrent_tasks or base_config.HTML2OFFICE_MAX_CONCURRENT_TASKS

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
                    project_repo.db_update_project(
                        project_id, new_pdf_status=Status.completed
                    )
                else:
                    project_repo.db_update_project(
                        project_id, new_pdf_status=Status.failed
                    )
                    if to_pptx:
                         project_repo.db_update_project(
                            project_id, new_pptx_status=Status.failed
                        )
                    return
            else:
                logger.info(f"PDF文件已存在: {merged_pdf_path}")
                project_repo.db_update_project(
                    project_id, new_pdf_status=Status.completed
                )
        
        # ==================== to_pptx 逻辑块修改 ====================
        if to_pptx:
            if not merged_pdf_path.exists():
                logger.error(f"无法进行PPTX转换，因为依赖的PDF文件不存在: {merged_pdf_path}")
                project_repo.db_update_project(project_id, new_pptx_status=Status.failed)
                return

            logger.info(f"准备在独立的子进程中执行PDF到PPTX的转换...")
            
            conversion_process = multiprocessing.Process(
                target=convert_pdf_to_pptx, 
                args=(str(merged_pdf_path), str(output_pptx_path)),
                name=f"PPTX-Converter-{project_id[:8]}"
            )
            conversion_process.start()
            TIMEOUT_SECONDS = 300
            conversion_process.join(timeout=TIMEOUT_SECONDS)

            if conversion_process.is_alive():
                logger.warning(f"子进程 {conversion_process.name} 超时({TIMEOUT_SECONDS}秒)，正在强制终止...")
                conversion_process.terminate()
                conversion_process.join(5)
                if conversion_process.is_alive():
                    conversion_process.kill()
                logger.error(f"PPTX转换任务因超时而失败。")
                project_repo.db_update_project(
                    project_id, new_pptx_status=Status.failed
                )
            else:
                if conversion_process.exitcode == 0:
                    # 我们需要一种方式知道 convert_pdf_to_pptx 的返回值
                    # 但跨进程返回值需要用 Queue 或 Pipe，会增加复杂性。
                    # 更简单的方式是检查输出文件是否存在。
                    if output_pptx_path.exists() and output_pptx_path.stat().st_size > 0:
                        logger.info(f"PPTX转换任务成功完成。")
                        project_repo.db_update_project(
                            project_id, new_pptx_status=Status.completed
                        )
                    else:
                        # 子进程退出了，但文件没生成，说明内部出错了
                        logger.error(f"子进程正常退出，但未生成有效的PPTX文件。")
                        project_repo.db_update_project(
                            project_id, new_pptx_status=Status.failed
                        )
                else:
                    # 子进程以非零退出码结束，表示有错误发生
                    logger.error(f"子进程以错误码 {conversion_process.exitcode} 退出，PPTX转换任务失败。")
                    project_repo.db_update_project(
                        project_id, new_pptx_status=Status.failed
                    )

    except Exception as e:
        if to_pptx:
            project_repo.db_update_project(project_id, new_pptx_status=Status.failed)
            project_repo.db_update_project(project_id, new_pdf_status=Status.failed)
        else:
            project_repo.db_update_project(project_id, new_pdf_status=Status.failed)
        logger.error(f"html2office 任务执行失败: {e}")
        logger.error(traceback.format_exc())
    finally:
        if temp_pdf_path and temp_pdf_path.exists():
             shutil.rmtree(temp_pdf_path, ignore_errors=True)

