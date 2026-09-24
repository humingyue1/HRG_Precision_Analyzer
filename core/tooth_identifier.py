"""
齿识别器
识别和分割振子周边的齿状结构
"""
import numpy as np
from typing import List, Tuple, Optional
import sys
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from models.base_types import BoundingBox, ValidationResult
from models.output_models import ToothInfo
from algorithms.segmentation.region_growing import region_growing_segmentation
from algorithms.segmentation.tooth_roi import extract_tooth_roi
from utils.coordinate_transform import cartesian_to_polar


class ToothIdentifier:
    """齿识别器类"""
    
    def __init__(
        self,
        center: Tuple[float, float, float] = (0, 0, 0),
        theoretical_tooth_count: Optional[int] = None,
        segmentation_method: str = 'region_growing'
    ):
        """
        初始化齿识别器
        
        Args:
            center: 振子中心坐标
            theoretical_tooth_count: 理论齿数
            segmentation_method: 分割方法
        """
        self.center = center
        self.theoretical_tooth_count = theoretical_tooth_count
        self.segmentation_method = segmentation_method
    
    def segment_teeth(self, points: np.ndarray) -> Tuple[np.ndarray, List[np.ndarray]]:
        """
        分割齿状结构与背景
        
        Args:
            points: 点云数组
            
        Returns:
            (teeth_points, tooth_clusters) 齿点云和各齿点云列表
        """
        points = np.asarray(points)
        
        tooth_clusters = region_growing_segmentation(
            points,
            center=self.center,
            tooth_count=self.theoretical_tooth_count
        )
        
        if len(tooth_clusters) > 0:
            teeth_points = np.vstack(tooth_clusters)
        else:
            teeth_points = points
        
        return teeth_points, tooth_clusters
    
    def identify_teeth(self, points: np.ndarray) -> List[ToothInfo]:
        """
        识别并编号所有齿
        
        Args:
            points: 点云数组
            
        Returns:
            齿信息列表
        """
        teeth_points, tooth_clusters = self.segment_teeth(points)
        
        tooth_infos = []
        
        for i, tooth_points in enumerate(tooth_clusters):
            tooth_info = self._create_tooth_info(tooth_points, i)
            tooth_infos.append(tooth_info)
        
        tooth_infos = self._sort_teeth_by_angle(tooth_infos)
        
        for i, tooth_info in enumerate(tooth_infos):
            tooth_info.tooth_id = i
        
        return tooth_infos
    
    def _create_tooth_info(self, tooth_points: np.ndarray, index: int) -> ToothInfo:
        """
        创建单齿信息
        
        Args:
            tooth_points: 单齿点云
            index: 索引
            
        Returns:
            齿信息对象
        """
        center = tuple(np.mean(tooth_points, axis=0))
        
        bounding_box = BoundingBox.from_points(tooth_points)
        
        polar_points = cartesian_to_polar(tooth_points, self.center)
        tooth_angle = float(np.mean(polar_points[:, 1]))
        
        return ToothInfo(
            tooth_id=index,
            center=center,
            bounding_box=bounding_box,
            boundary_points=tooth_points,
            tooth_angle=tooth_angle
        )
    
    def _sort_teeth_by_angle(self, tooth_infos: List[ToothInfo]) -> List[ToothInfo]:
        """
        按角度排序齿
        
        Args:
            tooth_infos: 齿信息列表
            
        Returns:
            排序后的齿信息列表
        """
        return sorted(tooth_infos, key=lambda t: t.tooth_angle)
    
    def extract_roi(self, tooth_points: np.ndarray, expand_ratio: float = 0.1) -> Tuple[np.ndarray, BoundingBox]:
        """
        提取单齿ROI区域
        
        Args:
            tooth_points: 单齿点云
            expand_ratio: 边界框扩展比例
            
        Returns:
            (roi_points, bounding_box) ROI点云和边界框
        """
        return extract_tooth_roi(tooth_points, expand_ratio)
    
    def validate_tooth_count(self, identified_count: int) -> ValidationResult:
        """
        验证齿数是否正确
        
        Args:
            identified_count: 识别的齿数
            
        Returns:
            验证结果
        """
        result = ValidationResult(is_valid=True)
        
        if self.theoretical_tooth_count is None:
            result.add_warning("未设置理论齿数，无法验证")
            result.details['identified_count'] = identified_count
            return result
        
        result.details['identified_count'] = identified_count
        result.details['theoretical_count'] = self.theoretical_tooth_count
        
        if identified_count != self.theoretical_tooth_count:
            result.is_valid = False
            result.add_error(
                f"齿数不匹配：识别齿数{identified_count} ≠ 理论齿数{self.theoretical_tooth_count}"
            )
        
        return result
