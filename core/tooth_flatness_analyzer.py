"""
齿平整度分析器
专门用于齿状结构的平整度分析
"""
import numpy as np
from typing import Tuple, Optional
import sys
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from models.output_models import FlatnessResults
from algorithms.fitting.plane_fitting import least_squares_plane_fitting, ransac_plane_fitting, calculate_point_to_plane_distance


class ToothFlatnessAnalyzer:
    """齿平整度分析器类"""
    
    def __init__(self, standard: str = 'GB_T_24630'):
        """
        初始化齿平整度分析器
        
        Args:
            standard: 使用的国标标准
        """
        self.standard = standard
        self.flatness_grades = {
            '优秀': 0.005,
            '良好': 0.01,
            '合格': 0.02,
            '不合格': float('inf')
        }
    
    def fit_plane(
        self,
        points: np.ndarray,
        method: str = 'least_squares'
    ) -> Tuple[Tuple[float, float, float, float], float]:
        """
        拟合齿面平面
        
        Args:
            points: 齿面点云
            method: 拟合方法
            
        Returns:
            (plane_equation, rmse) 平面方程和拟合误差
        """
        points = np.asarray(points)
        
        if method == 'least_squares':
            plane_equation, rmse = least_squares_plane_fitting(points)
        elif method == 'ransac':
            plane_equation, inliers, rmse = ransac_plane_fitting(points)
        else:
            raise ValueError(f"不支持的拟合方法：{method}")
        
        return plane_equation, rmse
    
    def calculate_flatness(
        self,
        points: np.ndarray,
        plane_equation: Optional[Tuple[float, float, float, float]] = None
    ) -> FlatnessResults:
        """
        计算齿面平面度
        
        Args:
            points: 齿面点云
            plane_equation: 平面方程（可选）
            
        Returns:
            平整度分析结果
        """
        points = np.asarray(points)
        
        if plane_equation is None:
            plane_equation, rmse = self.fit_plane(points)
        else:
            distances = calculate_point_to_plane_distance(points, plane_equation)
            rmse = float(np.sqrt(np.mean(distances**2)))
        
        distances = calculate_point_to_plane_distance(points, plane_equation)
        
        flatness = float(np.max(distances) - np.min(distances))
        
        grade, is_qualified = self.evaluate_flatness_grade(flatness)
        
        return FlatnessResults(
            flatness=flatness,
            plane_equation=plane_equation,
            deviations=distances,
            grade=grade,
            is_qualified=is_qualified,
            rmse=rmse
        )
    
    def evaluate_flatness_grade(self, flatness: float) -> Tuple[str, bool]:
        """
        评估平面度等级
        
        Args:
            flatness: 平面度值
            
        Returns:
            (grade, is_qualified) 等级和是否合格
        """
        for grade, threshold in self.flatness_grades.items():
            if flatness <= threshold:
                return grade, grade != '不合格'
        
        return '不合格', False
    
    def calculate_array_flatness(
        self,
        tooth_centers: np.ndarray,
        tooth_heights: np.ndarray
    ) -> Tuple[float, float, float]:
        """
        计算齿列平整度
        
        Args:
            tooth_centers: 齿中心坐标数组
            tooth_heights: 齿高度数组
            
        Returns:
            (flatness, mean_height, std_height) 齿列平整度、平均高度、高度标准差
        """
        tooth_heights = np.asarray(tooth_heights)
        
        mean_height = float(np.mean(tooth_heights))
        std_height = float(np.std(tooth_heights))
        flatness = float(np.max(tooth_heights) - np.min(tooth_heights))
        
        return flatness, mean_height, std_height
