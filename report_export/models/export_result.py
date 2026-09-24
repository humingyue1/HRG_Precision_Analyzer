"""
导出结果模型
封装报告导出的结果信息
"""

from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime


@dataclass
class ExportResult:
    """
    导出结果封装类

    Attributes:
        success: 是否成功
        file_paths: 生成的文件路径列表
        error_message: 错误信息（失败时）
        export_time: 导出耗时（秒）
        file_sizes: 文件大小列表（字节）
        timestamp: 结果时间戳
    """
    success: bool
    file_paths: List[str] = field(default_factory=list)
    error_message: Optional[str] = None
    export_time: float = 0.0
    file_sizes: List[int] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)

    def add_file(self, file_path: str, file_size: int):
        """
        添加生成的文件信息

        Args:
            file_path: 文件路径
            file_size: 文件大小（字节）
        """
        self.file_paths.append(file_path)
        self.file_sizes.append(file_size)

    def get_total_size(self) -> int:
        """
        获取所有文件的总大小

        Returns:
            总大小（字节）
        """
        return sum(self.file_sizes)

    def get_total_size_mb(self) -> float:
        """
        获取所有文件的总大小（MB）

        Returns:
            总大小（MB）
        """
        return self.get_total_size() / (1024 * 1024)

    def to_dict(self) -> dict:
        """
        转换为字典格式

        Returns:
            字典格式的结果数据
        """
        return {
            'success': self.success,
            'file_paths': self.file_paths,
            'error_message': self.error_message,
            'export_time': self.export_time,
            'file_sizes': self.file_sizes,
            'total_size_mb': self.get_total_size_mb(),
            'timestamp': self.timestamp.isoformat()
        }

    @classmethod
    def create_success(cls, file_paths: List[str], file_sizes: List[int],
                       export_time: float) -> 'ExportResult':
        """
        创建成功的导出结果

        Args:
            file_paths: 文件路径列表
            file_sizes: 文件大小列表
            export_time: 导出耗时

        Returns:
            ExportResult实例
        """
        result = cls(success=True, export_time=export_time)
        for path, size in zip(file_paths, file_sizes):
            result.add_file(path, size)
        return result

    @classmethod
    def create_failure(cls, error_message: str, export_time: float = 0.0) -> 'ExportResult':
        """
        创建失败的导出结果

        Args:
            error_message: 错误信息
            export_time: 导出耗时

        Returns:
            ExportResult实例
        """
        return cls(success=False, error_message=error_message, export_time=export_time)
