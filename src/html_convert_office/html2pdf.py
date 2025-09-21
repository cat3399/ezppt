import asyncio
import os
import shutil
import sys
from pathlib import Path
from pypdf import PdfWriter
from playwright.async_api import async_playwright, Browser

project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from config.logging_config import logger


async def create_pdf_from_html(
    browser: Browser, html_file_path: str, output_pdf_path: str, timeout: int = 60
) -> str:
    """
    在一个已存在的浏览器实例中创建一个新页面来生成 PDF。
    """
    absolute_html_path = Path(html_file_path).resolve()
    html_file_url = absolute_html_path.as_uri()

    context = await browser.new_context()
    page = await context.new_page()

    logger.info(f"📄 开始处理: {html_file_path}")

    try:
        await page.goto(html_file_url, wait_until="networkidle", timeout=timeout * 1000)

        await page.pdf(
            path=output_pdf_path,
            width="1280px",
            height="720px",
            print_background=True,
            margin={"top": "0px", "right": "0px", "bottom": "0px", "left": "0px"},
        )

        logger.info(f"✅ PDF 生成成功: {output_pdf_path}")
        return output_pdf_path
    except Exception as e:
        # 让异常向上抛出，由 asyncio.wait_for 和 gather 统一处理
        logger.error(f"❌ 在处理 {html_file_path} 时发生错误: {type(e).__name__} - {e}")
        raise e
    finally:
        await page.close()
        await context.close()


async def generate_multiple_pdfs(
    files_to_process: list[tuple[str, str]],
    timeout: int = 60,
    max_concurrent_tasks: int = 5,  # 新增控制并发数量参数
) -> bool:
    """
    启动一个浏览器会话，并发地处理多个 HTML 到 PDF 的转换任务。
    每个任务都有一个总的超时限制，并限制最大并发数。

    Args:
        files_to_process: 文件处理列表。
        task_timeout_seconds: 每个单独的PDF生成任务的超时时间（秒）。
        max_concurrent_tasks: 最大并发任务数量。
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        logger.info(
            f"🚀 每个html转pdf任务超时时间为 {timeout} 秒，最大并发数为 {max_concurrent_tasks}。"
        )

        semaphore = asyncio.Semaphore(max_concurrent_tasks)

        async def limited_create_pdf(html_path, pdf_path):
            async with semaphore:  # 控制并发数量
                return await create_pdf_from_html(browser, html_path, pdf_path, timeout=timeout)

        tasks = []
        for html_path, pdf_path in files_to_process:
            task = asyncio.wait_for(
                limited_create_pdf(html_path, pdf_path),
                timeout=timeout,
            )
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        logger.info("🎉 所有任务已完成。")
        successful_files = []
        failed_tasks = 0

        for i, res in enumerate(results):
            html_path, _ = files_to_process[i]
            if isinstance(res, Exception):
                failed_tasks += 1
                if isinstance(res, asyncio.TimeoutError):
                    logger.error(f"⏰ 任务超时失败 ({html_path})")
                else:
                    logger.error(f"💥 任务执行失败 ({html_path}), 错误: {res}")
            else:
                successful_files.append(res)

        logger.info("--- 任务总结 ---")
        logger.info(
            f"总任务数: {len(tasks)}, 成功: {len(successful_files)}, 失败: {failed_tasks}"
        )

        await browser.close()
        logger.info("🖐️ 浏览器已关闭。")
        return len(successful_files) != 0

def merge_pdfs(pdf_paths, output_path):
    """将多个 PDF 文件按传入顺序合并为一个"""
    try:
        with PdfWriter() as pdf_merger:
            for pdf_path in pdf_paths:
                pdf_merger.append(pdf_path)
            with open(output_path, "wb") as output_file:
                pdf_merger.write(output_file)
                logger.info(f"✅ 合并PDF成功 ({output_path})")
    except Exception as e:
        logger.error(f"💥 合并PDF失败, 错误: {e}")


# if __name__ == "__main__":
#     base_path = project_root / "data" / "projects" / "aas_20251013"
#     html_files_path = base_path / "html_files"
#     tmp_pdf_file_path = project_root / "data" / "temp" / "aas_20251013"
#     pdf_file_path = base_path / "aas_20251013.pdf"

#     html_list = [
#         f.name for f in html_files_path.iterdir() if f.is_file() and f.suffix == ".html"
#     ]
#     pdf_list = [f.rsplit(".", maxsplit=1)[0] + ".pdf" for f in html_list]
#     logger.info(f"HTML文件列表: {html_list}")
#     logger.info(f"PDF文件列表: {pdf_list}")

#     pdf_jobs = [
#         (str(html_files_path / html_file), str(tmp_pdf_file_path / pdf_file))
#         for html_file, pdf_file in zip(html_list, pdf_list)
#     ]

#     asyncio.run(generate_multiple_pdfs(pdf_jobs))
#     merge_pdfs(
#         [str(tmp_pdf_file_path / pdf_file) for pdf_file in pdf_list], str(pdf_file_path)
#     )
#     # 强制删除临时文件目录
#     shutil.rmtree(tmp_pdf_file_path, ignore_errors=True)
