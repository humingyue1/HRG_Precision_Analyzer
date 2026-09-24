"""
基础数据类型定义
包含点、向量、平面、边界框等基础几何类型，以及误差、统计结果、验证结果等数据类
"""
from dataclasses import dataclass, field
from typing import Tuple, List, Optional, Dict, Any
import numpy as np

Point3D = Tuple[float, float, float]
Vector3D = Tuple[float, float, float]
Plane = Tuple[float, float, float, float]


@dataclass
class BoundingBox:
    """三维边界框"""
    min_x: float
    max_x: float
    min_y: float
    max_y: float
    min_z: float
    max_z: float
    
    def contains(self, point: Point3D) -> bool:
        """判断点是否在边界框内"""
        x, y, z = point
        return (self.min_x <= x <= self.max_x and
                self.min_y <= y <= self.max_y and
                self.min_z <= z <= self.max_z)
    
    def volume(self) -> float:
        """计算边界框体积"""
        return ((self.max_x - self.min_x) * 
                (self.max_y - self.min_y) * 
                (self.max_z - self.min_z))
    
    def to_dict(self) -> Dict[str, float]:
        """转换为字典格式"""
        return {
            'min_x': self.min_x, 'max_x': self.max_x,
            'min_y': self.min_y, 'max_y': self.max_y,
            'min_z': self.min_z, 'max_z': self.max_z
        }
    
    @classmethod
    def from_points(cls, points: np.ndarray) -> 'BoundingBox':
        """从点云数组创建边界框"""
        if len(points) == 0:
            return cls(0, 0, 0, 0, 0, 0)
        
        min_vals = np.min(points, axis=0)
        max_vals = np.max(points, axis=0)
        
        return cls(
            min_x=float(min_vals[0]), max_x=float(max_vals[0]),
            min_y=float(min_vals[1]), max_y=float(max_vals[1]),
            min_z=float(min_vals[2]), max_z=float(max_vals[2])
        )
    
    def expand(self, ratio: float) -> 'BoundingBox':
        """扩展边界框"""
        dx = (self.max_x - self.min_x) * ratio / 2
        dy = (self.max_y - self.min_y) * ratio / 2
        dz = (self.max_z - self.min_z) * ratio / 2
        
        return BoundingBox(
            min_x=self.min_x - dx, max_x=self.max_x + dx,
            min_y=self.min_y - dy, max_y=self.max_y + dy,
            min_z=self.min_z - dz, max_z=self.max_z + dz
        )


@dataclass
class ToothError:
    """齿误差数据"""
    radial_error: float
    circumferential_error: float
    composite_error: float
    tooth_id: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'tooth_id': self.tooth_id,
            'radial_error': self.radial_error,
            'circumferential_error': self.circumferential_error,
            'composite_error': self.composite_error
        }


@dataclass
class StatisticalResult:
    """统计结果数据"""
    mean: float
    std: float
    min: float
    max: float
    range: float
    median: Optional[float] = None
    count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'mean': self.mean,
            'std': self.std,
            'min': self.min,
            'max': self.max,
            'range': self.range,
            'median': self.median,
            'count': self.count
        }
    
    @classmethod
    def from_array(cls, data: np.ndarray) -> 'StatisticalResult':
        """从数组计算统计结果"""
        if len(data) == 0:
            return cls(0, 0, 0, 0, 0, None, 0)
        
        return cls(
            mean=float(np.mean(data)),
            std=float(np.std(data)),
            min=float(np.min(data)),
            max=float(np.max(data)),
            range=float(np.max(data) - np.min(data)),
            median=float(np.median(data)),
            count=len(data)
        )


@dataclass
class ValidationResult:
    """验证结果数据"""
    is_valid: bool
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)
    
    def add_warning(self, message: str):
        """添加警告信息"""
        self.warnings.append(message)
    
    def add_error(self, message: str):
        """添加错误信息"""
        self.errors.append(message)
        self.is_valid = False
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'is_valid': self.is_valid,
            'warnings': self.warnings,
            'errors': self.errors,
            'details': self.details
        }
    
    def merge(self, other: 'ValidationResult'):
        """合并另一个验证结果"""
        self.is_valid = self.is_valid and other.is_valid
        self.warnings.extend(other.warnings)
        self.errors.extend(other.errors)
        self.details.update(other.details)
