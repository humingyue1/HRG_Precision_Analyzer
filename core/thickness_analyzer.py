"""
HRG谐振陀螺加工精度分析系统 - 壁厚分析器
版本: v4.0
"""

import numpy as np
from typing import Optional, Dict, Any
from scipy.spatial import KDTree
# 支持相对导入和绝对导入
try:
    from .base_analyzer import BaseAnalyzer, ThicknessResult
except ImportError:
    from base_analyzer import BaseAnalyzer, ThicknessResult


class ThicknessAnalyzer(BaseAnalyzer):
    """
    壁厚分析器
    实现壁厚均匀性分析
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化壁厚分析器
        
        Args:
            config: 配置参数，包含：
                - normal_neighbors: 法向量估计邻域点数
                - search_radius: KD树搜索半径
        """
        super().__init__(config)
        
        self.normal_neighbors = self.config.get('normal_neighbors', 20)
        self.search_radius = self.config.get('search_radius', 5.0)
        
    def analyze(self, point_cloud: np.ndarray) -> ThicknessResult:
        """
        执行壁厚分析
        
        Args:
            point_cloud: 点云数据 (N, 3)
            
        Returns:
            ThicknessResult对象
        """
        if not self.validate_input(point_cloud):
            raise ValueError("无效的点云数据")
        
        self.logger.info("开始壁厚分析...")
        
        try:
            # 1. 归一化点云
            normalized = self.normalize_point_cloud(point_cloud)
            
            # 2. 分离内外表面
            inner_surface, outer_surface = self._separate_surfaces(normalized)
            
            # 3. 计算局部壁厚
            thickness_values = self._compute_local_thickness(outer_surface, inner_surface)
            
            # 4. 计算统计量
            mean_thickness = float(np.mean(thickness_values))
            std_thickness = float(np.std(thickness_values))
            min_thickness = float(np.min(thickness_values))
            max_thickness = float(np.max(thickness_values))
            
            # 5. 计算不均匀度
            uniformity = std_thickness / mean_thickness if mean_thickness > 0 else 0
            
            # 6. 创建结果
            result = ThicknessResult(
                mean_thickness=mean_thickness,
                std_thickness=std_thickness,
                uniformity=float(uniformity),
                min_thickness=min_thickness,
                max_thickness=max_thickness,
                thickness_map=thickness_values
            )
            
            self.log_result(result)
            return result
            
        except Exception as e:
            self.handle_error(e, "壁厚分析失败")
            raise
    
    def _separate_surfaces(self, point_cloud: np.ndarray) -> tuple:
        """
        分离内外表面
        
        Args:
            point_cloud: 点云数据
            
        Returns:
            (内表面, 外表面)
        """
        # 使用半径分离
        r = np.sqrt(point_cloud[:, 0]**2 + point_cloud[:, 1]**2)
        
        # 使用聚类方法分离内外表面
        # 简化：使用半径的中位数作为分界
        median_r = np.median(r)
        
        inner_mask = r < median_r
        outer_mask = r >= median_r
        
        inner_surface = point_cloud[inner_mask]
        outer_surface = point_cloud[outer_mask]
        
        return inner_surface, outer_surface
    
    def _compute_local_thickness(self, outer_surface: np.ndarray, 
                                 inner_surface: np.ndarray) -> np.ndarray:
        """
        计算局部壁厚（高性能版本，保持精度）
        
        Args:
            outer_surface: 外表面点云
            inner_surface: 内表面点云
            
        Returns:
            壁厚值数组
        """
        from scipy.spatial import cKDTree
        import multiprocessing as mp
        
        # 构建KD树（使用cKDTree，更快）
        tree = cKDTree(inner_surface)
        
        self.logger.info(f"计算壁厚... (外表面: {len(outer_surface)} 点)")
        
        # 方法1: 批量查询（向量化，最快）
        # 直接对所有外表面点查询最近邻
        distances, indices = tree.query(outer_surface, k=1)
        
        self.logger.info(f"壁厚计算完成")
        
        return np.array(distances)
    
    def _estimate_normal(self, point: np.ndarray, 
                        point_cloud: np.ndarray) -> np.ndarray:
        """
        估计点的法向量
        
        Args:
            point: 目标点
            point_cloud: 点云数据
            
        Returns:
            法向量
        """
        # 构建KD树
        tree = KDTree(point_cloud)
        
        # 查找邻近点
        distances, indices = tree.query(point, k=self.normal_neighbors)
        neighbors = point_cloud[indices]
        
        # 使用PCA估计法向量
        centered = neighbors - np.mean(neighbors, axis=0)
        cov = np.cov(centered.T)
        eigenvalues, eigenvectors = np.linalg.eigh(cov)
        
        # 最小特征值对应的特征向量为法向量
        normal = eigenvectors[:, 0]
        
        return normal
    
    def generate_thickness_colormap(self, thickness_values: np.ndarray,
                                   points: np.ndarray) -> np.ndarray:
        """
        生成壁厚分布彩色云图
        
        Args:
            thickness_values: 壁厚值
            points: 点坐标
            
        Returns:
            彩色点云 (N, 6): [x, y, z, r, g, b]
        """
        # 归一化壁厚值到0-1
        t_min = np.min(thickness_values)
        t_max = np.max(thickness_values)
        
        if t_max - t_min > 0:
            normalized = (thickness_values - t_min) / (t_max - t_min)
        else:
            normalized = np.zeros_like(thickness_values)
        
        # 映射到颜色（使用jet色图）
        colors = self._value_to_color(normalized)
        
        # 组合坐标和颜色
        colored_points = np.hstack([points, colors])
        
        return colored_points
    
    def _value_to_color(self, values: np.ndarray) -> np.ndarray:
        """
        将数值映射到颜色
        
        Args:
            values: 归一化值 (0-1)
            
        Returns:
            RGB颜色 (N, 3)
        """
        # 简化的jet色图
        colors = np.zeros((len(values), 3))
        
        for i, v in enumerate(values):
            if v < 0.25:
                # 蓝到青
                colors[i, 0] = 0
                colors[i, 1] = 4 * v
                colors[i, 2] = 1
            elif v < 0.5:
                # 青到绿
                colors[i, 0] = 0
                colors[i, 1] = 1
                colors[i, 2] = 1 - 4 * (v - 0.25)
            elif v < 0.75:
                # 绿到黄
                colors[i, 0] = 4 * (v - 0.5)
                colors[i, 1] = 1
                colors[i, 2] = 0
            else:
                # 黄到红
                colors[i, 0] = 1
                colors[i, 1] = 1 - 4 * (v - 0.75)
                colors[i, 2] = 0
        
        return colors
