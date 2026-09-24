"""
HRG谐振陀螺加工精度分析系统 - 分析器基类
版本: v4.0
"""

import numpy as np
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
import logging
from dataclasses import dataclass, asdict, field


@dataclass
class FilterConfig:
    """滤波器配置参数
    GB/T 6062-2009 第3.1条, GB/T 18777-2002
    """
    lambda_s: float = 0.0025  # 短波截止波长 (mm), GB/T 6062-2009 3.1.4
    lambda_c: float = 0.8     # 粗糙度长波截止波长 (mm), GB/T 3505-2009 3.1.9
    lambda_f: float = 8.0     # 波纹度长波截止波长 (mm), GB/T 3505-2009 3.1.7
    upr_low: int = 1          # upr滤波器通带下限 (波数/转), GB/T 7235-2004 4.1.3
    upr_high: int = 50        # upr滤波器通带上限 (波数/转), GB/T 7235-2004 5.3.1
    transmission_at_cutoff: float = 0.50  # 截止波长处传输率, GB/T 18777-2002

    def to_dict(self) -> Dict[str, Any]:
        return {
            'lambda_s': self.lambda_s,
            'lambda_c': self.lambda_c,
            'lambda_f': self.lambda_f,
            'upr_low': self.upr_low,
            'upr_high': self.upr_high,
            'transmission_at_cutoff': self.transmission_at_cutoff,
        }


@dataclass
class RoughnessResult:
    """表面粗糙度分析结果
    GB/T 3505-2009 第4章
    """
    ra: float  # 轮廓算术平均偏差 (μm), GB/T 3505-2009 4.2.1
    rq: float  # 轮廓均方根偏差 (μm), GB/T 3505-2009 4.2.2
    rz: float  # 轮廓最大高度 (μm), GB/T 3505-2009 4.1.3
    rsm: float  # 轮廓单元的平均宽度 (mm), GB/T 3505-2009 4.3.1
    profile_data: Optional[np.ndarray] = None
    baseline_data: Optional[np.ndarray] = None
    sampling_length: float = 0.8       # 取样长度 lr (mm), GB/T 3505-2009 3.1.9
    num_sampling_lengths: int = 5      # 取样长度数量
    per_sampling_rz: Optional[List[float]] = None   # 各取样长度Rz值
    per_sampling_rsm: Optional[List[float]] = None  # 各取样长度RSm值
    lambda_s: float = 0.0025   # 短波截止波长 (mm), GB/T 6062-2009 3.1.4
    lambda_c: float = 0.8      # 长波截止波长 (mm), GB/T 3505-2009 3.1.9

    def to_dict(self) -> Dict[str, Any]:
        result = {
            'ra': self.ra,
            'rq': self.rq,
            'rz': self.rz,
            'rsm': self.rsm,
            'sampling_length': self.sampling_length,
            'num_sampling_lengths': self.num_sampling_lengths,
            'lambda_s': self.lambda_s,
            'lambda_c': self.lambda_c,
        }
        if self.per_sampling_rz is not None:
            result['per_sampling_rz'] = self.per_sampling_rz
        if self.per_sampling_rsm is not None:
            result['per_sampling_rsm'] = self.per_sampling_rsm
        if self.profile_data is not None:
            result['profile_data'] = self.profile_data.tolist()
        if self.baseline_data is not None:
            result['baseline_data'] = self.baseline_data.tolist()
        return result


@dataclass
class WavinessResult:
    """波纹度分析结果
    GB/T 3505-2009 第3.1.7条
    """
    waviness_amplitude: float  # 波纹度幅值 (μm)
    waviness_profile: Optional[np.ndarray] = None
    lambda_f: float = 8.0       # 长波截止波长 (mm), GB/T 3505-2009 3.1.7
    lambda_c: float = 2.5       # 短波截止波长 (mm), GB/T 3505-2009 3.1.7
    nominal_shape_removed: bool = True  # 是否已去除标称形状

    def to_dict(self) -> Dict[str, Any]:
        result = {
            'waviness_amplitude': self.waviness_amplitude,
            'lambda_f': self.lambda_f,
            'lambda_c': self.lambda_c,
            'nominal_shape_removed': self.nominal_shape_removed,
        }
        if self.waviness_profile is not None:
            result['waviness_profile'] = self.waviness_profile.tolist()
        return result


@dataclass
class SymmetryResult:
    """对称性分析结果"""
    symmetry_errors: Dict[int, float]  # 各阶对称性误差 {阶数: 误差值}
    max_asymmetry_position: Optional[tuple] = None  # 最大不对称位置 (角度, 误差)
    polar_data: Optional[np.ndarray] = None  # 极坐标数据
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        result = {'symmetry_errors': self.symmetry_errors}
        if self.max_asymmetry_position is not None:
            result['max_asymmetry_position'] = self.max_asymmetry_position
        if self.polar_data is not None:
            result['polar_data'] = self.polar_data.tolist()
        return result


