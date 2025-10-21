import ast
import json
import os
from pathlib import Path
import re
import sys
from urllib.parse import urlparse
import uuid
from PIL import Image
from io import BytesIO
import base64
import requests
from datetime import datetime

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from config.logging_config import logger

MAX_IMAGE_LEN = 100 * 1024 * 1024


def get_prompt(prompt_name: str) -> str:
    """
    从指定路径加载提示词模板
    Args:
        prompt_name (str): 提示词文件名（不包含路径和扩展名）
    Returns:
        str: 加载的提示词内容
    """
    prompt_base_path = project_root.joinpath("src", "prompts")
    prompt_path = prompt_base_path.joinpath(f"{prompt_name}.md")
    with open(prompt_path, "r", encoding="utf8") as f:
        return f.read()


def img2base64(filename_result: str) -> str:
    """将图片文件转换为base64编码字符串

    该函数可以将各种格式的图片文件读取并转换为base64编码的字符串，主要用于图片在网络传输或存储时的格式转换。

    Args:
        filename_result (str): 图片文件的路径

    Returns:
        str: 返回图片文件对应的base64编码字符串

    Examples:
        >>> img_base64 = img2base64("path/to/image.jpg")
        >>> print(img_base64[:20])  # 打印前20个字符
        '/9j/4AAQSkZJRgABAQE...'

    Note:
        - 支持的图片格式包括PNG、JPEG、GIF等常见格式
        - 对于RGBA、LA、P模式的图片会自动转换为RGB模式
        - 最终输出格式为JPEG
    """
    try:
        img_tmp = Image.open(filename_result)
        if img_tmp.mode in ("RGBA", "LA", "P"):
            img_tmp = img_tmp.convert("RGB")
        buffered = BytesIO()
        img_tmp.save(buffered, format="JPEG")
        img_tmp_base64 = base64.b64encode(buffered.getvalue()).decode()
        return img_tmp_base64
    except Exception as e:
        print(f"无法将图片文件 {filename_result} 转换为base64编码: {e}")
        return ""

def download_image(url: str, filename: str, url_bak: str = ""):
    """
    下载图片并返回文件名（如果文件已存在则不下载）
    """
    # 检查文件是否已存在
    if os.path.exists(filename):
        logger.info(f"文件已存在，跳过下载: {filename}")
        return filename

    referer_url = urlparse(str(url)).netloc
    user_agents = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36 Edg/91.0.864.59"
    file_size = 0
    headers = {
        "User-Agent": user_agents,
        "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Referer": referer_url,
        "Connection": "keep-alive",
    }
    try:
        response = requests.get(url, headers=headers, timeout=15, stream=True)
        content_length = response.headers.get("Content-Length")
        if content_length:
            file_size = int(content_length)
        if file_size <= MAX_IMAGE_LEN:
            response.raise_for_status()
            with open(filename, "wb") as f:
                downloaded_size = 0
                for chunk in response.iter_content(chunk_size=819200):
                    if downloaded_size <= MAX_IMAGE_LEN:
                        downloaded_size += len(chunk)
                        f.write(chunk)
                    else:
                        logger.info(f" {url} 文件过大,已停止下载")
                        return None
            logger.info(f"从 {url} 下载成功: {filename}")
        else:
            logger.info(f" {url} 文件过大,不进行下载")
            return None
    except requests.exceptions.RequestException as e:
        logger.error(f"下载图片失败: {url} - 错误: {str(e)}")
        if url_bak:
            logger.info(f"尝试使用备用 URL: {url_bak}")
            return download_image(url_bak, filename)
        return None
    return filename


def response2list(llm_output: str) -> list:
    """
    从任意 LLM 输出中提取最长的 JSON 数组（支持嵌套）。
    返回该数组对应的 Python list；若未找到则返回空列表。
    """
    # 1. 用正则一次性抓出所有“成对中括号”里的内容
    #    非贪婪匹配内部，保证不交叉
    brackets = re.findall(r"\[(?:[^\[\]]|\[(?:[^\[\]]|\[[^\[\]]*\])*\])*\]", llm_output)
    if not brackets:
        return []
    # 2. 按长度排序，取最长
    longest = max(brackets, key=len)
    try:
        return json.loads(longest)
    except Exception:
        return []


def response2json(text: str) -> dict:
    """
    从字符串中提取第一个 { 和最后一个 } 之间的内容
    并尝试将其解析为 JSON 对象。
    这个版本会先清理掉JSON中常见的结尾逗号问题。
    参数:
        text (str): 要处理的输入字符串
    返回:
        dict: 成功时返回解析后的 JSON 对象, 失败时返回空字典
    """
    # 清理输入文本
    if text.rstrip(" ").startswith("<think>"):
        text = text.split("</think>", maxsplit=1)[-1]
    if "</think>" in text: # 兼容cerebras和sambanova,应该不会引发其他问题吧
        text = text.split("</think>", maxsplit=1)[-1]
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)

    pattern_json_obj = r"({.*})"  # 匹配 JSON 对象: 第一个 { 到最后一个 }
    match_obj = re.search(pattern_json_obj, text, re.DOTALL)

    if match_obj:
        string_to_parse = match_obj.group(1)

        # 使用正则表达式移除在 } 或 ] 前的多余逗号
        string_to_parse = re.sub(r",\s*([}\]])", r"\1", string_to_parse)
        try:
            parsed_json_content = json.loads(string_to_parse)
            return parsed_json_content
        except json.JSONDecodeError as e:
            logger.error(f"JSON 解析失败: {e}")
            # 为了调试，可以打印出清理后但仍然解析失败的字符串
            logger.info("清理后无法解析的字符串:", string_to_parse)
            return {}
    else:
        logger.warning("未找到匹配的 JSON 格式内容")
        return {}


