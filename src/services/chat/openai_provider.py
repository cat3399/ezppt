import requests
import sys
from pathlib import Path

# 将项目根目录添加到 Python 路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from config.base_config import LLMConfig
import config.base_config as base_config

def chat_openai(images_base64: list[str] = [], prompt: str = "", llm_config: LLMConfig = base_config.OUTLINE_LLM_CONFIG) -> str:
    """
    调用OpenAI对话API，支持传入多个图片
    
    Args:
        api_key (str): OpenAI API密钥
        base64_images (list): base64编码的图片列表
        prompt (str): 用户的文本提示
        model (str): 使用的模型名称
    
    Returns:
        str: AI的回复内容
    """
    model = llm_config.name
    api_key = llm_config.api_key
    api_url = llm_config.api_url

    if images_base64:
        # 构建消息内容
        content = []
        
        # 添加文本内容
        content.append({
            "type": "text",
            "text": prompt
        })
        
        # 添加所有图片
        for image_base64 in images_base64:
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{image_base64}"
                }
            })
        
        # 构建请求载荷
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": content
                }
            ],
        }
    else:
        # 构建请求载荷
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
        }
    # print(payload)
    # 设置请求头
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    # 发送请求
    completions_url = f"{api_url}/chat/completions"
    response = requests.post(
        completions_url,
        headers=headers,
        json=payload,
        timeout=600
    )
    
    # 处理响应
    if response.status_code == 200:
        result = response.json()
        return result['choices'][0]['message']['content']
    else:
        raise Exception(f"API调用失败: {response.status_code} - {response.json()}")
