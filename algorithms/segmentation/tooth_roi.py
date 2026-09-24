"""
齿ROI提取
"""
import numpy as np
from typing import Tuple
from ...models.base_types import BoundingBox


def extract_tooth_roi(
    points: np.ndarray,
    expand_ratio: float = 0.1
) -> Tuple[np.ndarray, BoundingBox]:
    """
    提取单齿ROI边界框
    
    Args:
        points: 单齿点云数组，形状为(n, 3)
        expand_ratio: 边界框扩展比例
        
    Returns:
        (roi_points, bounding_box) ROI点云和边界框
    """
    points = np.asarray(points)
    
    bounding_box = BoundingBox.from_points(points)
    
    expanded_box = bounding_box.expand(expand_ratio)
    
    mask = np.ones(len(points), dtype=bool)
    roi_points = points[mask]
    
    return roi_points, expanded_box