def parse_outline(data) -> str:
    """
    解析演示文稿的JSON大纲，并返回包含章节、幻灯片及其内容的格式化字符串。
    Args:
        data (dict): 演示文稿大纲的JSON对象
    Returns:
        str: 格式化后的演示文稿大纲及内容字符串
    """
    output_lines = []

    # 格式化主标题
    main_title = data.get("main_title", "未知演示文稿标题")
    subtitle = data.get("subtitle", "")
    target_audience = data.get("target_audience", "未知目标受众")

    output_lines.append("=" * 60)
    output_lines.append(f"📊 演示文稿标题: {main_title}")
    if subtitle:
        output_lines.append(f"📝 副标题: {subtitle}")
    output_lines.append(f"👥 目标受众: {target_audience}")
    output_lines.append("=" * 60)

    # 检查是否存在 "chapters" 键
    chapters_list = data.get("chapters")
    if not chapters_list:
        output_lines.append(
            "警告：JSON数据中未找到任何章节 ('chapters' 键缺失或为空)。"
        )
        return "\n".join(output_lines)

    # 遍历主章节
    for main_chapter in chapters_list:
        chapter_id = main_chapter.get("chapter_id", "N/A")
        chapter_topic = main_chapter.get("chapter_topic", "未知章节主题")
        page_count_suggestion = main_chapter.get("page_count_suggestion", "N/A")
        output_lines.append(
            f"\n📂 第 {chapter_id} 章: {chapter_topic}  (建议页数: {page_count_suggestion})"
        )
        output_lines.append("-" * 40)

        # 遍历幻灯片
        slides_list = main_chapter.get("slides")
        if not slides_list:
            output_lines.append("  (本章无具体幻灯片主题或 'slides' 列表为空)")
            continue

        for slide in slides_list:
            slide_id = slide.get("slide_id", "N/A")
            slide_topic = slide.get("slide_topic", "未知幻灯片主题")
            slide_content = slide.get("slide_content", [])
            output_lines.append(f"  📄 幻灯片 {slide_id}: {slide_topic}")
            if slide_content:
                for line in slide_content:
                    output_lines.append(f"      • {line}")
            output_lines.append("")  # 在每张幻灯片后添加空行以提高可读性
    # for idx, visual_suggestion in enumerate(data["visual_suggestions"]):
    #     output_lines.append(f'图片 {idx+1} 搜索-{visual_suggestion["search_keywords"]}')
    #     output_lines.append(f'     描述-{visual_suggestion["image_description"]}')
    return "\n".join(output_lines)


def extract_html(html_content: str) -> str:
    """
    从可能包含 Markdown 代码块或裸 HTML 的字符串中提取**最后一段**纯 HTML 内容。
    规则优先级（均从字符串末尾向前匹配）：
        1. 最后一段 ```html ... ```
        2. 最后一段 ``` ... ```
        3. 最后一个 <!DOCTYPE html> 或 <html 标签到结尾（或下一个 ``` 之前）
        4. 兜底：原字符串 strip 后返回
    """
    if not isinstance(html_content, str):
        return ""
    # 1. 最后一段 ```html ... ```
    # 先整体从后往前找 ```html 开头的 fence
    html_fence_pattern = re.compile(r"```html(.*?)```", re.DOTALL)
    matches = list(html_fence_pattern.finditer(html_content))
    if matches:
        return matches[-1].group(1).strip()
    # 2. 最后一段 ``` ... ```
    generic_fence_pattern = re.compile(r"```(.*?)```", re.DOTALL)
    matches = list(generic_fence_pattern.finditer(html_content))
    if matches:
        return matches[-1].group(1).strip()
    # 3. 裸 HTML：最后一个 <!DOCTYPE html> 或 <html
    doctype_ridx = html_content.rfind("<!DOCTYPE html>")
    html_tag_ridx = html_content.rfind("<html")
    start_pos = 0
    if doctype_ridx != -1:
        start_pos = doctype_ridx
    elif html_tag_ridx != -1:
        start_pos = html_tag_ridx
    if start_pos is not None:
        # 截取到下一个 ``` 或到结尾
        fence_pos = html_content.find("```", start_pos)
        end_pos = fence_pos if fence_pos != -1 else len(html_content)
        return html_content[start_pos:end_pos].strip()
    # 4. 兜底
    return html_content.strip()


def time_name() -> str:
    # ts_str = datetime.now().strftime("%Y%m%d")  # 例如 20250907
    ts_str = datetime.now().strftime("%Y%m%d_%H%M%S")  # 例如 20250907_202903
    return ts_str
