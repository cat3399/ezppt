import os
import threading
from pathlib import Path
import sys
from typing import Any, Dict
from dotenv import load_dotenv, set_key, dotenv_values

# 将项目根目录添加到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config.logging_config import logger

env_path = project_root / '.env'
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
    logger.info(f"✅成功从 {env_path} 加载环境变量")
else:
    logger.warning(f"未找到 {env_path} ")
    # assert False, "请创建 .env 文件并设置必要的环境变量"

_config_lock = threading.RLock()
_runtime_overrides: Dict[str, Any] = {}


def _load_runtime_overrides() -> Dict[str, Any]:
    if not env_path.exists():
        return {}
    overrides: Dict[str, Any] = {}
    try:
        raw_values = dotenv_values(dotenv_path=env_path) or {}
    except Exception as exc:  # pylint: disable=broad-except
        logger.error("读取 .env 失败: %s", exc)
        return {}

    for key, value in raw_values.items():
        if key not in CONFIG_ITEM_MAP:
            continue
        if value in (None, ""):
            continue
        try:
            overrides[key] = _sanitize_value(key, value)
        except ValueError as exc:
            logger.error(".env 中的配置 %s 无效: %s", key, exc)
    return overrides


def _get_config_value(key: str, default: Any = None) -> Any:
    with _config_lock:
        if key in _runtime_overrides:
            return _runtime_overrides[key]
    return os.getenv(key, default)


# === 基础配置占位符 ===
OUTLINE_API_TYPE = ""
OUTLINE_API_KEY = ""
OUTLINE_API_URL = ""
OUTLINE_MODEL = ""

PPT_API_TYPE = ""
PPT_API_KEY = ""
PPT_API_URL = ""
PPT_MODEL = ""
PPT_API_LIMIT = 4

PIC_API_TYPE = ""
PIC_API_KEY = ""
PIC_API_URL = ""
PIC_MODEL = ""
PIC_NUM_LIMIT = 5

APRYSE_LICENSE_KEY = ""

SEARXNG_URL = ""

TAVILY_KEY = ""
TAVILY_MAX_NUM = 20

IMAGE_DOWNLOAD_MAX_WORKERS = 15

# === 配置定义 ===
CONFIG_ITEMS = [
    {"key": "OUTLINE_API_TYPE", "label": "大纲 LLM API 类型", "type": "text", "group": "大纲模型", "description": "仅支持 openai 或 gemini"},
    {"key": "OUTLINE_API_KEY", "label": "大纲 LLM API Key", "type": "text", "group": "大纲模型"},
    {"key": "OUTLINE_API_URL", "label": "大纲 LLM API 地址", "type": "text", "group": "大纲模型"},
    {"key": "OUTLINE_MODEL", "label": "大纲 LLM 模型名称", "type": "text", "group": "大纲模型"},

    {"key": "PPT_API_TYPE", "label": "PPT LLM API 类型", "type": "text", "group": "PPT 模型", "description": "仅支持 openai 或 gemini"},
    {"key": "PPT_API_KEY", "label": "PPT LLM API Key", "type": "text", "group": "PPT 模型"},
    {"key": "PPT_API_URL", "label": "PPT LLM API 地址", "type": "text", "group": "PPT 模型"},
    {"key": "PPT_MODEL", "label": "PPT LLM 模型名称", "type": "text", "group": "PPT 模型"},
    {"key": "PPT_API_LIMIT", "label": "PPT LLM API 并发限制", "type": "number", "group": "PPT 模型"},


    {"key": "PIC_API_TYPE", "label": "图片理解 LLM API 类型", "type": "text", "group": "图片模型", "description": "仅支持 openai 或 gemini"},
    {"key": "PIC_API_KEY", "label": "图片理解 LLM API Key", "type": "text", "group": "图片模型"},
    {"key": "PIC_API_URL", "label": "图片理解 LLM API 地址", "type": "text", "group": "图片模型"},
    {"key": "PIC_MODEL", "label": "图片理解 LLM 模型名称", "type": "text", "group": "图片模型", "description": "必须支持图片理解!"},
    {"key": "PIC_NUM_LIMIT", "label": "图片数量限制", "type": "number", "group": "图片模型", "description": "搜索时返回的图片数量限制"},

    {"key": "SEARXNG_URL", "label": "Searxng 地址", "type": "text", "group": "搜索", "description": "公共服务器 https://searx.space/ "},

    # {"key": "TAVILY_KEY", "label": "Tavily Key", "type": "text", "group": "搜索"},
    # {"key": "TAVILY_MAX_NUM", "label": "Tavily 最大检索数", "type": "number", "group": "搜索"},

    {"key": "IMAGE_DOWNLOAD_MAX_WORKERS", "label": "图片下载并发数", "type": "number", "group": "杂项"},
    {
        "key": "APRYSE_LICENSE_KEY",
        "label": "Apryse License Key",
        "type": "text",
        "group": "杂项",
        "description": "Apryse SDK 所需的 License Key",
    },
]

CONFIG_ITEM_MAP = {item["key"]: item for item in CONFIG_ITEMS}


