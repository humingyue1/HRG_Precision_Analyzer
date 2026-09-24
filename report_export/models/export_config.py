"""
导出配置模型
定义报告导出的配置参数
"""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class ExportConfig:
    """
    导出配置

    Attributes:
        default_output_dir: 默认输出目录
        filename_format: 文件命名格式
        pdf_page_size: PDF页面大小
        pdf_orientation: PDF页面方向
        word_compatibility: Word兼容版本
        max_file_size_mb: 最大文件大小(MB)
        chart_dpi: 图表DPI
        max_pages: 最大页数
        allowed_extensions: 允许的文件扩展名
        temp_dir: 临时目录
    """
    # 默认输出目录
    default_output_dir: str = "output/reports"

    # 文件命名格式
    filename_format: str = "HRG分析报告_{timestamp}_{format}"

    # PDF配置
    pdf_page_size: str = "A4"              # 页面大小
    pdf_orientation: str = "portrait"      # 页面方向

    # Word配置
    word_compatibility: str = "2010"       # Word兼容版本

    # 性能配置
    max_file_size_mb: int = 20             # 最大文件大小(MB)
    chart_dpi: int = 300                   # 图表DPI
    max_pages: int = 50                    # 最大页数

    # 安全配置
    allowed_extensions: Optional[List[str]] = None   # 允许的文件扩展名
    temp_dir: str = "temp"                 # 临时目录

    # 图表配置
    chart_width: float = 8.0               # 图表宽度（英寸）
    chart_height: float = 6.0              # 图表高度（英寸）
    chart_format: str = "png"              # 图表格式

    # 样式配置
    font_family: str = "SimHei"            # 字体
    font_size_title: int = 16              # 标题字号
    font_size_heading: int = 14            # 标题字号
    font_size_body: int = 12               # 正文字号

    def __post_init__(self):
        """初始化后处理"""
        if self.allowed_extensions is None:
            self.allowed_extensions = ['.pdf', '.docx']

    def get_pdf_config(self) -> dict:
        """获取PDF配置"""
        return {
            'page_size': self.pdf_page_size,
            'orientation': self.pdf_orientation,
            'max_file_size_mb': self.max_file_size_mb,
            'max_pages': self.max_pages,
            'chart_dpi': self.chart_dpi
        }

    def get_word_config(self) -> dict:
        """获取Word配置"""
        return {
            'compatibility': self.word_compatibility,
            'max_file_size_mb': self.max_file_size_mb,
            'max_pages': self.max_pages,
            'chart_dpi': self.chart_dpi
        }

    def get_chart_config(self) -> dict:
        """获取图表配置"""
        return {
            'width': self.chart_width,
            'height': self.chart_height,
            'dpi': self.chart_dpi,
            'format': self.chart_format
        }

    def get_style_config(self) -> dict:
        """获取样式配置"""
        return {
            'font_family': self.font_family,
            'font_size_title': self.font_size_title,
            'font_size_heading': self.font_size_heading,
            'font_size_body': self.font_size_body
        }

    @classmethod
    def default(cls) -> 'ExportConfig':
        """获取默认配置"""
        return cls()
