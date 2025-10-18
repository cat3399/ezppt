import json
import sys
from pathlib import Path

# 将项目根目录添加到 Python 路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.services.chat.chat import pic_understand
from src.services.search.image_search import image_search
from src.utils.help_utils import get_prompt, response2list
from config.logging_config import logger
import config.base_config as base_config


def get_pic(
    query: str,
    description: str,
    pic_num_limit: int = base_config.PIC_NUM_LIMIT,
    img_base_path: str = str(project_root / "data" / "images"),
):
    """获取与指定查询相关的图片，并进行理解分析。
    Args:
        query (str): 查询关键词
        max_pic_num (int): 最大图片数量
    """
    results = {}
    img_search_results = image_search(
        query=query, pic_num_limit=pic_num_limit, img_base_path=img_base_path
    )
    # logger.info(f"图片搜索结果 {results.keys()}")
    # logger.info(f"图片搜索结果 {results.values()}")
    base_prompt = get_prompt("pic_understand")
    imgs_info = ""
    for i, value in enumerate(img_search_results.values()):
        imgs_info += f"""\n
        图片编号 {i+1} : 标题: {value.title}, 简介: {value.content}, 图片链接: {value.img_url[:200]} 分辨率: {value.height}x{value.width}
        """
    id2key = {
        idx + 1: key for idx, key in enumerate(img_search_results.keys())
    }  # 创建一个字典，将图片编号映射到对应的图片键名
    prompt = base_prompt.format(description=description, imgs_info=imgs_info)
    images_base64 = [
        value.img_base64 for value in img_search_results.values() if value.img_base64
    ]
    # logger.info(prompt)
    pic_results = pic_understand(images_base64=images_base64, prompt=prompt)
    pic_results = response2list(pic_results)
    for result in pic_results:
        img_id = int(result["img_id"])
        # 检查 img_id 是否在 id2key 的有效范围内
        if img_id not in id2key:
            logger.warning(
                f"无效图片ID: {img_id}（有效范围: 1~{len(id2key)}），跳过处理"
            )
            logger.warning(f"大模型返回结果{pic_results}")
            continue
        description = result["img_description"]
        img_info = img_search_results[id2key[img_id]]
        img_info.description = description
        results[id2key[img_id]] = img_info
    return results


if __name__ == "__main__":
    query = "芯片 晶圆 半导体"
    description = "一张展示芯片制造过程的高清图片，用作科技类PPT的背景图"
    results = get_pic(query=query, description=description)
    logger.info(f"图片理解结果: {results}")
