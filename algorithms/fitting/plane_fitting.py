"""
平面拟合算法
最小二乘平面拟合
"""
import numpy as np
from typing import Tuple


def least_squares_plane_fitting(points: np.ndarray) -> Tuple[Tuple[float, float, float, float], float]:
    """
    最小二乘平面拟合
    
    平面方程：ax + by + cz + d = 0
    
    Args:
        points: 点云数组，形状为(n, 3)
        
    Returns:
        (plane_equation, rmse) 平面方程系数(a, b, c, d)和拟合误差RMSE
    """
    points = np.asarray(points)
    
    if len(points) < 3:
        raise ValueError("点云数量不足，至少需要3个点")
    
    centroid = np.mean(points, axis=0)
    
    points_centered = points - centroid
    
    cov_matrix = np.cov(points_centered.T)
    
    eigenvalues, eigenvectors = np.linalg.eigh(cov_matrix)
    
    normal = eigenvectors[:, 0]
    
    a, b, c = normal
    d = -(a * centroid[0] + b * centroid[1] + c * centroid[2])
    
    norm = np.sqrt(a**2 + b**2 + c**2)
    a, b, c, d = a/norm, b/norm, c/norm, d/norm
    
    distances = calculate_point_to_plane_distance(points, (a, b, c, d))
    rmse = np.sqrt(np.mean(distances**2))
    
    return (a, b, c, d), float(rmse)


def calculate_point_to_plane_distance(points: np.ndarray, plane_equation: Tuple[float, float, float, float]) -> np.ndarray:
    """
    计算点到平面距离
    
    Args:
        points: 点云数组，形状为(n, 3)
        plane_equation: 平面方程系数(a, b, c, d)
        
    Returns:
        距离数组，形状为(n,)
    """
    points = np.asarray(points)
    a, b, c, d = plane_equation
    
    distances = (a * points[:, 0] + b * points[:, 1] + c * points[:, 2] + d) / np.sqrt(a**2 + b**2 + c**2)
    
    return distances
