import time
import traceback
import requests
import sys
from pathlib import Path

# 将项目根目录添加到 Python 路径，使能够导入项目中的其他模块
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

import config.base_config as base_config
from config.logging_config import logger
from src.utils.help_utils import retry_on_failure


@retry_on_failure(max_attempts=3, delay=2, description="进行Searxng搜索")
def search_searxng(
    query, language="zh-cn", time_page=[0, 0, 0], images_search=False
) -> list:
    """
    使用 SearXNG 搜索引擎 API 进行搜索

    参数:
        query (str): 搜索关键词
        language (str): 搜索语言，默认为 "zh-cn"（简体中文）语法符合ISO 639-1标准
        time_page (list): 时间分页参数，格式为 [offset, limit, time_range]，默认为 [0, 0, 0]
        images_search (bool): 是否进行图片搜索，默认为 False（网页搜索）

    返回:
        list: 搜索结果列表，每个元素是一个包含搜索结果信息的字典
              如果搜索失败或无结果则返回空列表
    """

    # 定义图片搜索使用的搜索引擎
    images_search_engines = "google_images,bing_images"
    # 定义网页搜索使用的搜索引擎
    web_search_engines = "bing,duckduckgo,google,wikipedia"
    # 根据是否进行图片搜索设置不同的请求参数
    if images_search:
        params = {
            "q": query,  # 搜索关键词
            "format": "json",  # 返回格式为 JSON
            "time_page": time_page,  # 时间分页参数
            "engines": images_search_engines,  # 图片搜索引擎
            "categories": "images",  # 搜索类别为图片
        }
    else:
        params = {
            "q": query,  # 搜索关键词
            "format": "json",  # 返回格式为 JSON
            "language": language,  # 搜索语言
            "engines": web_search_engines,  # 网页搜索引擎
            "time_page": time_page,  # 时间分页参数
        }

    try:
        # 记录搜索日志
        logger.info(f"正在搜索: '{query}' (语言:{language}, 时间页:{time_page})")

        response = requests.get(base_config.SEARXNG_URL, params=params, timeout=40)
        response.raise_for_status()
        # logger.info(f"搜索成功: '{response.json()}'")
        results = response.json().get("results", [])
        if not results:
            logger.warning(f"搜索关键词 '{query}' 未返回任何结果")
            raise Exception(f"搜索关键词 '{query}' 未返回任何结果")
        return results

    except Exception as e:
        logger.debug(f"搜索关键词 '{query}' 时发生错误: {str(e)}. ")
        raise Exception(
            f"搜索关键词 '{query}' 时发生错误: {str(e)}. 响应内容: {response.text}"
        )


# 当脚本直接运行时执行测试代码
if __name__ == "__main__":
    test_query = "猫"
    results = search_searxng(test_query, images_search=False)
    # 打印搜索结果
    for result in results:
        print(result)
