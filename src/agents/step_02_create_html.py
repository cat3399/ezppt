import sys
from pathlib import Path

# 将项目根目录添加到 Python 路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.agents.step_01_create_outline import create_outline
from src.services.chat.chat import text_chat
from src.utils.help_utils import response2json, parse_outline, get_prompt, extract_html
from config.base_config import OUTLINE_LLM_CONFIG, PPT_LLM_CONFIG
from config.logging_config import logger
from src.models.outline_model import Outline

create_html_ppt = get_prompt("create_html_ppt")
create_html_ppt_with_image = get_prompt("create_html_ppt_with_image")


def _format_slides_as_reference_html(slides: list) -> str:
    """
    一个辅助函数，用于将幻灯片列表格式化为带有标题和分隔符的参考字符串。

    Args:
        slides (list): 包含幻灯片字典的列表。
    Returns:
        str: 格式化后的HTML内容字符串，如果无有效内容则返回空字符串。
    """
    content_list = []
    for slide in slides:
        if slide.get("html_content"):
            content_list.append(
                f"第 {slide['slide_id']}节\n" f"{'-'*5}\n" f"{slide['html_content']}"
            )

    if not content_list:
        return ""

    header = f"\n\n{'=' * 5}\n"
    body = "\n\n".join(content_list)

    return header + body


def create_html(
    outline_config: Outline, target_id: str, llm_config=OUTLINE_LLM_CONFIG
) -> str:
    """根据大纲和目标ID生成HTML内容"""
    chapters = outline_config.outline_json.get("chapters", [])

    # 初始化变量
    style_reference_html = ""
    layout_reference_html = ""

    # 生成 style_reference_html (风格参考)
    if chapters:
        first_chapter = chapters[0]
        style_reference_html = _format_slides_as_reference_html(
            slides=first_chapter.get("slides", []),
        )

    # 生成 layout_reference_html (布局参考)
    if chapters:
        target_chapter_id = target_id.split(".", maxsplit=1)[0]
        for chapter in chapters:
            if chapter.get("chapter_id") == target_chapter_id:
                layout_reference_html = _format_slides_as_reference_html(
                    slides=chapter.get("slides", []),
                )
                break

    if not style_reference_html:
        style_reference_html = "这是第一个界面,没有任何参考文件"

    if not layout_reference_html:
        layout_reference_html = "这是第一个界面,没有任何参考文件"

    # for reference_html,reference_html_content in reference_html_dict.items():
    #     print("有参考的编号",reference_html)
    #     print("有参考的内容",reference_html_content[:100])

    images = outline_config.images.get(target_id, {})
    # logger.info(f"images: {images}")
    imgs_info = ""
    if images == {}:
        html_prompt = create_html_ppt.format(
            outline=parse_outline(outline_config.outline_json),
            target_id=target_id,
            style_reference_html=style_reference_html,
            layout_reference_html=layout_reference_html,
        )
    else:
        for k, value in images.items():
            imgs_info += f"""\n
            图片路径: {k}  图片来源的标题: {value.title}, 图片来源的简介: {value.content}, 图片链接: {value.img_url[:200]} 分辨率: {value.height}x{value.width}, 描述: {value.description}
            """
            # logger.info(f"图片提示词:{imgs_info}")
        html_prompt = create_html_ppt_with_image.format(
            outline=parse_outline(outline_config.outline_json),
            target_id=target_id,
            imgs_info=imgs_info,
            style_reference_html=style_reference_html,
            layout_reference_html=layout_reference_html,
        )
    # html_prompt = create_html_ppt.format(outline=parse_outline(outline_config.outline_json), target_id=target_id)
    if target_id == "2.2":
        # print(html_prompt)
        with open("tmp.prompt", "w", encoding="utf-8") as fp:
            fp.write(html_prompt)

    html_llm_rsp = text_chat(prompt=html_prompt, llm_config=llm_config)
    html_content = extract_html(html_llm_rsp)
    return html_content


