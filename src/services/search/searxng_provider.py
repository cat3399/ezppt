import time
import traceback
import requests
import sys
from pathlib import Path

# 将项目根目录添加到 Python 路径，使能够导入项目中的其他模块
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# 导入项目配置文件中的 SEARXNG 服务地址和日志记录器
from config.base_config import SEARXNG_URL
from config.logging_config import logger

# 定义最大重试次数，用于网络请求失败时的重试机制
MAX_RETRIES = 3


def search_searxng(query, language="zh-cn", time_page=[0, 0, 0], images_search=False):
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
    
    # 根据是否进行图片搜索设置不同的请求参数
    if images_search:
        params = {
            "q": query,              # 搜索关键词
            "format": "json",        # 返回格式为 JSON
            "time_page": time_page,  # 时间分页参数
            "engines": images_search_engines,  # 图片搜索引擎
            "categories": "images",  # 搜索类别为图片
        }
    else:
        # 定义网页搜索使用的搜索引擎
        web_search_engines = "bing,duckduckgo,google,wikipedia"
        params = {
            "q": query,              # 搜索关键词
            "format": "json",        # 返回格式为 JSON
            "language": language,    # 搜索语言
            "engines": web_search_engines,  # 网页搜索引擎
            "time_page": time_page,  # 时间分页参数
        }

    # 初始化重试计数器
    retry_count = 0
    
    # 循环重试直到达到最大重试次数
    while retry_count < MAX_RETRIES:
        try:
            # 记录搜索日志
            logger.info(f"正在搜索: '{query}' (语言:{language}, 时间页:{time_page})")
            
            # 发送 GET 请求到 SearXNG API
            response = requests.get(SEARXNG_URL, params=params, timeout=40)
            
            # 检查 HTTP 响应状态码，如果失败则抛出异常
            response.raise_for_status()
            # logger.info(f"搜索成功: '{response.json()}'")
            # 解析 JSON 响应并提取结果列表
            results = response.json()["results"]
            if not results:
                logger.warning(f"警告: 搜索关键词 '{query}' 未返回任何结果")
                assert False, "搜索结果为空，请检查 SearXNG 服务是否正常运行"
            return results

        # 处理网络请求相关的异常
        except Exception as e:
            retry_count += 1
            wait_time = 3  # 重试等待时间（秒）
            
            # 记录调试日志和错误日志
            logger.debug(
                f"搜索关键词 '{query}' 时发生错误: {str(e)}. "
                f"尝试次数 {retry_count}/{MAX_RETRIES}. "
                f"{f'等待 {wait_time} 秒后重试...' if retry_count < MAX_RETRIES else '已达最大重试次数.'}"
            )
            logger.error(traceback.format_exc())
            
            # 如果未达到最大重试次数，则等待后继续重试
            if retry_count < MAX_RETRIES:
                time.sleep(wait_time)

    # 如果达到最大重试次数仍然失败，记录错误并返回空列表
    logger.error(f"搜索关键词 '{query}' 失败，已重试 {MAX_RETRIES} 次。")
    return []

# 当脚本直接运行时执行测试代码
if __name__ == "__main__":
    test_query = "猫"  # 测试搜索关键词
    results = search_searxng(test_query, images_search=False)  # 执行网页搜索
    
    # 打印搜索结果
    for result in results:
        print(result)
