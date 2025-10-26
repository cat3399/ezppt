import sys
from pathlib import Path
import json

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import config.base_config as base_config
from config.logging_config import logger
from src.services.chat.chat import text_chat
from src.utils.help_utils import response2json, get_prompt
from src.models.outline_model import Outline

standard_outline_prompt = get_prompt("outline_prompt")
standard_outline_prompt_with_image = get_prompt("outline_prompt_with_image")


def create_outline(outline_config: Outline, llm_config=base_config.OUTLINE_LLM_CONFIG) -> Outline:
    logger.info("大纲生成中...")
    topic = outline_config.topic
    page_num = outline_config.page_num
    audience = outline_config.audience
    style = outline_config.style
    reference_content = outline_config.reference_content
    enable_img_search = outline_config.enable_img_search

    if enable_img_search:
        logger.info("启用图片搜索")
        outline_base_prompt = standard_outline_prompt_with_image
    else:
        logger.info("禁用图片搜索")
        outline_base_prompt = standard_outline_prompt
    outline_prompt = outline_base_prompt.format(
            topic=topic,
            page_num=page_num,
            reference_content=reference_content,
            audience=audience,
            style=style,
        )
    outline_llm_rsp = text_chat(prompt=outline_prompt, llm_config=llm_config)
    # print("大纲模型返回的原始内容：\n", outline_llm_rsp)
    outline_json = response2json(outline_llm_rsp)

    # with open(project_root.joinpath("response.json"),'w',encoding="utf-8") as fp:
    #     fp.write(json.dumps(outline_json,ensure_ascii=False,indent=4))

    # with open(project_root.joinpath("response.json"), "r", encoding="utf-8") as fp:
    #     outline_json = fp.read()
    #     outline_json = json.loads(outline_json)

    outline_config.outline_json = outline_json
    return outline_config
