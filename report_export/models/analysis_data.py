"""
分析数据模型
定义HRG分析结果的数据结构
"""

from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime


@dataclass
class AssemblyErrorData:
    """装配误差数据"""
    mean_distance: float      # 平均距离 (mm)
    std_distance: float       # 标准差 (mm)
    min_distance: float       # 最小距离 (mm)
    max_distance: float       # 最大距离 (mm)
    quality: str              # 质量评价
    comment: str              # 评价说明


@dataclass
class RoundnessData:
    """圆度误差数据"""
    max_error: float          # 最大圆度误差 (μm)
    mean_error: float         # 平均圆度误差 (μm)
    quality: str              # 质量评价
    comment: str              # 评价说明


@dataclass
class SphericityData:
    """球度误差数据"""
    center: List[float]       # 拟合球心 [x, y, z] (mm)
    radius: float             # 拟合球半径 (mm)
    error: float              # 球度误差 (μm)
    quality: str              # 质量评价
    comment: str              # 评价说明


@dataclass
class STLComparisonData:
    """STL对比数据"""
    align_strategy: str       # 对齐策略
    align_error: float        # 对齐误差 (mm)
    roundness_diff: float     # 圆度差异 (μm)
    sphericity_diff: float    # 球度差异 (μm)
    radius_diff: float        # 半径差异 (mm)
    quality: str              # 对比评价
    comment: str              # 评价说明


@dataclass
class AnalysisReportData:
    """完整分析报告数据"""
    # 基本信息
    timestamp: datetime                    # 报告生成时间
    asc_file: str                          # ASC文件名
    stl_file: Optional[str]                # STL文件名（可选）
    software_version: str                  # 软件版本

    # 原始数据统计
    total_points: int                      # 总点数
    x_range: List[float]                   # X坐标范围
    y_range: List[float]                   # Y坐标范围
    z_range: List[float]                   # Z坐标范围

    # 点云分割结果
    hrg_points: int                        # 谐振陀螺点数
    assembly_points: int                   # 装配结构点数
    bottom_plane_points: int               # 底部平面点数
    hrg_clean_points: int                  # 清理后谐振陀螺点数

    # 分析结果
    assembly_error: AssemblyErrorData      # 装配误差
    roundness: RoundnessData               # 圆度误差
    sphericity: SphericityData             # 球度误差
    stl_comparison: Optional[STLComparisonData]  # STL对比（可选）

    # 综合评价
    overall_score: float                   # 综合得分
    overall_quality: str                   # 综合评价
    overall_comment: str                   # 评价说明
    suggestions: List[str]                 # 改进建议列表

    def to_dict(self) -> dict:
        """转换为字典格式"""
        data = {
            'timestamp': self.timestamp.isoformat(),
            'asc_file': self.asc_file,
            'stl_file': self.stl_file,
            'software_version': self.software_version,
            'total_points': self.total_points,
            'x_range': self.x_range,
            'y_range': self.y_range,
            'z_range': self.z_range,
            'hrg_points': self.hrg_points,
            'assembly_points': self.assembly_points,
            'bottom_plane_points': self.bottom_plane_points,
            'hrg_clean_points': self.hrg_clean_points,
            'assembly_error': {
                'mean_distance': self.assembly_error.mean_distance,
                'std_distance': self.assembly_error.std_distance,
                'min_distance': self.assembly_error.min_distance,
                'max_distance': self.assembly_error.max_distance,
                'quality': self.assembly_error.quality,
                'comment': self.assembly_error.comment
            },
            'roundness': {
                'max_error': self.roundness.max_error,
                'mean_error': self.roundness.mean_error,
                'quality': self.roundness.quality,
                'comment': self.roundness.comment
            },
            'sphericity': {
                'center': self.sphericity.center,
                'radius': self.sphericity.radius,
                'error': self.sphericity.error,
                'quality': self.sphericity.quality,
                'comment': self.sphericity.comment
            },
            'overall_score': self.overall_score,
            'overall_quality': self.overall_quality,
            'overall_comment': self.overall_comment,
            'suggestions': self.suggestions
        }

        if self.stl_comparison:
            data['stl_comparison'] = {
                'align_strategy': self.stl_comparison.align_strategy,
                'align_error': self.stl_comparison.align_error,
                'roundness_diff': self.stl_comparison.roundness_diff,
                'sphericity_diff': self.stl_comparison.sphericity_diff,
                'radius_diff': self.stl_comparison.radius_diff,
                'quality': self.stl_comparison.quality,
                'comment': self.stl_comparison.comment
            }

        return data
