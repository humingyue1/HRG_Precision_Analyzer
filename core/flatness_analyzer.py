"""
GB/T 24630.1-2024 & GB/T 24630.2-2024 平面度分析
支持最小区域参考平面(MZPL)和最小二乘参考平面(LSPL)
参数: FLTt(峰-谷), FLTp(峰值), FLTv(谷值), FLTq(均方根)
"""

import numpy as np
from typing import Optional, Dict, Any
from dataclasses import dataclass
try:
    from .base_analyzer import BaseAnalyzer
except ImportError:
    from base_analyzer import BaseAnalyzer


@dataclass
class FlatnessResult:
    """平面度分析结果 (GB/T 24630.1-2024)"""
    flt_t_mz: float = 0.0   # 峰-谷平面度偏差 (MZPL) mm
    flt_t_ls: float = 0.0   # 峰-谷平面度偏差 (LSPL) mm
    flt_p: float = 0.0      # 峰值平面度偏差 (LSPL) mm
    flt_v: float = 0.0      # 谷值平面度偏差 (LSPL) mm
    flt_q: float = 0.0      # 均方根平面度偏差 (LSPL) mm
    lspl_normal: Optional[np.ndarray] = None  # LSPL法向量
    lspl_center: Optional[np.ndarray] = None  # LSPL中心点
    mzpl_normal: Optional[np.ndarray] = None  # MZPL法向量

    def to_dict(self) -> Dict[str, Any]:
        result = {
            'FLTt_MZPL': self.flt_t_mz,
            'FLTt_LSPL': self.flt_t_ls,
            'FLTp_LSPL': self.flt_p,
            'FLTv_LSPL': self.flt_v,
            'FLTq_LSPL': self.flt_q,
        }
        if self.lspl_normal is not None:
            result['LSPL_normal'] = self.lspl_normal.tolist()
        if self.lspl_center is not None:
            result['LSPL_center'] = self.lspl_center.tolist()
        return result


class FlatnessAnalyzer(BaseAnalyzer):
    """
    平面度分析器
    GB/T 24630.1-2024: 词汇和参数
    GB/T 24630.2-2024: 规范操作集
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.method = self.config.get('method', 'both')  # 'lspl', 'mzpl', 'both'

    def analyze(self, point_cloud: np.ndarray) -> FlatnessResult:
        if not self.validate_input(point_cloud):
            raise ValueError("Invalid point cloud")

        self.logger.info("开始平面度分析 (GB/T 24630.1-2024)...")

        result = FlatnessResult()

        # LSPL - 最小二乘参考平面
        if self.method in ('lspl', 'both'):
            normal, center = self._fit_lspl(point_cloud)
            deviations = self._compute_deviations(point_cloud, normal, center)

            result.lspl_normal = normal
            result.lspl_center = center
            result.flt_p = float(np.max(deviations)) * 1000  # mm -> um
            result.flt_v = float(-np.min(deviations)) * 1000
            result.flt_t_ls = float(np.max(deviations) - np.min(deviations)) * 1000
            result.flt_q = float(np.sqrt(np.mean(deviations**2))) * 1000

            self.logger.info(f"LSPL: FLTt={result.flt_t_ls:.3f}um, FLTp={result.flt_p:.3f}um, "
                           f"FLTv={result.flt_v:.3f}um, FLTq={result.flt_q:.3f}um")

        # MZPL - 最小区域参考平面
        if self.method in ('mzpl', 'both'):
            normal_mz, d1, d2 = self._fit_mzpl(point_cloud)
            result.mzpl_normal = normal_mz
            result.flt_t_mz = float(abs(d2 - d1)) * 1000  # mm -> um

            self.logger.info(f"MZPL: FLTt={result.flt_t_mz:.3f}um")

        return result

    def _fit_lspl(self, points: np.ndarray):
        """最小二乘参考平面 (LSPL)"""
        # 平面方程: n0*x + n1*y + n2*z = d
        # 使用SVD拟合
        centroid = np.mean(points, axis=0)
        centered = points - centroid
        U, S, Vt = np.linalg.svd(centered, full_matrices=False)
        normal = Vt[2]  # 最小奇异值对应的左奇异向量
        # 确保法向量指向z正方向
        if normal[2] < 0:
            normal = -normal
        return normal, centroid

    def _compute_deviations(self, points: np.ndarray, normal: np.ndarray,
                           center: np.ndarray) -> np.ndarray:
        """计算各点到参考平面的法向偏差"""
        return (points - center) @ normal

    def _fit_mzpl(self, points: np.ndarray):
        """最小区域参考平面 (MZPL) - 使用旋转搜索法"""
        # 先用LSPL作为初始估计
        normal_ls, center_ls = self._fit_lspl(points)
        deviations_ls = self._compute_deviations(points, normal_ls, center_ls)
        t_ls = np.max(deviations_ls) - np.min(deviations_ls)

        # 使用单纯形法优化法向量使峰-谷值最小
        from scipy.optimize import minimize

        def objective(params):
            # 参数化法向量: (theta, phi) -> (sin(phi)*cos(theta), sin(phi)*sin(theta), cos(phi))
            theta, phi = params
            n = np.array([np.sin(phi)*np.cos(theta),
                         np.sin(phi)*np.sin(theta),
                         np.cos(phi)])
            c = np.mean(points, axis=0)
            devs = (points - c) @ n
            return np.max(devs) - np.min(devs)

        # 初始角度
        phi0 = np.arccos(normal_ls[2])
        theta0 = np.arctan2(normal_ls[1], normal_ls[0])
        x0 = [theta0, phi0]

        res = minimize(objective, x0, method='Nelder-Mead',
                      options={'xatol': 1e-10, 'fatol': 1e-12, 'maxiter': 5000})

        theta_opt, phi_opt = res.x
        normal_mz = np.array([np.sin(phi_opt)*np.cos(theta_opt),
                              np.sin(phi_opt)*np.sin(theta_opt),
                              np.cos(phi_opt)])
        if normal_mz[2] < 0:
            normal_mz = -normal_mz

        center = np.mean(points, axis=0)
        devs = (points - center) @ normal_mz
        d1, d2 = np.min(devs), np.max(devs)

        return normal_mz, d1, d2
