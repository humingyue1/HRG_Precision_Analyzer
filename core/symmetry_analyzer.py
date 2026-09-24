"""
HRG谐振陀螺加工精度分析系统 - 对称性分析器
版本: v4.0
"""

import numpy as np
from typing import Optional, Dict, Any, List
from scipy.spatial import KDTree
# 支持相对导入和绝对导入
try:
    from .base_analyzer import BaseAnalyzer, SymmetryResult
except ImportError:
    from base_analyzer import BaseAnalyzer, SymmetryResult


class SymmetryAnalyzer(BaseAnalyzer):
    """
    对称性分析器
    实现n阶旋转对称性误差分析
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化对称性分析器
        
        Args:
            config: 配置参数，包含：
                - symmetry_orders: 对称性阶数列表
                - axis_finding_method: 对称轴查找方法
                - polar_resolution: 极坐标分辨率
        """
        super().__init__(config)
        
        self.symmetry_orders = self.config.get('symmetry_orders', [2, 4, 6, 8])
        self.axis_finding_method = self.config.get('axis_finding_method', 'pca')
        self.polar_resolution = self.config.get('polar_resolution', 1.0)
        
    def analyze(self, point_cloud: np.ndarray) -> SymmetryResult:
        """
        执行对称性分析
        
        Args:
            point_cloud: 点云数据 (N, 3)
            
        Returns:
            SymmetryResult对象
        """
        if not self.validate_input(point_cloud):
            raise ValueError("无效的点云数据")
        
        self.logger.info("开始对称性分析...")
        
        try:
            # 1. 归一化点云
            normalized = self.normalize_point_cloud(point_cloud)
            
            # 2. 找到对称轴
            axis = self._find_symmetry_axis(normalized)
            
            # 3. 转换到极坐标
            polar_coords = self._to_polar_coordinates(normalized, axis)
            
            # 4. 计算各阶对称性误差
            symmetry_errors = {}
            for n in self.symmetry_orders:
                error = self._compute_symmetry_error(polar_coords, n)
                symmetry_errors[n] = error
            
            # 5. 找到最大不对称位置
            max_asymmetry = self._find_max_asymmetry(polar_coords, symmetry_errors)
            
            # 6. 创建结果
            result = SymmetryResult(
                symmetry_errors=symmetry_errors,
                max_asymmetry_position=max_asymmetry,
                polar_data=polar_coords
            )
            
            self.log_result(result)
            return result
            
        except Exception as e:
            self.handle_error(e, "对称性分析失败")
            raise
    
    def _find_symmetry_axis(self, point_cloud: np.ndarray) -> np.ndarray:
        """
        找到旋转对称轴
        
        Args:
            point_cloud: 点云数据
            
        Returns:
            对称轴方向向量 (3,)
        """
        if self.axis_finding_method == 'pca':
            # 使用PCA找到主轴
            eigenvalues, eigenvectors = self.compute_pca(point_cloud)
            # 选择最小特征值对应的特征向量作为对称轴
            axis = eigenvectors[:, 2]
        else:
            # 使用几何方法
            # 假设Z轴为对称轴
            axis = np.array([0, 0, 1])
        
        return axis
    
    def _to_polar_coordinates(self, point_cloud: np.ndarray, 
                             axis: np.ndarray) -> np.ndarray:
        """
        转换到极坐标
        
        Args:
            point_cloud: 点云数据
            axis: 对称轴
            
        Returns:
            极坐标数据 (N, 3): [r, theta, z]
        """
        # 旋转点云，使对称轴与Z轴对齐
        rotated = self._align_to_z_axis(point_cloud, axis)
        
        # 转换到极坐标
        r = np.sqrt(rotated[:, 0]**2 + rotated[:, 1]**2)
        theta = np.arctan2(rotated[:, 1], rotated[:, 0])
        z = rotated[:, 2]
        
        return np.column_stack([r, theta, z])
    
    def _align_to_z_axis(self, point_cloud: np.ndarray, 
                        axis: np.ndarray) -> np.ndarray:
        """
        旋转点云，使对称轴与Z轴对齐
        
        Args:
            point_cloud: 点云数据
            axis: 对称轴
            
        Returns:
            旋转后的点云
        """
        # 目标轴（Z轴）
        target = np.array([0, 0, 1])
        
        # 计算旋转轴和角度
        rotation_axis = np.cross(axis, target)
        
        if np.linalg.norm(rotation_axis) < 1e-10:
            # 轴已经对齐
            return point_cloud
        
        rotation_axis = rotation_axis / np.linalg.norm(rotation_axis)
        angle = np.arccos(np.dot(axis, target))
        
        # Rodrigues旋转公式
        K = np.array([
            [0, -rotation_axis[2], rotation_axis[1]],
            [rotation_axis[2], 0, -rotation_axis[0]],
            [-rotation_axis[1], rotation_axis[0], 0]
        ])
        
        R = np.eye(3) + np.sin(angle) * K + (1 - np.cos(angle)) * (K @ K)
        
        return point_cloud @ R.T
    
    def _compute_symmetry_error(self, polar_coords: np.ndarray, 
                               n: int) -> float:
        """
        计算n阶旋转对称性误差（高性能版本，保持精度）
        
        Args:
            polar_coords: 极坐标数据
            n: 对称阶数
            
        Returns:
            对称性误差 (0-1)
        """
        from scipy.spatial import cKDTree
        
        r = polar_coords[:, 0]
        theta = polar_coords[:, 1]
        z = polar_coords[:, 2]
        
        self.logger.info(f"计算{n}阶对称性误差... (点数: {len(polar_coords)})")
        
        # 构建KD树（使用cKDTree，更快）
        tree = cKDTree(polar_coords)
        
        # 旋转角度
        rotation_angle = 2 * np.pi / n
        
        # 批量计算旋转后的点
        theta_rotated = theta + rotation_angle
        
        # 处理角度周期性
        theta_rotated = np.where(theta_rotated > np.pi, theta_rotated - 2*np.pi, theta_rotated)
        theta_rotated = np.where(theta_rotated < -np.pi, theta_rotated + 2*np.pi, theta_rotated)
        
        # 构建查询点（向量化）
        query_points = np.column_stack([r, theta_rotated, z])
        
        # 批量查询最近邻
        distances, indices = tree.query(query_points, k=1)
        
        # 计算误差（向量化）
        distance_threshold = 0.1 * np.mean(r)
        valid_mask = distances < distance_threshold
        
        if np.sum(valid_mask) > 0:
            z_diff = np.abs(z[valid_mask] - z[indices[valid_mask]])
            mean_error = np.mean(z_diff)
            
            # 归一化到0-1范围
            z_range = np.max(z) - np.min(z)
            normalized_error = mean_error / z_range if z_range > 0 else 0
        else:
            normalized_error = 0
        
        self.logger.info(f"{n}阶对称性误差计算完成")
        
        return float(normalized_error)
    
    def _find_max_asymmetry(self, polar_coords: np.ndarray, 
                           symmetry_errors: Dict[int, float]) -> tuple:
        """
        找到最大不对称位置
        
        Args:
            polar_coords: 极坐标数据
            symmetry_errors: 各阶对称性误差
            
        Returns:
            (角度, 误差值)
        """
        # 选择误差最大的阶数
        max_order = max(symmetry_errors, key=symmetry_errors.get)
        
        # 在该阶数下找到最大不对称位置
        theta = polar_coords[:, 1]
        z = polar_coords[:, 2]
        
        # 简化：找到z值变化最大的角度
        # 按角度排序
        idx = np.argsort(theta)
        theta_sorted = theta[idx]
        z_sorted = z[idx]
        
        # 计算z值梯度
        dz = np.abs(np.gradient(z_sorted))
        
        # 找到最大梯度位置
        max_idx = np.argmax(dz)
        max_theta = theta_sorted[max_idx]
        max_error = dz[max_idx]
        
        return (float(max_theta), float(max_error))
