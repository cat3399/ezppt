import requests
import sys
from pathlib import Path
import traceback

project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

import config.base_config as base_config
from config.logging_config import logger
from src.utils.help_utils import retry_on_failure


@retry_on_failure(max_attempts=3, delay=1, description="调用Gemini格式LLM")
def chat_gemini(
    images_base64: list[str] = [],
    prompt: str = "",
    llm_config: base_config.LLMConfig = base_config.PIC_LLM_CONFIG,
) -> str:
    api_key = llm_config.api_key
    model = llm_config.name
    parts = []
    parts.append({"text": prompt})

    for image_base64 in images_base64:
        parts.append({"inline_data": {"mime_type": "image/jpeg", "data": image_base64}})
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
    completions_url = f"{llm_config.api_url}/v1beta/models/{model}:generateContent?key={api_key}"
    response = None
    try:
        response = requests.post(completions_url, headers=headers, json=request_body, timeout=600)
        response.raise_for_status()
        return response.json()["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        # logger.error(f"API调用失败: {response.status_code} - {response.text}")
        raise Exception(f"API调用失败: {response.status_code if response else 'None'} - 响应内容: {response.text if response else 'None'} - 错误信息{e}")

        # traceback.print_exc()
    # print("返回的内容为",response.content)
    # print("返回的内容为",response.json())


if __name__ == "__main__":
    # 测试代码
    test_prompt = "泥嚎鸭"
    logger.info(base_config.PIC_LLM_CONFIG)
    response = chat_gemini(prompt=test_prompt, llm_config=base_config.PIC_LLM_CONFIG)
    print(response)