if __name__ == "__main__":
    outline_config = Outline(
        topic="tpu的发展历史",
        audience="大众",
        style="简洁明了",
        page_num=20,
        project_id="test",
    )
    outline_config = create_outline(
        outline_config=outline_config, llm_config=PPT_LLM_CONFIG
    )
    outline_json = outline_config.outline_json
    # Outline_str = """ {"main_title": "TPU的发展历史：从概念到现实的智能计算加速之路", "subtitle": "探索谷歌TPU如何改变AI硬件的未来", "chapters": [{"chapter_id": "1", "chapter_topic": "序幕", "page_count_suggestion": 2, "slides": [{"slide_id": "1.1", "slide_topic": "欢迎页", "slide_content": ["主标题：TPU的发展历史：从概念到现实的智能计算加速之路", "副标题：探索谷歌TPU如何改变AI硬件的未来", "分享人：XXX", "日期：2025年4月5日"]}, {"slide_id": "1.2", "slide_topic": "议程概览", "slide_content": ["本次演示将带你了解TPU（张量处理单元）的诞生背景与发展历程。", "我们将回顾AI计算的发展趋势，理解为什么TPU如此重要。", "紧接着，探索TPU的几代演进及其技术突破。", "最后，展望TPU在未来的应用前景与影响。"]}]}, {"chapter_id": "2", "chapter_topic": "AI计算的背景与挑战", "page_count_suggestion": 3, "slides": [{"slide_id": "2.1", "slide_topic": "什么是AI计算？", "slide_content": ["AI计算是指通过计算机模拟人类智能，如图像识别、语音识别、语言翻译等任务。", "这些任务需要处理大量数据并执行复杂的数学计算。", "传统CPU在执行这类任务时效率较低，而GPU则成为主流的加速工具。", "但随着AI应用的复杂化，对计算能力的需求已超越现有硬件能力。"]}, {"slide_id": "2.2", "slide_topic": "为什么需要专用AI芯片？", "slide_content": ["CPU为通用计算设计，处理AI任务时不够高效。", "GPU虽然适用于大规模并行计算，但能耗高、成本高。", "专用AI芯片可以针对特定任务进行优化，提升性能并降低能耗。", "谷歌在2016年推出了TPU，专门用于加速深度学习模型的训练和推理。"]}, {"slide_id": "2.3", "slide_topic": "TPU诞生前的AI芯片格局", "slide_content": ["在TPU之前，AI计算主要依赖CPU和GPU。", "英伟达的GPU在深度学习领域占据主导地位。", "初创公司和大型科技公司开始探索定制芯片的可能性。", "谷歌TPU的出现，标志着AI芯片从通用到专用的转变。"]}]}, {"chapter_id": "3", "chapter_topic": "第一代TPU（2016）", "page_count_suggestion": 3, "slides": [{"slide_id": "3.1", "slide_topic": "TPU的诞生", "slide_content": ["第一代TPU在2016年谷歌I/O大会上正式发布。", "它专为加速谷歌的深度学习框架TensorFlow而设计。", "TPU最初用于推理任务，处理神经网络预测阶段的计算。"]}, {"slide_id": "3.2", "slide_topic": "性能对比与实际应用", "slide_content": ["第一代TPU比CPU和GPU更快、更节能。", "它的性能大约是同期GPU的30到80倍。", "主要用于谷歌的搜索建议、街景识别和翻译服务。"]}, {"slide_id": "3.3", "slide_topic": "设计特点", "slide_content": ["使用28纳米工艺制造。", "集成于服务器级主板，非通用插槽设计。", "支持低精度计算（8位整数），特别适合推理场景。"]}]}, {"chapter_id": "4", "chapter_topic": "第二代TPU（2017）", "page_count_suggestion": 3, "slides": [{"slide_id": "4.1", "slide_topic": "TPU v2：支持训练的里程碑", "slide_content": ["第二代TPU在2017年谷歌I/O上发布。", "相比第一代，TPU v2不仅支持推理，还支持训练任务。", "首次以TPU Pods集群方式对外展示，提升系统整体性能。"]}, {"slide_id": "4.2", "slide_topic": "架构升级和性能提升", "slide_content": ["采用16纳米工艺，提升能效。", "每块TPU v2芯片包含两个核心：矩阵乘法单元和标量处理单元。", "大幅提高训练效率，适合ResNet、Transformer等复杂模型。"]}, {"slide_id": "4.3", "slide_topic": "开放平台：Cloud TPU", "slide_content": ["谷歌开始在云平台上提供TPU v2服务。", "使研究者和开发者无需购买硬件即可使用TPU。", "推动了AI社区对专用硬件的兴趣和发展。"]}]}, {"chapter_id": "5", "chapter_topic": "第三代TPU（2018）", "page_count_suggestion": 3, "slides": [{"slide_id": "5.1", "slide_topic": "TPU v3的突破", "slide_content": ["2018年谷歌发布了TPU v3，进一步优化了训练性能。", "支持更大的模型和更高精度的计算。", "开始使用液冷技术，以应对高热负荷。"]}, {"slide_id": "5.2", "slide_topic": "更强的计算能力与能效", "slide_content": ["在ImageNet训练中表现出惊人的速度提升。", "相比前代，能耗效率提高一倍。", "是BERT和AlphaGo Zero等模型背后的重要推手。"]}, {"slide_id": "5.3", "slide_topic": "AI超算集群 TPU Pod v3", "slide_content": ["构建高达1024块TPU的Pod集群。", "可提供数百PetaFLOPS的计算能力。", "成为深度学习研究中的一股强大力量。"]}]}, {"chapter_id": "6", "chapter_topic": "第四代与后续演进", "page_count_suggestion": 3, "slides": [{"slide_id": "6.1", "slide_topic": "TPU v4：迈向更高效能", "slide_content": ["2021年谷歌推出TPU v4。", "新增对稀疏计算的支持，使模型更加轻量化。", "TPU Pod v4包含超过4000个芯片，性能再度飞跃。"]}, {"slide_id": "6.2", "slide_topic": "支持更复杂的AI任务", "slide_content": ["TPU v4开始支持自然语言理解、图像生成等任务。", "成为PaLM、Imagen、LaMDA等先进模型的关键硬件。", "通过与软件生态深度整合，进一步简化AI模型部署。"]}, {"slide_id": "6.3", "slide_topic": "Edge TPU与普及化尝试", "slide_content": ["谷歌推出Edge TPU，面向移动和边缘设备。", "其体积小、功耗低，适合嵌入式AI应用。", "结合Cloud IoT平台，为企业提供端到端AI解决方案。"]}]}, {"chapter_id": "7", "chapter_topic": "总结与展望", "page_count_suggestion": 3, "slides": [{"slide_id": "7.1", "slide_topic": "TPU发展关键回顾", "slide_content": ["TPU从专为推理设计的第一代，逐步演进为支持训练的AI计算利器。", "每一代都显著提升了性能、精度和能效。", "TPU Pods的集群设计为大型AI模型扫清了硬件障碍。"]}, {"slide_id": "7.2", "slide_topic": "对未来AI硬件的影响", "slide_content": ["TPU的成功激励了微软、亚马逊等科技巨头开发自研AI芯片。", "专用AI芯片正在成为主流，降低运营成本并提升模型效率。", "边缘计算和云端AI生态共同推动专用芯片多场景落地。"]}, {"slide_id": "7.3", "slide_topic": "结语", "slide_content": ["TPU不仅是硬件的技术进步，更代表了AI从软件驱动向硬件协同优化的转变。", "它改变了AI研究和产品部署的方式，加速了行业创新。", "未来，我们期待更多定制化、高效能的AI芯片涌现。"]}]}, {"chapter_id": "8", "chapter_topic": "互动与致谢", "page_count_suggestion": 2, "slides": [{"slide_id": "8.1", "slide_topic": "核心要点回顾", "slide_content": ["AI计算发展推动了硬件需求的转变，TPU应运而生。", "从TPU v1到v4，持续推动深度学习模型的计算边界。", "TPU Pods和Edge TPU为不同场景提供定制解决方案。", "专用AI芯片成为未来AI基础设施的关键组成部分。"]}, {"slide_id": "8.2", "slide_topic": "问答与致谢", "slide_content": ["Q&A", "感谢大家的聆听，欢迎提出关于TPU或AI硬件发展的问题！", "联系方式：xxx@example.com"]}]}]} """
    # outline_json = json.loads(Outline_str)
    print(outline_json["chapters"][1])
    print(outline_json["chapters"][2])
    print(outline_config)
