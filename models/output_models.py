"""
输出数据模型定义
包含齿信息、平整度结果、几何结果、倾角结果、质量报告等输出数据类
"""
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
import numpy as np
from .base_types import BoundingBox, ToothError, StatisticalResult


@dataclass
class ToothInfo:
    """单齿信息"""
    tooth_id: int
    center: tuple
    bounding_box: BoundingBox
    boundary_points: Optional[np.ndarray] = None
    roi_points: Optional[np.ndarray] = None
    tooth_angle: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'tooth_id': self.tooth_id,
            'center': self.center,
            'bounding_box': self.bounding_box.to_dict(),
            'tooth_angle': self.tooth_angle,
            'num_boundary_points': len(self.boundary_points) if self.boundary_points is not None else 0,
            'num_roi_points': len(self.roi_points) if self.roi_points is not None else 0
        }


@dataclass
class FlatnessResults:
    """平整度分析结果"""
    flatness: float
    plane_equation: tuple
    deviations: Optional[np.ndarray] = None
    grade: str = '未评估'
    is_qualified: bool = True
    rmse: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'flatness': self.flatness,
            'plane_equation': self.plane_equation,
            'grade': self.grade,
            'is_qualified': self.is_qualified,
            'rmse': self.rmse,
            'num_points': len(self.deviations) if self.deviations is not None else 0
        }


@dataclass
class GeometryResults:
    """几何测量结果"""
    tooth_height: float
    tooth_width: float
    tooth_thickness: float
    tooth_spacing: Optional[float] = None
    tooth_error: Optional[ToothError] = None
    theoretical_height: Optional[float] = None
    theoretical_width: Optional[float] = None
    theoretical_thickness: Optional[float] = None
    
    @property
    def height_deviation(self) -> Optional[float]:
        """高度偏差"""
        if self.theoretical_height is not None:
            return self.tooth_height - self.theoretical_height
        return None
    
    @property
    def width_deviation(self) -> Optional[float]:
        """宽度偏差"""
        if self.theoretical_width is not None:
            return self.tooth_width - self.theoretical_width
        return None
    
    @property
    def thickness_deviation(self) -> Optional[float]:
        """厚度偏差"""
        if self.theoretical_thickness is not None:
            return self.tooth_thickness - self.theoretical_thickness
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        result = {
            'tooth_height': self.tooth_height,
            'tooth_width': self.tooth_width,
            'tooth_thickness': self.tooth_thickness,
            'tooth_spacing': self.tooth_spacing,
            'height_deviation': self.height_deviation,
            'width_deviation': self.width_deviation,
            'thickness_deviation': self.thickness_deviation
        }
        
        if self.tooth_error:
            result['tooth_error'] = self.tooth_error.to_dict()
        
        return result


@dataclass
class InclinationResults:
    """倾角分析结果"""
    side_inclination: float
    circumferential_inclination: float
    radial_inclination: float
    normal_vector: tuple
    theoretical_side_inclination: Optional[float] = None
    theoretical_circumferential_inclination: Optional[float] = None
    theoretical_radial_inclination: Optional[float] = None
    
    @property
    def side_inclination_error(self) -> Optional[float]:
        """侧倾角误差"""
        if self.theoretical_side_inclination is not None:
            return self.side_inclination - self.theoretical_side_inclination
        return None
    
    @property
    def circumferential_inclination_error(self) -> Optional[float]:
        """周向倾角误差"""
        if self.theoretical_circumferential_inclination is not None:
            return self.circumferential_inclination - self.theoretical_circumferential_inclination
        return None
    
    @property
    def radial_inclination_error(self) -> Optional[float]:
        """径向倾角误差"""
        if self.theoretical_radial_inclination is not None:
            return self.radial_inclination - self.theoretical_radial_inclination
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'side_inclination': self.side_inclination,
            'circumferential_inclination': self.circumferential_inclination,
            'radial_inclination': self.radial_inclination,
            'normal_vector': self.normal_vector,
            'side_inclination_error': self.side_inclination_error,
            'circumferential_inclination_error': self.circumferential_inclination_error,
            'radial_inclination_error': self.radial_inclination_error
        }


@dataclass
class ToothResult:
    """单齿完整分析结果"""
    tooth_id: int
    tooth_info: ToothInfo
    flatness: Optional[FlatnessResults] = None
    geometry: Optional[GeometryResults] = None
    inclination: Optional[InclinationResults] = None
    quality_score: float = 0.0
    quality_grade: str = '未评估'
    is_abnormal: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        result = {
            'tooth_id': self.tooth_id,
            'tooth_info': self.tooth_info.to_dict(),
            'quality_score': self.quality_score,
            'quality_grade': self.quality_grade,
            'is_abnormal': self.is_abnormal
        }
        
        if self.flatness:
            result['flatness'] = self.flatness.to_dict()
        
        if self.geometry:
            result['geometry'] = self.geometry.to_dict()
        
        if self.inclination:
            result['inclination'] = self.inclination.to_dict()
        
        return result


@dataclass
class AnalysisSummary:
    """整体分析结果统计"""
    tooth_count: int
    flatness_stats: StatisticalResult
    height_stats: StatisticalResult
    width_stats: StatisticalResult
    thickness_stats: StatisticalResult
    spacing_stats: Optional[StatisticalResult] = None
    side_inclination_stats: Optional[StatisticalResult] = None
    circumferential_inclination_stats: Optional[StatisticalResult] = None
    radial_inclination_stats: Optional[StatisticalResult] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        result = {
            'tooth_count': self.tooth_count,
            'flatness_stats': self.flatness_stats.to_dict(),
            'height_stats': self.height_stats.to_dict(),
            'width_stats': self.width_stats.to_dict(),
            'thickness_stats': self.thickness_stats.to_dict()
        }
        
        if self.spacing_stats:
            result['spacing_stats'] = self.spacing_stats.to_dict()
        
        if self.side_inclination_stats:
            result['side_inclination_stats'] = self.side_inclination_stats.to_dict()
        
        if self.circumferential_inclination_stats:
            result['circumferential_inclination_stats'] = self.circumferential_inclination_stats.to_dict()
        
        if self.radial_inclination_stats:
            result['radial_inclination_stats'] = self.radial_inclination_stats.to_dict()
        
        return result


@dataclass
class QualityReport:
    """质量评估报告"""
    overall_score: float
    quality_grade: str
    flatness_score: float
    geometry_score: float
    inclination_score: float
    abnormal_tooth_count: int
    abnormal_tooth_ids: List[int]
    summary: AnalysisSummary
    details: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'overall_score': self.overall_score,
            'quality_grade': self.quality_grade,
            'flatness_score': self.flatness_score,
            'geometry_score': self.geometry_score,
            'inclination_score': self.inclination_score,
            'abnormal_tooth_count': self.abnormal_tooth_count,
            'abnormal_tooth_ids': self.abnormal_tooth_ids,
            'summary': self.summary.to_dict(),
            'details': self.details
        }
    
    def to_json(self) -> str:
        """转换为JSON字符串"""
        import json
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)
