"""
输入数据模型定义
包含点云数据、分析配置等输入数据类
"""
from dataclasses import dataclass, field
from typing import Optional, Dict, Any
import numpy as np
from pathlib import Path
from .base_types import ValidationResult


@dataclass
class PointCloudData:
    """点云数据类"""
    points: np.ndarray
    file_path: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """初始化后验证"""
        if self.points is None or len(self.points) == 0:
            raise ValueError("点云数据不能为空")
        
        if self.points.shape[1] != 3:
            raise ValueError(f"点云数据形状错误，期望(n,3)，实际{self.points.shape}")
    
    @property
    def num_points(self) -> int:
        """点云数量"""
        return len(self.points)
    
    @property
    def bounds(self):
        """点云边界"""
        from .base_types import BoundingBox
        return BoundingBox.from_points(self.points)
    
    def validate(self, min_points: int = 1000, coverage_threshold: float = 0.85) -> ValidationResult:
        """
        验证点云数据
        
        Args:
            min_points: 最小点数要求
            coverage_threshold: 最小覆盖率要求
            
        Returns:
            验证结果
        """
        result = ValidationResult(is_valid=True)
        
        if self.num_points < min_points:
            result.add_error(f"点云数量不足：{self.num_points} < {min_points}")
        
        bounds = self.bounds
        volume = bounds.volume()
        
        if volume <= 0:
            result.add_error("点云体积为0，数据可能共面")
        
        coverage = self._calculate_coverage()
        if coverage < coverage_threshold:
            result.add_warning(f"点云覆盖率较低：{coverage:.2%} < {coverage_threshold:.2%}")
        
        result.details['num_points'] = self.num_points
        result.details['volume'] = volume
        result.details['coverage'] = coverage
        
        return result
    
    def _calculate_coverage(self) -> float:
        """计算点云覆盖率（简化实现）"""
        bounds = self.bounds
        expected_volume = bounds.volume()
        
        if expected_volume == 0:
            return 0.0
        
        actual_volume = self._estimate_actual_volume()
        
        return min(actual_volume / expected_volume, 1.0)
    
    def _estimate_actual_volume(self) -> float:
        """估算实际体积（基于凸包的简化实现）"""
        try:
            from scipy.spatial import ConvexHull
            hull = ConvexHull(self.points)
            return hull.volume
        except:
            bounds = self.bounds
            return bounds.volume() * 0.5
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式（不包含点云数组）"""
        return {
            'num_points': self.num_points,
            'file_path': self.file_path,
            'metadata': self.metadata,
            'bounds': self.bounds.to_dict()
        }
    
    @classmethod
    def from_file(cls, file_path: str) -> 'PointCloudData':
        """从文件加载点云"""
        path = Path(file_path)
        
        if path.suffix in ['.xyz', '.txt']:
            points = np.loadtxt(file_path)
        elif path.suffix == '.asc':
            points = np.loadtxt(file_path, skiprows=1)
        elif path.suffix in ['.npy', '.npz']:
            points = np.load(file_path)
        else:
            raise ValueError(f"不支持的文件格式：{path.suffix}")
        
        return cls(points=points, file_path=file_path)


@dataclass
class AnalysisConfig:
    """分析配置类"""
    tooth_count: Optional[int] = None
    center: tuple = (0.0, 0.0, 0.0)
    
    segmentation_method: str = 'region_growing'
    segmentation_radius: float = 0.5
    segmentation_threshold: float = 0.01
    
    flatness_method: str = 'least_squares'
    flatness_threshold: float = 0.01
    
    normal_radius: float = 0.3
    
    inclination_threshold: float = 1.0
    
    quality_weights: Dict[str, float] = field(default_factory=lambda: {
        'flatness': 0.4,
        'geometry': 0.3,
        'inclination': 0.3
    })
    
    output_dir: str = './output'
    save_intermediate: bool = False
    parallel_workers: int = 4
    
    def validate(self) -> ValidationResult:
        """验证配置参数"""
        result = ValidationResult(is_valid=True)
        
        if self.segmentation_radius <= 0:
            result.add_error("分割半径必须大于0")
        
        if self.flatness_threshold <= 0:
            result.add_error("平面度阈值必须大于0")
        
        if self.normal_radius <= 0:
            result.add_error("法向量估计半径必须大于0")
        
        if not np.isclose(sum(self.quality_weights.values()), 1.0, atol=0.01):
            result.add_warning(f"质量权重总和不为1: {sum(self.quality_weights.values()):.3f}")
        
        if self.parallel_workers < 1:
            result.add_error("并行工作进程数必须至少为1")
        
        return result
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'tooth_count': self.tooth_count,
            'center': self.center,
            'segmentation_method': self.segmentation_method,
            'segmentation_radius': self.segmentation_radius,
            'segmentation_threshold': self.segmentation_threshold,
            'flatness_method': self.flatness_method,
            'flatness_threshold': self.flatness_threshold,
            'normal_radius': self.normal_radius,
            'inclination_threshold': self.inclination_threshold,
            'quality_weights': self.quality_weights,
            'output_dir': self.output_dir,
            'save_intermediate': self.save_intermediate,
            'parallel_workers': self.parallel_workers
        }
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'AnalysisConfig':
        """从字典创建配置"""
        return cls(**config_dict)
