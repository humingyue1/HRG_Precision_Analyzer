"""
区域生长分割算法
基于极坐标角度分割识别单个齿
"""
import numpy as np
from typing import List, Tuple, Optional
import sys
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(os.path.dirname(current_dir))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from utils.coordinate_transform import cartesian_to_polar


def region_growing_segmentation(
    points: np.ndarray,
    center: Tuple[float, float, float] = (0, 0, 0),
    tooth_count: Optional[int] = None,
    angle_tolerance: float = 2.0
) -> List[np.ndarray]:
    """
    基于区域生长的点云分割（极坐标角度分割）
    
    Args:
        points: 点云数组，形状为(n, 3)
        center: 振子中心坐标
        tooth_count: 理论齿数（用于验证）
        angle_tolerance: 角度容差（度）
        
    Returns:
        分割后的点云簇列表，每个元素为一个齿的点云
    """
    points = np.asarray(points)
    
    polar_points = cartesian_to_polar(points, center)
    angles = polar_points[:, 1]
    
    angles_sorted = np.sort(angles)
    angle_gaps = np.diff(angles_sorted)
    angle_gaps = np.append(angle_gaps, 360 + angles_sorted[0] - angles_sorted[-1])
    
    if tooth_count is not None:
        expected_gap = 360.0 / tooth_count
        gap_threshold = expected_gap / 2
    else:
        gap_threshold = np.percentile(angle_gaps, 90)
    
    tooth_boundaries = []
    cumulative_angle = 0
    
    for i, gap in enumerate(angle_gaps):
        cumulative_angle += gap
        if gap > gap_threshold:
            tooth_boundaries.append(angles_sorted[i])
    
    if not tooth_boundaries:
        return [points]
    
    tooth_boundaries = np.sort(tooth_boundaries)
    
    tooth_clusters = []
    for i in range(len(tooth_boundaries)):
        start_angle = tooth_boundaries[i]
        end_angle = tooth_boundaries[(i + 1) % len(tooth_boundaries)]
        
        if end_angle <= start_angle:
            end_angle += 360
        
        mask = (angles >= start_angle) & (angles < end_angle)
        
        if not np.any(mask):
            mask = (angles >= start_angle - 360) & (angles < end_angle - 360)
        
        if np.any(mask):
            tooth_clusters.append(points[mask])
    
    if tooth_count is not None and len(tooth_clusters) != tooth_count:
        tooth_clusters = _refine_segmentation(points, angles, tooth_count)
    
    return tooth_clusters


def _refine_segmentation(points: np.ndarray, angles: np.ndarray, tooth_count: int) -> List[np.ndarray]:
    """
    优化分割结果
    
    Args:
        points: 点云数组
        angles: 极坐标角度数组
        tooth_count: 理论齿数
        
    Returns:
        优化后的点云簇列表
    """
    angle_step = 360.0 / tooth_count
    tooth_clusters = []
    
    for i in range(tooth_count):
        start_angle = i * angle_step
        end_angle = (i + 1) * angle_step
        
        mask = (angles >= start_angle) & (angles < end_angle)
        
        if np.any(mask):
            tooth_clusters.append(points[mask])
    
    return tooth_clusters
