"""
导出请求模型
封装报告导出的请求参数
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from datetime import datetime


@dataclass
class ExportRequest:
    """
    导出请求封装类

    Attributes:
        format_type: 导出格式，'pdf', 'word' 或 'both'
        output_dir: 输出目录路径
        filename_prefix: 文件名前缀
        analysis_data: 分析结果数据字典
        include_charts: 是否包含图表
        language: 语言选择，'zh'或'en'
        template_name: 模板名称（可选）
        timestamp: 请求时间戳
    """
    format_type: str
    output_dir: str
    analysis_data: Dict[str, Any]
    filename_prefix: str = "HRG分析报告"
    include_charts: bool = True
    language: str = "zh"
    template_name: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)

    def validate(self) -> tuple[bool, str]:
        """
        验证导出请求参数

        Returns:
            (is_valid, error_message): 验证结果和错误信息
        """
        # 验证格式类型
        if self.format_type not in ['pdf', 'word', 'both']:
            return False, f"不支持的格式类型: {self.format_type}，必须是 'pdf', 'word' 或 'both'"

        # 验证输出目录
        if not self.output_dir:
            return False, "输出目录不能为空"

        # 验证文件名前缀
        if not self.filename_prefix:
            return False, "文件名前缀不能为空"

        # 验证文件名前缀长度
        if len(self.filename_prefix) > 50:
            return False, "文件名前缀长度不能超过50字符"

        # 验证语言
        if self.language not in ['zh', 'en']:
            return False, f"不支持的语言: {self.language}，必须是 'zh' 或 'en'"

        # 验证分析数据
        if not self.analysis_data:
            return False, "分析数据不能为空"

        return True, ""

    def get_file_extensions(self) -> list:
        """
        获取需要生成的文件扩展名列表

        Returns:
            文件扩展名列表，如 ['.pdf'] 或 ['.pdf', '.docx']
        """
        if self.format_type == 'pdf':
            return ['.pdf']
        elif self.format_type == 'word':
            return ['.docx']
        else:  # both
            return ['.pdf', '.docx']

    def get_timestamp_str(self) -> str:
        """
        获取时间戳字符串（用于文件命名）

        Returns:
            格式化的时间戳字符串，如 '20240403_123045'
        """
        return self.timestamp.strftime('%Y%m%d_%H%M%S')

    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典格式

        Returns:
            字典格式的请求数据
        """
        return {
            'format_type': self.format_type,
            'output_dir': self.output_dir,
            'filename_prefix': self.filename_prefix,
            'include_charts': self.include_charts,
            'language': self.language,
            'template_name': self.template_name,
            'timestamp': self.timestamp.isoformat()
        }
