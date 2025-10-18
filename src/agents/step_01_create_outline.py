import sys
from pathlib import Path
import json
from pydantic import BaseModel, Field

# 将项目根目录添加到 Python 路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from config.base_config import OUTLINE_LLM_CONFIG
from config.logging_config import logger
from src.services.chat.chat import text_chat
from src.agents.get_pic import get_pic
from src.utils.help_utils import response2json, parse_outline, get_prompt
from src.models.outline_model import Outline

standard_outline_prompt = get_prompt("outline_prompt")

def create_outline(outline_config: Outline, llm_config=OUTLINE_LLM_CONFIG) -> Outline:
    topic = outline_config.topic
    page_num = outline_config.page_num
    audience = outline_config.audience
    style = outline_config.style
    reference_content = outline_config.reference_content

    # outline_prompt = standard_outline_prompt.format(topic=topic, page_num=page_num,reference_content=reference_content)
    # with open(project_root.joinpath("prompt_outline.md"),'w',encoding="utf-8") as fp:
    #     fp.write(outline_prompt)
    # outline_llm_rsp = text_chat(prompt=outline_prompt, llm_config=llm_config)
    # # print("大纲模型返回的原始内容：\n", outline_llm_rsp)
    # outline_json = response2json(outline_llm_rsp)

    # with open(project_root.joinpath("response.json"),'w',encoding="utf-8") as fp:
    #     fp.write(json.dumps(outline_json,ensure_ascii=False,indent=4))

    with open(project_root.joinpath("response.json"), "r", encoding="utf-8") as fp:
        outline_json = fp.read()
        outline_json = json.loads(outline_json)

    outline_config.outline_json = outline_json
    return outline_config