# === 配置类 ===
class LLMConfig:
    def __init__(self, name: str, api_key: str, api_url: str, api_type: str):
        self.name = name
        self.api_key = api_key
        self.api_url = api_url
        self.api_type = api_type
    
    def __repr__(self):
        return f"LLMConfig(name='{self.name}', api_key='{self.api_key[:10]}...', api_url='{self.api_url}', api_type='{self.api_type}')"

OUTLINE_LLM_CONFIG = LLMConfig("", "", "", "")
PPT_LLM_CONFIG = LLMConfig("", "", "", "")
PIC_LLM_CONFIG = LLMConfig("", "", "", "")

LLM_FIELD_SUFFIXES = ("API_TYPE", "API_KEY", "API_URL", "MODEL")
LLM_CONFIG_OBJECTS = {
    "OUTLINE": OUTLINE_LLM_CONFIG,
    "PPT": PPT_LLM_CONFIG,
    "PIC": PIC_LLM_CONFIG,
}
NUMERIC_DEFAULTS = {
    "PIC_NUM_LIMIT": 5,
    "TAVILY_MAX_NUM": 20,
    "IMAGE_DOWNLOAD_MAX_WORKERS": 15,
    "PPT_API_LIMIT": 4,
}
STRING_DEFAULTS = {
    "SEARXNG_URL": "",
    "TAVILY_KEY": "",
    "APRYSE_LICENSE_KEY": "",
}


def _load_config_value(key: str, default: Any) -> Any:
    value = _get_config_value(key, default)
    sanitized = _sanitize_value(key, value)
    return default if sanitized is None else sanitized


def _assign_global(key: str, value: Any) -> Any:
    globals()[key] = value
    return value


def _apply_llm_config(prefix: str, defaults: Dict[str, Any]) -> Dict[str, Any]:
    values: Dict[str, Any] = {}
    for field in LLM_FIELD_SUFFIXES:
        key = f"{prefix}_{field}"
        default_value = defaults.get(field, "")
        value = str(_load_config_value(key, default_value) or "")
        values[field] = _assign_global(key, value)

    config_obj = LLM_CONFIG_OBJECTS[prefix]
    config_obj.name = values["MODEL"]
    config_obj.api_key = values["API_KEY"]
    config_obj.api_url = values["API_URL"]
    config_obj.api_type = values["API_TYPE"]
    return values


def _apply_config() -> None:
    outline_defaults = {field: "" for field in LLM_FIELD_SUFFIXES}
    outline_values = _apply_llm_config("OUTLINE", outline_defaults)

    ppt_defaults = outline_values.copy()
    _apply_llm_config("PPT", ppt_defaults)

    pic_defaults = outline_values.copy()
    _apply_llm_config("PIC", pic_defaults)

    for key, default in NUMERIC_DEFAULTS.items():
        value = _load_config_value(key, default)
        _assign_global(key, int(value))

    for key, default in STRING_DEFAULTS.items():
        value = str(_load_config_value(key, default) or "")
        _assign_global(key, value)


def _sanitize_value(key: str, value: Any) -> Any:
    if key not in CONFIG_ITEM_MAP:
        return value
    item = CONFIG_ITEM_MAP[key]
    if value is None:
        return None
    if item["type"] == "number":
        if value == "":
            return None
        try:
            return int(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{item['label']} 需要为整数") from exc
    return str(value)


def get_effective_config() -> Dict[str, Any]:
    with _config_lock:
        config: Dict[str, Any] = {}
        for prefix in LLM_CONFIG_OBJECTS:
            for field in LLM_FIELD_SUFFIXES:
                key = f"{prefix}_{field}"
                config[key] = globals()[key]

        for key in NUMERIC_DEFAULTS:
            config[key] = globals()[key]

        for key in STRING_DEFAULTS:
            config[key] = globals()[key]
        return config


def get_runtime_overrides() -> Dict[str, Any]:
    with _config_lock:
        return dict(_runtime_overrides)


def update_runtime_overrides(data: Dict[str, Any]) -> None:
    sanitized: Dict[str, Any] = {}
    for key, value in data.items():
        if key not in CONFIG_ITEM_MAP:
            continue
        sanitized_value = _sanitize_value(key, value)
        if sanitized_value in (None, ""):
            continue
        sanitized[key] = sanitized_value

    with _config_lock:
        if not env_path.exists():
            env_path.touch()
        for key, value in sanitized.items():
            value_str = str(value)
            try:
                set_key(str(env_path), key, value_str)
            except Exception as exc:  # pylint: disable=broad-except
                logger.error("写入 .env 失败 (%s): %s", key, exc)
                continue
            os.environ[key] = value_str

    reload_runtime_overrides()


def reload_runtime_overrides() -> None:
    global _runtime_overrides
    if env_path.exists():
        load_dotenv(dotenv_path=env_path, override=True)
    _runtime_overrides = _load_runtime_overrides()
    _apply_config()


with _config_lock:
    _runtime_overrides = _load_runtime_overrides()
_apply_config()