@dataclass
class ThicknessResult:
    """壁厚分析结果"""
    mean_thickness: float  # 平均壁厚 (mm)
    std_thickness: float  # 壁厚标准差 (mm)
    uniformity: float  # 壁厚不均匀度 (无量纲，0-1)
    min_thickness: float  # 最小壁厚 (mm)
    max_thickness: float  # 最大壁厚 (mm)
    thickness_map: Optional[np.ndarray] = None  # 壁厚分布图
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        result = {
            'mean_thickness': self.mean_thickness,
            'std_thickness': self.std_thickness,
            'uniformity': self.uniformity,
            'min_thickness': self.min_thickness,
            'max_thickness': self.max_thickness,
        }
        if self.thickness_map is not None:
            result['thickness_map'] = self.thickness_map.tolist()
        return result


@dataclass
class ResonanceResult:
    """谐振参数分析结果"""
    mass_uniformity: float  # 质量分布均匀性 (无量纲，0-1)
    inertia_tensor: Optional[np.ndarray] = None  # 惯性张量
    frequency_shift_estimate: Optional[float] = None  # 频率偏移估计
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        result = {'mass_uniformity': self.mass_uniformity}
        if self.inertia_tensor is not None:
            result['inertia_tensor'] = self.inertia_tensor.tolist()
        if self.frequency_shift_estimate is not None:
            result['frequency_shift_estimate'] = self.frequency_shift_estimate
        return result


@dataclass
class QualityResult:
    """质量评价结果"""
    total_score: float  # 综合评分 (0-100)
    grade: str  # 质量等级 (优、良、中、差)
    individual_scores: Dict[str, float]  # 各项指标得分
    improvement_suggestions: list  # 改进建议列表
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'total_score': self.total_score,
            'grade': self.grade,
            'individual_scores': self.individual_scores,
            'improvement_suggestions': self.improvement_suggestions,
        }


class BaseAnalyzer(ABC):
    """
    分析器基类
    所有具体分析器都继承此类
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化分析器
        
        Args:
            config: 配置参数字典
        """
        self.config = config or {}
        self.logger = logging.getLogger(self.__class__.__name__)
        
    @abstractmethod
    def analyze(self, point_cloud: np.ndarray) -> Any:
        """
        执行分析（抽象方法，子类必须实现）
        
        Args:
            point_cloud: 点云数据，形状为 (N, 3)
            
        Returns:
            分析结果对象
        """
        pass
    
    def validate_input(self, point_cloud: np.ndarray) -> bool:
        """
        验证输入数据
        
        Args:
            point_cloud: 点云数据
            
        Returns:
            是否有效
        """
        if not isinstance(point_cloud, np.ndarray):
            self.logger.error("输入必须是NumPy数组")
            return False
            
        if point_cloud.ndim != 2 or point_cloud.shape[1] != 3:
            self.logger.error(f"点云形状必须为(N, 3)，当前形状: {point_cloud.shape}")
            return False
            
        if point_cloud.shape[0] < 100:
            self.logger.warning(f"点云数量较少: {point_cloud.shape[0]}")
            
        return True
    
    def handle_error(self, error: Exception, context: str = "") -> None:
        """
        错误处理
        
        Args:
            error: 异常对象
            context: 错误上下文信息
        """
        error_msg = f"{context}: {str(error)}" if context else str(error)
        self.logger.error(error_msg, exc_info=True)
        
    def log_result(self, result: Any) -> None:
        """
        记录分析结果
        
        Args:
            result: 分析结果对象
        """
        if hasattr(result, 'to_dict'):
            self.logger.info(f"分析结果: {result.to_dict()}")
        else:
            self.logger.info(f"分析结果: {result}")
    
    def normalize_point_cloud(self, point_cloud: np.ndarray) -> np.ndarray:
        """
        归一化点云（平移到原点）
        
        Args:
            point_cloud: 原始点云
            
        Returns:
            归一化后的点云
        """
        centroid = np.mean(point_cloud, axis=0)
        return point_cloud - centroid
    
    def compute_pca(self, point_cloud: np.ndarray) -> tuple:
        """
        计算主成分分析
        
        Args:
            point_cloud: 点云数据
            
        Returns:
            (特征值, 特征向量)
        """
        # 归一化
        normalized = self.normalize_point_cloud(point_cloud)
        
        # 计算协方差矩阵
        cov_matrix = np.cov(normalized.T)
        
        # 特征值分解
        eigenvalues, eigenvectors = np.linalg.eigh(cov_matrix)
        
        # 按特征值降序排列
        idx = np.argsort(eigenvalues)[::-1]
        eigenvalues = eigenvalues[idx]
        eigenvectors = eigenvectors[:, idx]
        
        return eigenvalues, eigenvectors
