import sys
import argparse
from apryse_sdk import PDFNetPython
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from config.logging_config import logger
import config.base_config as base_config

def convert_pdf_to_pptx(pdf_path, pptx_path):
    """使用 Apryse SDK 将 PDF 转换为 PPTX"""
    logger.info(f"📄 正在将 PDF 转换为 PowerPoint 文件...")
    try:
        PDFNetPython.PDFNet.Initialize(base_config.APRYSE_LICENSE_KEY)
        PDFNetPython.Convert.ToPowerPoint(pdf_path, pptx_path)
        logger.info(f"✅ PowerPoint 文件已保存至 {pptx_path}")
        return True
    except Exception as e:
        logger.error(f"❌ 任务执行失败 ({pdf_path}), 错误: {e}")
        return False

def main():
    """命令行接口"""
    parser = argparse.ArgumentParser(description='将PDF文件转换为PowerPoint文件')
    parser.add_argument('pdf_path', help='输入PDF文件路径')
    parser.add_argument('pptx_path', help='输出PPTX文件路径')
    
    args = parser.parse_args()
    
    # 检查PDF文件是否存在
    pdf_file = Path(args.pdf_path)
    if not pdf_file.exists():
        logger.error(f"❌ PDF文件不存在: {args.pdf_path}")
        sys.exit(1)
    
    # 确保输出目录存在
    pptx_file = Path(args.pptx_path)
    pptx_file.parent.mkdir(parents=True, exist_ok=True)
    
    # 执行转换
    success = convert_pdf_to_pptx(str(pdf_file), str(pptx_file))
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
