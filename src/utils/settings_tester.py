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


def _generate_test_images(pic_num=1):
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
    logger.info("测试大纲大模型是否可用")
    prompt = "hi"
    response = text_chat(prompt, llm_config=base_config.OUTLINE_LLM_CONFIG)
    print(response)


def ppt_llm_test():
    logger.info("测试PPT大模型是否可用")
    prompt = "hi"
    response = text_chat(prompt, llm_config=base_config.PPT_LLM_CONFIG)
    print(response)


def pic_llm_test():
    logger.info("测试图片理解大模型是否可用")
    images_base64 = _generate_test_images(pic_num=base_config.PIC_NUM_LIMIT)
    prompt = "hi"
    response = pic_understand(
        images_base64=images_base64,
        prompt=prompt,
        llm_config=base_config.PIC_LLM_CONFIG,
    )
    print(response)


def img_search_test():
    logger.info("测试图片搜索是否可用")
    response = image_search(query="哈基米")
    print(response)
