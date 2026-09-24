"""
齿状结构分析集成器
将齿状结构分析模块集成到v4.0 PrecisionAnalyzer系统
"""
import numpy as np
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
import time

try:
    from .tooth_identifier import ToothIdentifier
    from .tooth_flatness_analyzer import ToothFlatnessAnalyzer
    from .geometry_calculator import GeometryCalculator
except ImportError:
    from tooth_identifier import ToothIdentifier
    from tooth_flatness_analyzer import ToothFlatnessAnalyzer
    from geometry_calculator import GeometryCalculator


@dataclass
class ToothAnalysisResult:
    """齿状结构分析结果"""
    tooth_count: int = 0
    tooth_height_mean: float = 0.0
    tooth_height_std: float = 0.0
    tooth_width_mean: float = 0.0
    tooth_width_std: float = 0.0
    tooth_thickness_mean: float = 0.0
    tooth_thickness_std: float = 0.0
    flatness_mean: float = 0.0
    flatness_std: float = 0.0
    quality_score: float = 0.0
    quality_grade: str = '未评估'
    tooth_details: List[Dict[str, Any]] = field(default_factory=list)
    analysis_time: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'tooth_count': self.tooth_count,
            'tooth_height': {
                'mean': self.tooth_height_mean,
                'std': self.tooth_height_std
            },
            'tooth_width': {
                'mean': self.tooth_width_mean,
                'std': self.tooth_width_std
            },
            'tooth_thickness': {
                'mean': self.tooth_thickness_mean,
                'std': self.tooth_thickness_std
            },
            'flatness': {
                'mean': self.flatness_mean,
                'std': self.flatness_std
            },
            'quality_score': self.quality_score,
            'quality_grade': self.quality_grade,
            'tooth_details': self.tooth_details,
            'analysis_time': self.analysis_time
        }


class ToothStructureIntegrator:
    """齿状结构分析集成器"""
    
    def __init__(self, config: Optional[Dict] = None):
        """
        初始化集成器
        
        Args:
            config: 配置字典
        """
        self.config = config or {}
        tooth_config = self.config.get('tooth_analysis', {})
        
        self.enabled = tooth_config.get('enabled', True)
        self.theoretical_tooth_count = tooth_config.get('theoth_count', 48)
        self.center = tuple(tooth_config.get('center', [0, 0, 0]))
        
    def analyze(self, points: np.ndarray) -> Optional[ToothAnalysisResult]:
        """
        执行齿状结构分析
        
        Args:
            points: 点云数据
            
        Returns:
            齿状结构分析结果
        """
        if not self.enabled:
            return None
        
        start_time = time.time()
        
        try:
            center = self._calculate_center(points)
            
            identifier = ToothIdentifier(
                center=center,
                theoretical_tooth_count=self.theoretical_tooth_count
            )
            
            tooth_infos = identifier.identify_teeth(points)
            
            if len(tooth_infos) == 0:
                return ToothAnalysisResult(tooth_count=0)
            
            geometry_calculator = GeometryCalculator(center=center)
            flatness_analyzer = ToothFlatnessAnalyzer()
            
            heights = []
            widths = []
            thicknesses = []
            flatnesses = []
            tooth_details = []
            
            for tooth_info in tooth_infos:
                if tooth_info.boundary_points is None or len(tooth_info.boundary_points) < 10:
                    continue
                
                tooth_points = tooth_info.boundary_points
                
                geometry_result = geometry_calculator.calculate_all_geometry(
                    tooth_points, 
                    tooth_id=tooth_info.tooth_id
                )
                
                heights.append(geometry_result.tooth_height)
                widths.append(geometry_result.tooth_width)
                thicknesses.append(geometry_result.tooth_thickness)
                
                flatness_result = flatness_analyzer.calculate_flatness(tooth_points)
                flatnesses.append(flatness_result.flatness)
                
                tooth_details.append({
                    'tooth_id': tooth_info.tooth_id,
                    'height': geometry_result.tooth_height,
                    'width': geometry_result.tooth_width,
                    'thickness': geometry_result.tooth_thickness,
                    'flatness': flatness_result.flatness,
                    'center': tooth_info.center,
                    'angle': tooth_info.tooth_angle
                })
            
            if len(heights) == 0:
                return ToothAnalysisResult(tooth_count=len(tooth_infos))
            
            quality_score, quality_grade = self._evaluate_quality(
                heights, widths, thicknesses, flatnesses
            )
            
            analysis_time = time.time() - start_time
            
            return ToothAnalysisResult(
                tooth_count=len(tooth_infos),
                tooth_height_mean=float(np.mean(heights)),
                tooth_height_std=float(np.std(heights)),
                tooth_width_mean=float(np.mean(widths)),
                tooth_width_std=float(np.std(widths)),
                tooth_thickness_mean=float(np.mean(thicknesses)),
                tooth_thickness_std=float(np.std(thicknesses)),
                flatness_mean=float(np.mean(flatnesses)),
                flatness_std=float(np.std(flatnesses)),
                quality_score=quality_score,
                quality_grade=quality_grade,
                tooth_details=tooth_details,
                analysis_time=analysis_time
            )
            
        except Exception as e:
            print(f"齿状结构分析失败: {e}")
            import traceback
            traceback.print_exc()
            return ToothAnalysisResult(tooth_count=0)
    
    def _calculate_center(self, points: np.ndarray) -> tuple:
        """计算点云中心"""
        if self.center != (0, 0, 0):
            return self.center
        
        center_x = float(np.mean(points[:, 0]))
        center_y = float(np.mean(points[:, 1]))
        center_z = float(np.mean(points[:, 2]))
        
        return (center_x, center_y, center_z)
    
    def _evaluate_quality(
        self,
        heights: List[float],
        widths: List[float],
        thicknesses: List[float],
        flatnesses: List[float]
    ) -> tuple:
        """评估质量"""
        height_score = max(0, 100 - np.std(heights)/np.mean(heights) * 1000)
        width_score = max(0, 100 - np.std(widths)/np.mean(widths) * 1000)
        thickness_score = max(0, 100 - np.std(thicknesses)/np.mean(thicknesses) * 1000)
        flatness_score = max(0, 100 - np.mean(flatnesses) * 1000)
        
        overall_score = (
            0.35 * height_score + 
            0.25 * width_score + 
            0.15 * thickness_score + 
            0.25 * flatness_score
        )
        
        if overall_score >= 90:
            quality_grade = "优秀"
        elif overall_score >= 80:
            quality_grade = "良好"
        elif overall_score >= 70:
            quality_grade = "合格"
        else:
            quality_grade = "需改进"
        
        return overall_score, quality_grade
