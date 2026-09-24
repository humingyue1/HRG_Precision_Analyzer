"""
HRG谐振陀螺加工精度分析系统 - 谐振参数分析器
版本: v4.0
"""

import numpy as np
from typing import Optional, Dict, Any
# 支持相对导入和绝对导入
try:
    from .base_analyzer import BaseAnalyzer, ResonanceResult
except ImportError:
    from base_analyzer import BaseAnalyzer, ResonanceResult


class ResonanceAnalyzer(BaseAnalyzer):
    """
    谐振参数分析器
    分析质量分布、惯性矩等谐振相关参数
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化谐振参数分析器
        
        Args:
            config: 配置参数，包含：
                - material_density: 材料密度 (kg/m³)
                - compute_inertia: 是否计算惯性矩
        """
        super().__init__(config)
        
        self.material_density = self.config.get('material_density', 7850.0)
        self.compute_inertia = self.config.get('compute_inertia', True)
        
    def analyze(self, point_cloud: np.ndarray) -> ResonanceResult:
        """
        执行谐振参数分析
        
        Args:
            point_cloud: 点云数据 (N, 3)
            
        Returns:
            ResonanceResult对象
        """
        if not self.validate_input(point_cloud):
            raise ValueError("无效的点云数据")
        
        self.logger.info("开始谐振参数分析...")
        
        try:
            # 1. 归一化点云
            normalized = self.normalize_point_cloud(point_cloud)
            
            # 2. 计算质量分布均匀性
            mass_uniformity = self._compute_mass_uniformity(normalized)
            
            # 3. 计算惯性张量
            inertia_tensor = None
            if self.compute_inertia:
                inertia_tensor = self._compute_inertia_tensor(normalized)
            
            # 4. 估计频率偏移
            frequency_shift = self._estimate_frequency_shift(
                mass_uniformity, inertia_tensor
            )
            
            # 5. 创建结果
            result = ResonanceResult(
                mass_uniformity=mass_uniformity,
                inertia_tensor=inertia_tensor,
                frequency_shift_estimate=frequency_shift
            )
            
            self.log_result(result)
            return result
            
        except Exception as e:
            self.handle_error(e, "谐振参数分析失败")
            raise
    
    def _compute_mass_uniformity(self, point_cloud: np.ndarray) -> float:
        """
        计算质量分布均匀性
        
        Args:
            point_cloud: 点云数据
            
        Returns:
            质量分布均匀性 (0-1)，1表示完全均匀
        """
        # 转换到极坐标
        r = np.sqrt(point_cloud[:, 0]**2 + point_cloud[:, 1]**2)
        theta = np.arctan2(point_cloud[:, 1], point_cloud[:, 0])
        z = point_cloud[:, 2]
        
        # 将空间划分为扇形区域
        n_sectors = 36  # 36个扇形，每个10度
        sector_size = 2 * np.pi / n_sectors
        
        # 计算每个扇形的质量（点数）
        sector_masses = []
        for i in range(n_sectors):
            theta_min = -np.pi + i * sector_size
            theta_max = theta_min + sector_size
            
            mask = (theta >= theta_min) & (theta < theta_max)
            sector_mass = np.sum(mask)  # 点数作为质量估计
            sector_masses.append(sector_mass)
        
        sector_masses = np.array(sector_masses)
        
        # 计算均匀性
        mean_mass = np.mean(sector_masses)
        std_mass = np.std(sector_masses)
        
        if mean_mass > 0:
            uniformity = 1 - std_mass / mean_mass
        else:
            uniformity = 0
        
        return float(max(0, min(1, uniformity)))
    
    def _compute_inertia_tensor(self, point_cloud: np.ndarray) -> np.ndarray:
        """
        计算惯性张量
        
        Args:
            point_cloud: 点云数据
            
        Returns:
            惯性张量 (3, 3)
        """
        # 假设每个点代表一个小质量单元
        # 单元质量 = 总质量 / 点数
        total_mass = self._estimate_total_mass(point_cloud)
        point_mass = total_mass / len(point_cloud)
        
        # 计算惯性张量分量
        Ixx = np.sum(point_mass * (point_cloud[:, 1]**2 + point_cloud[:, 2]**2))
        Iyy = np.sum(point_mass * (point_cloud[:, 0]**2 + point_cloud[:, 2]**2))
        Izz = np.sum(point_mass * (point_cloud[:, 0]**2 + point_cloud[:, 1]**2))
        
        Ixy = -np.sum(point_mass * point_cloud[:, 0] * point_cloud[:, 1])
        Ixz = -np.sum(point_mass * point_cloud[:, 0] * point_cloud[:, 2])
        Iyz = -np.sum(point_mass * point_cloud[:, 1] * point_cloud[:, 2])
        
        inertia_tensor = np.array([
            [Ixx, Ixy, Ixz],
            [Ixy, Iyy, Iyz],
            [Ixz, Iyz, Izz]
        ])
        
        return inertia_tensor
    
    def _estimate_total_mass(self, point_cloud: np.ndarray) -> float:
        """
        估计总质量
        
        Args:
            point_cloud: 点云数据
            
        Returns:
            总质量 (kg)
        """
        # 估计体积（使用凸包或简化方法）
        # 简化：使用包围盒体积
        x_range = np.max(point_cloud[:, 0]) - np.min(point_cloud[:, 0])
        y_range = np.max(point_cloud[:, 1]) - np.min(point_cloud[:, 1])
        z_range = np.max(point_cloud[:, 2]) - np.min(point_cloud[:, 2])
        
        # 假设为壳体，体积 = 表面积 * 壁厚
        # 简化：使用包围盒体积的10%
        volume = x_range * y_range * z_range * 0.1
        
        # 质量 = 密度 * 体积
        mass = self.material_density * volume * 1e-9  # 转换单位
        
        return mass
    
    def _estimate_frequency_shift(self, mass_uniformity: float,
                                  inertia_tensor: Optional[np.ndarray]) -> Optional[float]:
        """
        估计谐振频率偏移
        
        Args:
            mass_uniformity: 质量分布均匀性
            inertia_tensor: 惯性张量
            
        Returns:
            频率偏移估计 (无量纲)
        """
        if inertia_tensor is None:
            return None
        
        # 计算惯性主轴
        eigenvalues, _ = np.linalg.eigh(inertia_tensor)
        
        # 理想情况下，惯性主轴应该相等（对于旋转对称体）
        # 频率偏移与惯性主轴的差异相关
        
        # 归一化特征值
        eigenvalues = eigenvalues / np.max(eigenvalues)
        
        # 计算频率偏移（简化模型）
        # 频率偏移 ∝ 惯性主轴差异
        frequency_shift = np.std(eigenvalues) * (1 - mass_uniformity)
        
        return float(frequency_shift)
