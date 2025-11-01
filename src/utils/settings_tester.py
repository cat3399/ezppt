import ast
import json
import os
from pathlib import Path
import random
import re
import sys
from urllib.parse import urlparse
import uuid
from PIL import ImageDraw, ImageFont, Image
from io import BytesIO
import base64
import requests
from datetime import datetime

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import config.base_config as base_config
from config.logging_config import logger
from src.services.chat.chat import pic_understand, text_chat
from src.services.search.image_search import image_search


def _generate_test_images(pic_num: int = 1):
    images_base64 = []
    for i in range(pic_num):
        width, height = 300, 200
        r, g, b = random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)
        img = Image.new("RGB", (width, height), (r, g, b))
        draw = ImageDraw.Draw(img)
        circle_color = (255 - r, 255 - g, 255 - b)
        draw.ellipse([(50, 50), (150, 150)], fill=circle_color)
        rect_color = (
            random.randint(0, 255),
            random.randint(0, 255),
            random.randint(0, 255),
        )
        draw.rectangle([(180, 50), (280, 150)], fill=rect_color)
        text = f"TestImg_{i+1}"
        try:
            font = ImageFont.load_default()
            draw.text((10, 10), text, fill=(0, 0, 0), font=font)
        except:
            draw.text((10, 10), text, fill=(0, 0, 0))

        buffer = BytesIO()
        img.save(buffer, format="PNG")
        img_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
        images_base64.append(img_base64)

    return images_base64


def outline_llm_test():
    try:
        logger.info("正在测试大纲大模型是否可用...")
        prompt = "hi"
        response = text_chat(prompt, llm_config=base_config.OUTLINE_LLM_CONFIG)
        logger.info(f"测试内容返回为: {response}")
        return response
    except Exception as e:
        logger.error(f"测试大纲大模型失败: {e}")
        raise Exception(e)


def ppt_llm_test():
    try:
        logger.info("正在测试PPT大模型是否可用...")
        prompt = "hi"
        response = text_chat(prompt, llm_config=base_config.PPT_LLM_CONFIG)
        logger.info(f"测试内容返回为: {response}")
        return response
    except Exception as e:
        logger.error(f"测试PPT大模型失败: {e}")
        raise Exception(e)


def pic_llm_test():
    try:
        logger.info("正在测试图片理解大模型是否可用...")
        images_base64 = _generate_test_images(pic_num=base_config.PIC_NUM_LIMIT)
        prompt = "hi"
        response = pic_understand(
            images_base64=images_base64,
            prompt=prompt,
            llm_config=base_config.PIC_LLM_CONFIG,
        )
        logger.info(f"测试内容返回为: {response}")
        return response
    except Exception as e:
        logger.error(f"测试图片理解大模型失败: {e}")
        raise Exception(e)


def img_search_test():
    try:
        logger.info("正在测试图片搜索是否可用...")
        response = image_search(query="哈基米")
        logger.info(f"测试内容返回为: {response}")
        return response
    except Exception as e:
        logger.error(f"测试图片搜索失败: {e}")
        raise Exception(e)


def _stringify_result(payload):
    if payload is None:
        return ""
    if isinstance(payload, (str, int, float, bool)):
        return str(payload)
    try:
        return json.dumps(payload, ensure_ascii=False)
    except (TypeError, ValueError):
        return str(payload)


TEST_DEFINITIONS = [
    {
        "key": "outline_llm",
        "label": "大纲 LLM 检测",
        "description": "向大纲模型发送测试请求，验证配置是否有效。",
        "runner": outline_llm_test,
    },
    {
        "key": "ppt_llm",
        "label": "PPT LLM 检测",
        "description": "向 PPT 模型发送测试请求，确保接口可用。",
        "runner": ppt_llm_test,
    },
    {
        "key": "pic_llm",
        "label": "图片理解模型检测",
        "description": "生成测试图片并验证图片理解模型是否正常响应。",
        "runner": pic_llm_test,
    },
    {
        "key": "img_search",
        "label": "图片搜索检测",
        "description": "调用图片搜索服务，确认可以返回结果。",
        "runner": img_search_test,
    },
]

TEST_MAP = {item["key"]: item for item in TEST_DEFINITIONS}


def list_tests():
    return [
        {
            "key": item["key"],
            "label": item["label"],
            "description": item.get("description", ""),
        }
        for item in TEST_DEFINITIONS
    ]


def run_test(test_key: str):
    if test_key not in TEST_MAP:
        raise KeyError(test_key)
    test_item = TEST_MAP[test_key]
    started = datetime.utcnow()
    try:
        result = test_item["runner"]()
    except Exception as exc:
        logger.exception("配置检测 %s 失败", test_key)
        raise
    duration = (datetime.utcnow() - started).total_seconds()
    return {
        "key": test_key,
        "label": test_item["label"],
        "description": test_item.get("description", ""),
        "success": True,
        "result": _stringify_result(result),
        "duration": duration,
        "timestamp": datetime.utcnow().isoformat(),
    }
