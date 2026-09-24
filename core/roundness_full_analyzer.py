"""
GB/T 7235-2004 圆度误差评定 - 半径变化量测量
支持4种评定方法: MZC(最小区域圆), LSC(最小二乘圆), MCC(最小外接圆), MLC(最大内接圆)
支持滤波器频率响应: 1~15upr, 1~50upr(默认), 1~150upr, 1~500upr, 1~1500upr
"""

import numpy as np
from typing import Optional, Dict, Any
from dataclasses import dataclass
from scipy.optimize import minimize
try:
    from .base_analyzer import BaseAnalyzer
except ImportError:
    from base_analyzer import BaseAnalyzer


@dataclass
class RoundnessFullResult:
    """圆度完整评定结果 (GB/T 7235-2004)"""
    mzc_error: float = 0.0   # 最小区域圆法 um
    lsc_error: float = 0.0   # 最小二乘圆法 um
    mcc_error: float = 0.0   # 最小外接圆法 um
    mlc_error: float = 0.0   # 最大内接圆法 um
    lsc_center: Optional[np.ndarray] = None
    lsc_radius: float = 0.0
    mzc_center: Optional[np.ndarray] = None
    mzc_radius: float = 0.0
    upr_range: str = "1-50"

    def to_dict(self) -> Dict[str, Any]:
        result = {
            'MZC_error': self.mzc_error,
            'LSC_error': self.lsc_error,
            'MCC_error': self.mcc_error,
            'MLC_error': self.mlc_error,
            'LSC_radius': self.lsc_radius,
            'MZC_radius': self.mzc_radius,
            'upr_range': self.upr_range,
        }
        if self.lsc_center is not None:
            result['LSC_center'] = self.lsc_center.tolist()
        if self.mzc_center is not None:
            result['MZC_center'] = self.mzc_center.tolist()
        return result


