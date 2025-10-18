import base64
import os
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from pathlib import Path
import sys
import traceback
import hashlib

from PIL import Image

# 将项目根目录添加到 Python 路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from services.search.searxng_provider import search_searxng
from src.utils.help_utils import download_image
from config.logging_config import logger
from config.base_config import PIC_NUM_LIMIT, IMAGE_DOWNLOAD_MAX_WORKERS

MAX_RETRIES = 3
IMG_PATH = "data/images"


class ImageInfo:
    """图片信息类"""

    def __init__(
        self,
        img_url,
        thumbnail_url,
        title,
        content,
        img_content=None,
        img_base64="",
        width=0,
        height=0,
        file_path="",
        description="",
    ):
        self.img_url = img_url
        self.thumbnail_url = thumbnail_url
        self.title = title
        self.content = content
        self.img_content = img_content
        self.img_base64 = img_base64
        self.width = width
        self.height = height
        self.file_path = file_path
        self.description = description

    def __repr__(self):
        return (
            f"ImageInfo(img_url={self.img_url!r}, "
            f"thumbnail_url={self.thumbnail_url!r}, "
            f"title={self.title!r}, "
            f"content={self.content!r}, "
            # f"img_content={self.img_content!r}, "
            # f"img_base64={self.img_base64!r}, "
            f"width={self.width}, "
            f"height={self.height}, "
            f"file_path={self.file_path!r}, "
            f"description={self.description!r})"
        )

    def __str__(self):
        return self.__repr__()


def normalize_url(url):
    """标准化URL协议"""
    if url.startswith("//"):
        return "https:" + url
    elif url and not url.startswith("http"):
        return "https://" + url
    return url


def get_filename_from_url(url, img_base_path=str(project_root / "data" / "images")):
    """从 URL 中提取文件名 使用定长哈希"""
    url_hash = hashlib.md5(url.encode("utf-8")).hexdigest()[:6]
    filename_path = img_base_path + "/" + url_hash
    return filename_path + ".png"


def process_img_file(img_path, img_info_temp):
    """处理单个图片文件"""
    try:
        with Image.open(img_path) as img_temp:
            # 转换图片模式
            if img_temp.mode in ("RGBA", "LA", "P"):
                img_temp = img_temp.convert("RGB")

            width, height = img_temp.size
            # print(f"处理图片 {img_path} 大小: {width}x{height} 分辨率总和: {width * height}")
            # 转换为base64
            buffered = BytesIO()
            img_temp.save(buffered, format="JPEG")
            img_base64 = base64.b64encode(buffered.getvalue()).decode()
            if width * height != 0:
                img_info = ImageInfo(
                    img_url=img_info_temp.img_url,
                    thumbnail_url=img_info_temp.thumbnail_url,
                    title=img_info_temp.title,
                    content=img_info_temp.content,
                    img_content=img_temp.copy(),
                    img_base64=img_base64,
                    width=width,
                    height=height,
                    file_path=img_path,
                )
                return img_info
            else:
                logger.warning(f"警告: 图片 {img_path} 大小为0，跳过该图片")
                return None

    except Exception as e:
        logger.error(f"警告: 无法处理图片文件 {img_path}: {e}")
        traceback.print_exc()


def image_search(
    query,
    pic_num_limit=PIC_NUM_LIMIT,
    time_page=[0, 0, 0],
    img_base_path: str = str(project_root / "data" / "images"),
) -> dict:
    """
    图片搜索主函数

    Args:
        query: 搜索关键词
        max_img_count: 最大图片数量
        time_page: 时间页面设置

    Returns:
        dict: 包含图片信息的字典
    """
    os.makedirs(IMG_PATH, exist_ok=True)
    img_info_dict_temp = {}
    img_info_dict = {}

    # 需要排除的域名列表
    BLOCKED_DOMAINS = {"www.artic.edu"}

    results = search_searxng(query=query, images_search=True)
    results = results[:pic_num_limit]

    for i, result in enumerate(results):
        img_url = normalize_url(result.get("img_src", ""))

        # 域名过滤 某些网站的图片链接有反爬机制，需要排除
        from urllib.parse import urlparse
        if img_url and urlparse(img_url).hostname.lower() in BLOCKED_DOMAINS:
            continue

        content = result.get("content", "")[:100]
        title   = result.get("title", "")[:100]
        thumbnail_url = normalize_url(result.get("thumbnail_src", ""))
        score   = result.get("score", 0)

        logger.info(f"结果 {i+1}: {title} - {content} - {img_url} - 分数: {score}")

        if img_url:
            filename = get_filename_from_url(img_url, img_base_path)
            img_info_dict_temp[filename] = ImageInfo(
                img_url, thumbnail_url, title, content
            )


    # 多线程下载图片
    logger.info("开始下载")
    with ThreadPoolExecutor(max_workers=IMAGE_DOWNLOAD_MAX_WORKERS) as pool:
        futures = [
            pool.submit(download_image, value.img_url, key, value.thumbnail_url)
            for key, value in img_info_dict_temp.items()
        ]

        # 处理下载结果
        for future in futures:
            img_path = future.result()
            if img_path and os.path.exists(img_path):
                img_info = process_img_file(
                    img_path, img_info_temp=img_info_dict_temp[img_path]
                )
                if img_info:
                    img_info_dict[img_path] = img_info
            else:
                logger.warning(f"下载失败或文件不存在: {img_path}")

    return img_info_dict


if __name__ == "__main__":
    test_query = "哈基米"
    images_info = image_search(query=test_query)
    print(images_info)
    for filename, info in images_info.items():
        print(f"文件: {filename}, 信息: {info}, 大小: {info.width}x{info.height}")
