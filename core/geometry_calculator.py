"""
几何计算器
计算齿高、齿宽、齿厚、齿间距等几何指标
"""
import numpy as np
from typing import Tuple, Optional
import sys
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from models.base_types import ToothError, StatisticalResult
from models.output_models import GeometryResults
from utils.coordinate_transform import cartesian_to_polar
from utils.statistical_analysis import calculate_statistics


class GeometryCalculator:
    """几何计算器类"""
    
    def __init__(
        self,
        center: Tuple[float, float, float] = (0, 0, 0),
        theoretical_params: Optional[dict] = None
    ):
        """
        初始化几何计算器
        
        Args:
            center: 振子中心坐标
            theoretical_params: 理论参数字典
        """
        self.center = center
        self.theoretical_params = theoretical_params or {}
    
    def measure_height(self, points: np.ndarray) -> float:
        """
        测量齿高
        
        Args:
            points: 单齿点云
            
        Returns:
            齿高值
        """
        points = np.asarray(points)
        
        polar_points = cartesian_to_polar(points, self.center)
        radii = polar_points[:, 0]
        
        tooth_height = float(np.max(radii) - np.min(radii))
        
        return tooth_height
    
    def measure_width(self, points: np.ndarray) -> float:
        """
        测量齿宽
        
        Args:
            points: 单齿点云
            
        Returns:
            齿宽值（弧长）
        """
        points = np.asarray(points)
        
        polar_points = cartesian_to_polar(points, self.center)
        angles = polar_points[:, 1]
        radii = polar_points[:, 0]
        
        angle_range = np.max(angles) - np.min(angles)
        
        mean_radius = np.mean(radii)
        
        tooth_width = float(mean_radius * np.radians(angle_range))
        
        return tooth_width
    
    def measure_thickness(self, points: np.ndarray) -> float:
        """
        测量齿厚
        
        Args:
            points: 单齿点云
            
        Returns:
            齿厚值
        """
        points = np.asarray(points)
        
        z_coords = points[:, 2]
        
        tooth_thickness = float(np.max(z_coords) - np.min(z_coords))
        
        return tooth_thickness
    
    def measure_spacing(
        self,
        tooth1_points: np.ndarray,
        tooth2_points: np.ndarray
    ) -> float:
        """
        测量齿间距
        
        Args:
            tooth1_points: 第一个齿的点云
            tooth2_points: 第二个齿的点云
            
        Returns:
            齿间距值
        """
        polar1 = cartesian_to_polar(tooth1_points, self.center)
        polar2 = cartesian_to_polar(tooth2_points, self.center)
        
        angle1 = np.mean(polar1[:, 1])
        angle2 = np.mean(polar2[:, 1])
        
        angle_diff = np.abs(angle2 - angle1)
        if angle_diff > 180:
            angle_diff = 360 - angle_diff
        
        mean_radius = (np.mean(polar1[:, 0]) + np.mean(polar2[:, 0])) / 2
        
        spacing = float(mean_radius * np.radians(angle_diff))
        
        return spacing
    
    def calculate_tooth_error(
        self,
        points: np.ndarray,
        tooth_id: Optional[int] = None
    ) -> ToothError:
        """
        计算齿顶/齿底误差
        
        Args:
            points: 单齿点云
            tooth_id: 齿编号
            
        Returns:
            齿误差对象
        """
        points = np.asarray(points)
        
        polar_points = cartesian_to_polar(points, self.center)
        radii = polar_points[:, 0]
        angles = polar_points[:, 1]
        
        radial_error = float(np.std(radii))
        
        circumferential_error = float(np.std(angles))
        
        composite_error = float(np.sqrt(radial_error**2 + circumferential_error**2))
        
        return ToothError(
            radial_error=radial_error,
            circumferential_error=circumferential_error,
            composite_error=composite_error,
            tooth_id=tooth_id
        )
    
    def calculate_all_geometry(
        self,
        points: np.ndarray,
        tooth_id: Optional[int] = None
    ) -> GeometryResults:
        """
        计算所有几何指标
        
        Args:
            points: 单齿点云
            tooth_id: 齿编号
            
        Returns:
            几何测量结果
        """
        tooth_height = self.measure_height(points)
        tooth_width = self.measure_width(points)
        tooth_thickness = self.measure_thickness(points)
        
        tooth_error = self.calculate_tooth_error(points, tooth_id)
        
        theoretical_height = self.theoretical_params.get('height')
        theoretical_width = self.theoretical_params.get('width')
        theoretical_thickness = self.theoretical_params.get('thickness')
        
        return GeometryResults(
            tooth_height=tooth_height,
            tooth_width=tooth_width,
            tooth_thickness=tooth_thickness,
            tooth_error=tooth_error,
            theoretical_height=theoretical_height,
            theoretical_width=theoretical_width,
            theoretical_thickness=theoretical_thickness
        )
