"""
导出控制器
报告导出的统一入口和流程控制
"""

import os
import time
from typing import Tuple, Optional

from models.export_request import ExportRequest
from models.export_result import ExportResult
from models.export_config import ExportConfig
from utils.file_utils import ensure_dir, get_unique_filename, safe_write_file, get_file_size
from utils.validation_utils import validate_analysis_data, check_dependencies


class ExportController:
    """
    报告导出控制器
    
    提供统一的导出入口，协调PDF和Word生成器
    """

    def __init__(self, config: Optional[ExportConfig] = None):
        """
        初始化导出控制器

        Args:
            config: 导出配置，如果为None则使用默认配置
        """
        self.config = config if config else ExportConfig()

        # 检查依赖
        self.deps_ok, self.missing_deps = check_dependencies()

        if not self.deps_ok:
            print(f"警告: 缺少依赖: {', '.join(self.missing_deps)}")
            print("请运行: pip install " + " ".join(self.missing_deps))

    def export_report(self, request: ExportRequest) -> ExportResult:
        """
        执行报告导出

        Args:
            request: 导出请求对象

        Returns:
            ExportResult: 导出结果对象
        """
        start_time = time.time()

        try:
            # 1. 检查依赖
            if not self.deps_ok:
                return ExportResult.create_failure(
                    f"缺少依赖: {', '.join(self.missing_deps)}",
                    time.time() - start_time
                )

            # 2. 验证请求
            is_valid, error = request.validate()
            if not is_valid:
                return ExportResult.create_failure(error, time.time() - start_time)

            # 3. 验证分析数据
            is_valid, error = validate_analysis_data(request.analysis_data)
            if not is_valid:
                return ExportResult.create_failure(error, time.time() - start_time)

            # 4. 确保输出目录存在
            if not ensure_dir(request.output_dir):
                return ExportResult.create_failure(
                    "无法创建输出目录",
                    time.time() - start_time
                )

            # 5. 生成报告
            file_paths = []
            file_sizes = []

            for ext in request.get_file_extensions():
                # 生成文件名
                timestamp_str = request.get_timestamp_str()
                filename = f"{request.filename_prefix}_{timestamp_str}"
                filepath = get_unique_filename(request.output_dir, filename, ext)

                # 根据扩展名选择生成器
                success = False
                if ext == '.pdf':
                    success = self._generate_pdf(request.analysis_data, filepath)
                elif ext == '.docx':
                    success = self._generate_word(request.analysis_data, filepath)

                if success:
                    file_paths.append(filepath)
                    file_sizes.append(get_file_size(filepath))
                else:
                    # 如果部分失败，返回部分成功的结果
                    if file_paths:
                        export_time = time.time() - start_time
                        result = ExportResult.create_success(
                            file_paths, file_sizes, export_time
                        )
                        result.error_message = f"部分文件生成失败: {ext}"
                        return result
                    else:
                        return ExportResult.create_failure(
                            f"报告生成失败: {ext}",
                            time.time() - start_time
                        )

            # 6. 返回成功结果
            export_time = time.time() - start_time
            return ExportResult.create_success(file_paths, file_sizes, export_time)

        except Exception as e:
            export_time = time.time() - start_time
            return ExportResult.create_failure(f"导出过程出错: {str(e)}", export_time)

    def _generate_pdf(self, data: dict, filepath: str) -> bool:
        """
        生成PDF报告

        Args:
            data: 分析数据
            filepath: 文件路径

        Returns:
            bool: 是否成功
        """
        try:
            from generators.pdf_generator import PDFReportGenerator

            generator = PDFReportGenerator()
            return generator.generate(data, filepath)

        except Exception as e:
            print(f"PDF生成失败: {e}")
            return False

    def _generate_word(self, data: dict, filepath: str) -> bool:
        """
        生成Word报告

        Args:
            data: 分析数据
            filepath: 文件路径

        Returns:
            bool: 是否成功
        """
        try:
            from generators.word_generator import WordReportGenerator

            generator = WordReportGenerator()
            return generator.generate(data, filepath)

        except Exception as e:
            print(f"Word生成失败: {e}")
            return False

    def get_supported_formats(self) -> list:
        """
        获取支持的导出格式

        Returns:
            list: 支持的格式列表
        """
        return ['pdf', 'word', 'both']

    def validate_analysis_data(self, data: dict) -> Tuple[bool, str]:
        """
        验证分析数据

        Args:
            data: 分析数据

        Returns:
            (is_valid, error_message): 验证结果
        """
        return validate_analysis_data(data)
