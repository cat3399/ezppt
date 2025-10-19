import argparse
import sys
import platform
import requests
import zipfile
import tarfile
from pathlib import Path
from apryse_sdk.PDFNetPython import PDFNet, Convert

# 将项目根目录添加到 sys.path 中
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from config.logging_config import logger
import config.base_config as base_config

lib_path = Path(__file__).resolve().parent / "Lib"


def get_lib_url():
    """根据系统信息返回对应的Lib目录压缩包下载链接"""
    system = platform.system().lower()
    machine = platform.machine().lower()

    if system == "linux":
        if machine in ["aarch64", "arm64"]:
            return "https://pdftron.s3.amazonaws.com/downloads/StructuredOutputLinuxArm64.tar.gz"
        else:
            return "https://pdftron.s3.amazonaws.com/downloads/StructuredOutputLinux.tar.gz"
    elif system == "windows":
        return "https://pdftron.s3.amazonaws.com/downloads/StructuredOutputWindows.zip"
    elif system == "darwin":
        return "https://www.pdftron.com/downloads/StructuredOutputMac.zip"
    else:
        raise RuntimeError(f"不支持的操作系统: {system}")


def download_and_extract_lib(url: str, extract_to: Path):
    """下载并解压Lib资源文件"""
    logger.info(f"🌐 正在下载Lib资源文件: {url}")
    local_filename = extract_to / (url.split("/")[-1])

    response = requests.get(url, stream=True)
    response.raise_for_status()

    # 获取文件总大小
    total_size = int(response.headers.get("content-length", 0))
    downloaded_size = 0
    chunk_count = 0  # 添加计数器

    with open(local_filename, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)
                downloaded_size += len(chunk)
                chunk_count += 1

                # 每下载5次才打印一次进度
                if chunk_count % 300 == 0:
                    if total_size > 0:
                        progress = (downloaded_size / total_size) * 100
                        logger.info(
                            f"📥 下载进度: {progress:.1f}% ({downloaded_size}/{total_size} bytes)"
                        )
                    else:
                        logger.info(f"📥 已下载: {downloaded_size} bytes")

    # 最后打印一次最终进度
    if total_size > 0:
        progress = (downloaded_size / total_size) * 100
        logger.info(
            f"📥 下载完成: {progress:.1f}% ({downloaded_size}/{total_size} bytes)"
        )
    else:
        logger.info(f"📥 下载完成: {downloaded_size} bytes")

    logger.info("📦 正在解压Lib资源...")

    if local_filename.suffix == ".zip":
        with zipfile.ZipFile(local_filename, "r") as zip_ref:
            zip_ref.extractall(extract_to)
    elif local_filename.suffix == ".gz":
        with tarfile.open(local_filename, "r:gz") as tar_ref:
            tar_ref.extractall(extract_to)
    else:
        raise RuntimeError("未知压缩格式")

    local_filename.unlink()  # 删除下载的压缩包
    logger.info("✅ Lib资源已成功准备")


def ensure_lib_exists():
    """确保Lib目录存在，如果不存在则根据系统自动下载"""
    if not lib_path.exists():
        logger.warning(f"🔍 {lib_path}目录不存在，将自动下载对应的版本...")
        url = get_lib_url()
        download_and_extract_lib(url, lib_path.parent)


def convert_pdf_to_pptx(pdf_path: str, pptx_path: str) -> bool:
    """转换PDF到PPTX"""
    logger.info(f"📄 正在将 PDF 转换为 PowerPoint 文件...")
    PDFNet.Initialize(base_config.APRYSE_LICENSE_KEY)
    ensure_lib_exists()
    PDFNet.AddResourceSearchPath(str(lib_path))
    try:
        Convert.ToPowerPoint(pdf_path, pptx_path)
        logger.info(f"✅ 成功生成 PowerPoint 文件: {pptx_path}")
        return True
    except Exception as e:
        logger.error(f"❌ 任务执行失败 ({pdf_path}), 错误: {e}")
        return False
    finally:
        PDFNet.Terminate()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="将PDF文件转换为PowerPoint文件")
    parser.add_argument("pdf_path", help="输入PDF文件路径")
    parser.add_argument("pptx_path", help="输出PPTX文件路径")

    args = parser.parse_args()

    # 检查PDF文件是否存在
    pdf_file = Path(args.pdf_path)
    if not pdf_file.exists():
        logger.error(f"❌ PDF文件不存在: {args.pdf_path}")
        sys.exit(1)

    # 确保输出目录存在
    pptx_file = Path(args.pptx_path)
    pptx_file.parent.mkdir(parents=True, exist_ok=True)

    # 执行转换
    success = convert_pdf_to_pptx(str(pdf_file), str(pptx_file))
    sys.exit(0 if success else 1)
