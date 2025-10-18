import os
from pathlib import Path
import sys
from dotenv import load_dotenv

# 将项目根目录添加到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config.logging_config import logger
env_path = project_root / '.env'
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
    logger.info(f"✅成功从 {env_path} 加载环境变量")
else:
    logger.error(f"未找到 {env_path} ")
    assert False, "请创建 .env 文件并设置必要的环境变量"


# === 大纲模型配置 ===
OUTLINE_API_TYPE = str(os.getenv("OUTLINE_API_TYPE"))
OUTLINE_API_KEY = str(os.getenv("OUTLINE_API_KEY"))
OUTLINE_API_URL = str(os.getenv("OUTLINE_API_URL"))
OUTLINE_MODEL = str(os.getenv("OUTLINE_MODEL"))

# === PPT/HTML生成模型配置 ===
PPT_API_TYPE = str(os.getenv("PPT_API_TYPE") or OUTLINE_API_TYPE)
PPT_API_KEY = str(os.getenv("PPT_API_KEY") or OUTLINE_API_KEY)
PPT_API_URL = str(os.getenv("PPT_API_URL") or OUTLINE_API_URL)
PPT_MODEL = str(os.getenv("PPT_MODEL") or OUTLINE_MODEL)

# === 图片理解模型配置 ===
PIC_API_TYPE = str(os.getenv("PIC_API_TYPE") or OUTLINE_API_TYPE)
PIC_API_KEY = str(os.getenv("PIC_API_KEY") or OUTLINE_API_KEY)
PIC_API_URL = str(os.getenv("PIC_API_URL") or OUTLINE_API_URL)
PIC_MODEL = str(os.getenv("PIC_MODEL") or OUTLINE_MODEL)
PIC_NUM_LIMIT = int(os.getenv("PIC_NUM_LIMIT", 5))

# === 搜索引擎配置 ===
SEARXNG_URL = str(os.getenv("SEARXNG_URL"))

TAVILY_KEY = str(os.getenv("TAVILY_KEY"))
TAVILY_MAX_NUM = int(os.getenv("TAVILY_MAX_NUM", 20))

# === 并发配置 ===
IMAGE_DOWNLOAD_MAX_WORKERS = int(os.getenv("IMAGE_DOWNLOAD_MAX_WORKERS", 15))
HTML_GENERATION_MAX_WORKERS = int(os.getenv("HTML_GENERATION_MAX_WORKERS", 8))
HTML2OFFICE_MAX_CONCURRENT_TASKS = int(
    os.getenv("HTML2OFFICE_MAX_CONCURRENT_TASKS", 4)
)


# === 配置类 ===
class LLMConfig:
    def __init__(self, name: str, api_key: str, api_url: str, api_type: str):
        self.name = name
        self.api_key = api_key
        self.api_url = api_url
        self.api_type = api_type
    
    def __repr__(self):
        return f"LLMConfig(name='{self.name}', api_key='{self.api_key[:10]}...', api_url='{self.api_url}', api_type='{self.api_type}')"

# 创建配置实例
OUTLINE_LLM_CONFIG = LLMConfig(
    name=OUTLINE_MODEL,
    api_key=OUTLINE_API_KEY,
    api_url=OUTLINE_API_URL,
    api_type=OUTLINE_API_TYPE
)

PPT_LLM_CONFIG = LLMConfig(
    name=PPT_MODEL,
    api_key=PPT_API_KEY,
    api_url=PPT_API_URL,
    api_type=PPT_API_TYPE
)

PIC_LLM_CONFIG = LLMConfig(
    name=PIC_MODEL,
    api_key=PIC_API_KEY,
    api_url=PIC_API_URL,
    api_type=PIC_API_TYPE
)
