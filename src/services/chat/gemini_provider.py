import requests
import sys
from pathlib import Path
import traceback
# 将项目根目录添加到 Python 路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

import config.base_config as base_config
from config.logging_config import logger

def chat_gemini(images_base64: list[str] = [], prompt: str = "", llm_config:base_config.LLMConfig = base_config.PIC_LLM_CONFIG) -> str:
    api_key = llm_config.api_key
    model = llm_config.name
    parts = []
    parts.append({"text": prompt })

    for image_base64 in images_base64:
        parts.append(
            {"inline_data": {"mime_type": "image/jpeg", "data": image_base64}}
        )
    # 构建请求体
    request_body = {
        "contents": [{"parts": parts, "role": "user"}],
        # "generationConfig": {
        #     "thinkingConfig": {"thinkingBudget": 0},
        # },
        "safetySettings": [
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "OFF"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "OFF"},
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "OFF"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "OFF"},
            {"category": "HARM_CATEGORY_CIVIC_INTEGRITY", "threshold": "BLOCK_NONE"},
        ],
    }

    headers = {"Content-Type": "application/json"}
    url = f"{llm_config.api_url}/v1beta/models/{model}:generateContent?key={api_key}"
    try:
        response = requests.post(url, headers=headers, json=request_body, timeout=600)
    except Exception as e:
        logger.error(f"请求失败: {e}")
        traceback.print_exc()
    # print("返回的内容为",response.content)
    # print("返回的内容为",response.json())
    return response.json()["candidates"][0]["content"]["parts"][0]["text"]

if __name__ == "__main__":
    # 测试代码
    test_prompt = "泥嚎鸭"
    logger.info(base_config.PIC_LLM_CONFIG)
    response = chat_gemini(prompt=test_prompt, llm_config=base_config.PIC_LLM_CONFIG)
    print(response)
