import sys
from pathlib import Path

# 将项目根目录添加到 Python 路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.services.chat.gemini_provider import chat_gemini
from src.services.chat.openai_provider import chat_openai
from config.base_config import LLMConfig, OUTLINE_LLM_CONFIG, PIC_LLM_CONFIG

def pic_understand(images_base64: list[str], prompt: str, llm_config:LLMConfig = PIC_LLM_CONFIG) -> str:
    """
    调用图片理解API，支持传入多个图片
    
    Args:
        images_base64 (list[str]): base64编码的图片列表
        prompt (str): 用户的文本提示
        llm_config (LLMConfig): LLM配置对象，默认使用PIC_LLM_CONFIG
    
    Returns:
        str: AI的回复内容
    """
    
    if llm_config.api_type.lower() == "openai":
        return chat_openai(images_base64=images_base64, prompt=prompt, llm_config=llm_config)
    else:
        return chat_gemini(images_base64=images_base64, prompt=prompt, llm_config=llm_config)
    
def text_chat(prompt: str, llm_config:LLMConfig = OUTLINE_LLM_CONFIG) -> str:
    """
    调用文本聊天API
    
    Args:
        prompt (str): 用户的文本提示
        llm_config (LLMConfig): LLM配置对象，默认使用OUTLINE_LLM_CONFIG
    
    Returns:
        str: AI的回复内容
    """
    
    if llm_config.api_type.lower() == "openai":
        return chat_openai(prompt=prompt, llm_config=llm_config)
    else:
        return chat_gemini(prompt=prompt, llm_config=llm_config)
