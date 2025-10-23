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


# 全局变量，防止重复检查安装
_PLAYWRIGHT_INSTALLED = False


def ensure_playwright_installed():
    """确保 Playwright 已安装，并安装 chromium 浏览器（只执行一次）"""
    global _PLAYWRIGHT_INSTALLED
    if _PLAYWRIGHT_INSTALLED:
        return

    import subprocess

    try:
        # 只安装并仅使用 chromium，减少体积占用
        logger.info("🔍 检查并安装 Playwright 的 Chromium 浏览器中...")
        logger.info(
            f"请稍等，这可能需要一些时间...在此期间终端没有输出是正常的,如果想要查看进度,请中断此终端,另外运行 {sys.executable} -m playwright install chromium-headless-shell --with-deps "
        )
        subprocess.run(
            [
                sys.executable,
                "-m",
                "playwright",
                "install",
                "chromium-headless-shell",
                "--with-deps",
            ],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        logger.info("✅ Chromium 浏览器安装完成")
        _PLAYWRIGHT_INSTALLED = True
    except subprocess.CalledProcessError as e:
        logger.error(
            f"💥 安装 Playwright 浏览器失败，请手动执行 playwright install: {e}"
        )
        raise


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
        logger.error(f"❌ 在处理 {html_file_path} 时发生错误: {type(e).__name__} - {e}")
        raise e
    finally:
        await page.close()
        await context.close()


async def generate_multiple_pdfs(
    files_to_process: list[tuple[str, str]],
    timeout: int = 60,
    max_concurrent_tasks: int = 5,
) -> bool:
    """
    启动一个浏览器会话，并发地处理多个 HTML 到 PDF 的转换任务。
    每个任务都有一个总的超时限制，并限制最大并发数。
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        logger.info(
            f"🚀 每个html转pdf任务超时时间为 {timeout} 秒，最大并发数为 {max_concurrent_tasks}。"
        )

        semaphore = asyncio.Semaphore(max_concurrent_tasks)

        async def limited_create_pdf(html_path, pdf_path):
            async with semaphore:
                return await create_pdf_from_html(
                    browser, html_path, pdf_path, timeout=timeout
                )

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
