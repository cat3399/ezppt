import os
from urllib.parse import urlparse
import sys
from pathlib import Path

# 将项目根目录添加到 Python 路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from services.search.searxng_provider import search_searxng
from config.logging_config import logger

# TODO 增加网络搜索的功能