class RoundnessFullAnalyzer(BaseAnalyzer):
    """
    圆度完整评定分析器 (GB/T 7235-2004)
    支持MZC, LSC, MCC, MLC四种评定方法
    支持upr滤波器频率响应范围
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.upr_range = self.config.get('upr_range', '1-50')

    def analyze(self, point_cloud: np.ndarray) -> RoundnessFullResult:
        if not self.validate_input(point_cloud):
            raise ValueError("Invalid point cloud")

        self.logger.info("开始圆度完整评定 (GB/T 7235-2004)...")

        # 提取2D轮廓 (XY平面投影)
        xy = point_cloud[:, :2]

        result = RoundnessFullResult(upr_range=self.upr_range)

        # 1. LSC - 最小二乘圆 (默认方法)
        cx, cy, r = self._fit_lsc(xy)
        result.lsc_center = np.array([cx, cy])
        result.lsc_radius = r * 1000  # mm -> um for radius
        devs = np.sqrt((xy[:, 0] - cx)**2 + (xy[:, 1] - cy)**2) - r
        result.lsc_error = float((np.max(devs) - np.min(devs)) * 1000)  # mm -> um
        self.logger.info(f"LSC: error={result.lsc_error:.3f}um, R={result.lsc_radius:.3f}mm")

        # 2. MZC - 最小区域圆
        cx_mz, cy_mz, r_mz = self._fit_mzc(xy)
        result.mzc_center = np.array([cx_mz, cy_mz])
        result.mzc_radius = r_mz * 1000
        devs_mz = np.sqrt((xy[:, 0] - cx_mz)**2 + (xy[:, 1] - cy_mz)**2) - r_mz
        result.mzc_error = float((np.max(devs_mz) - np.min(devs_mz)) * 1000)
        self.logger.info(f"MZC: error={result.mzc_error:.3f}um")

        # 3. MCC - 最小外接圆
        result.mcc_error = self._fit_mcc(xy) * 1000
        self.logger.info(f"MCC: error={result.mcc_error:.3f}um")

        # 4. MLC - 最大内接圆
        result.mlc_error = self._fit_mlc(xy) * 1000
        self.logger.info(f"MLC: error={result.mlc_error:.3f}um")

        return result

    def _fit_lsc(self, points: np.ndarray):
        """最小二乘圆 (LSC) - 代数拟合"""
        x, y = points[:, 0], points[:, 1]
        n = len(x)
        # 最小二乘圆: (x-a)^2 + (y-b)^2 = R^2
        # 展开: x^2 + y^2 - 2ax - 2by + (a^2+b^2-R^2) = 0
        A = np.column_stack([x, y, np.ones(n)])
        b = -(x**2 + y**2)
        params, _, _, _ = np.linalg.lstsq(A, b, rcond=None)
        a, b_coef, c = params
        cx, cy = -a / 2, -b_coef / 2
        r = np.sqrt(cx**2 + cy**2 - c)
        return cx, cy, r

    def _fit_mzc(self, points: np.ndarray):
        """最小区域圆 (MZC) - 优化法"""
        cx0, cy0, r0 = self._fit_lsc(points)

        def objective(params):
            cx, cy = params
            dists = np.sqrt((points[:, 0] - cx)**2 + (points[:, 1] - cy)**2)
            return np.max(dists) - np.min(dists)

        res = minimize(objective, [cx0, cy0], method='Nelder-Mead',
                      options={'xatol': 1e-12, 'fatol': 1e-14, 'maxiter': 10000})
        cx, cy = res.x
        dists = np.sqrt((points[:, 0] - cx)**2 + (points[:, 1] - cy)**2)
        r = (np.max(dists) + np.min(dists)) / 2
        return cx, cy, r

    def _fit_mcc(self, points: np.ndarray):
        """最小外接圆 (MCC) - 返回圆度误差(mm)

        MCC: 所有点在圆内或圆上，最小化外接圆半径R。
        圆度误差 = R - r, 其中r是距圆心最近点距离。
        约束用惩罚项实现: 若最远点距离 > R 则加大惩罚。
        等效: 最小化 max(dists) 即外接半径, 圆度误差 = max(dists) - min(dists)。
        """
        cx0, cy0, _ = self._fit_lsc(points)

        def objective(params):
            cx, cy = params
            dists = np.sqrt((points[:, 0] - cx)**2 + (points[:, 1] - cy)**2)
            R = np.max(dists)
            r = np.min(dists)
            return R

        res = minimize(objective, [cx0, cy0], method='Nelder-Mead',
                      options={'xatol': 1e-12, 'fatol': 1e-14, 'maxiter': 10000})
        cx, cy = res.x
        dists = np.sqrt((points[:, 0] - cx)**2 + (points[:, 1] - cy)**2)
        return np.max(dists) - np.min(dists)

    def _fit_mlc(self, points: np.ndarray):
        """最大内接圆 (MLC) - 返回圆度误差(mm)

        MLC: 所有点在圆外或圆上，最大化内接圆半径r。
        圆度误差 = R - r, 其中R是距圆心最远点距离。
        等效: 最大化 min(dists) 即内接半径 -> 最小化 -min(dists)。
        """
        cx0, cy0, _ = self._fit_lsc(points)

        def objective(params):
            cx, cy = params
            dists = np.sqrt((points[:, 0] - cx)**2 + (points[:, 1] - cy)**2)
            return -np.min(dists)

        res = minimize(objective, [cx0, cy0], method='Nelder-Mead',
                      options={'xatol': 1e-12, 'fatol': 1e-14, 'maxiter': 10000})
        cx, cy = res.x
        dists = np.sqrt((points[:, 0] - cx)**2 + (points[:, 1] - cy)**2)
        return np.max(dists) - np.min(dists)

    def filter_by_upr(self, theta: np.ndarray, rho: np.ndarray,
                      upr_min: int = 1, upr_max: int = 50):
        """按upr范围滤波 (GB/T 7235-2004)"""
        N = len(theta)
        # FFT
        R = np.fft.fft(rho)
        freqs = np.fft.fftfreq(N, d=1.0/N)  # 波数/转 (upr)
        # 滤波
        mask = (np.abs(freqs) >= upr_min) & (np.abs(freqs) <= upr_max)
        R_filtered = np.zeros_like(R)
        R_filtered[0] = R[0]  # DC分量
        R_filtered[mask] = R[mask]
        rho_filtered = np.fft.ifft(R_filtered).real
        return rho_filtered
