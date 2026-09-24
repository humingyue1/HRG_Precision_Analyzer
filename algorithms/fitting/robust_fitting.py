"""
稳健平面拟合
RANSAC平面拟合
"""
import numpy as np
from typing import Tuple, Optional
import random


def ransac_plane_fitting(
    points: np.ndarray,
    max_iterations: int = 1000,
    inlier_threshold: float = 0.01,
    min_inliers: Optional[int] = None
) -> Tuple[Tuple[float, float, float, float], np.ndarray, float]:
    """
    RANSAC稳健平面拟合
    
    Args:
        points: 点云数组，形状为(n, 3)
        max_iterations: 最大迭代次数
        inlier_threshold: 内点阈值
        min_inliers: 最小内点数
        
    Returns:
        (plane_equation, inliers, rmse) 平面方程、内点索引、拟合误差
    """
    points = np.asarray(points)
    n_points = len(points)
    
    if n_points < 3:
        raise ValueError("点云数量不足，至少需要3个点")
    
    if min_inliers is None:
        min_inliers = int(0.5 * n_points)
    
    best_plane = None
    best_inliers = None
    best_inlier_count = 0
    
    for _ in range(max_iterations):
        sample_indices = random.sample(range(n_points), 3)
        sample_points = points[sample_indices]
        
        try:
            plane = _fit_plane_from_three_points(sample_points)
        except:
            continue
        
        distances = _calculate_distances(points, plane)
        
        inlier_mask = np.abs(distances) < inlier_threshold
        inlier_count = np.sum(inlier_mask)
        
        if inlier_count > best_inlier_count:
            best_inlier_count = inlier_count
            best_inliers = np.where(inlier_mask)[0]
            best_plane = plane
    
    if best_plane is None or best_inlier_count < min_inliers:
        from .plane_fitting import least_squares_plane_fitting
        best_plane, _ = least_squares_plane_fitting(points)
        best_inliers = np.arange(n_points)
    
    inlier_points = points[best_inliers]
    distances = _calculate_distances(inlier_points, best_plane)
    rmse = float(np.sqrt(np.mean(distances**2)))
    
    return best_plane, best_inliers, rmse


def _fit_plane_from_three_points(points: np.ndarray) -> Tuple[float, float, float, float]:
    """
    从三个点拟合平面
    
    Args:
        points: 三个点，形状为(3, 3)
        
    Returns:
        平面方程系数(a, b, c, d)
    """
    p1, p2, p3 = points
    
    v1 = p2 - p1
    v2 = p3 - p1
    
    normal = np.cross(v1, v2)
    
    norm = np.linalg.norm(normal)
    if norm < 1e-10:
        raise ValueError("三点共线，无法拟合平面")
    
    normal = normal / norm
    
    a, b, c = normal
    d = -(a * p1[0] + b * p1[1] + c * p1[2])
    
    return (a, b, c, d)


def _calculate_distances(points: np.ndarray, plane: Tuple[float, float, float, float]) -> np.ndarray:
    """
    计算点到平面距离
    """
    a, b, c, d = plane
    distances = (a * points[:, 0] + b * points[:, 1] + c * points[:, 2] + d) / np.sqrt(a**2 + b**2 + c**2)
    return distances
