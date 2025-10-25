import sys
from pathlib import Path
import json

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from config.base_config import OUTLINE_LLM_CONFIG
from config.logging_config import logger
from src.services.chat.chat import text_chat
from src.utils.help_utils import response2json, get_prompt, parse_outline
from src.models.outline_model import Outline

plan_layout_prompt_template = get_prompt("plan_layout")


def plan_layout(outline_config: Outline):
    logger.info("制定布局规划...")
    outline_md = parse_outline(outline_config.outline_json)
    plan_layout_prompt = plan_layout_prompt_template.format(outline=outline_md)
    response = text_chat(plan_layout_prompt)
    return response2json(response)
