"""
GB/T 6062-2009 接触(触针)式仪器的标称特性
实现高斯相位修正滤波器, lambda_s/lambda_c轮廓滤波器
截止波长标称值系列: 0.08, 0.25, 0.8, 2.5, 8.0 mm
"""

import numpy as np
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass
try:
    from .base_analyzer import BaseAnalyzer
except ImportError:
    from base_analyzer import BaseAnalyzer


# GB/T 6062-2009 表1: lambda_c, lambda_s, 针尖半径关系
FILTER_TABLE = {
    0.08:  {'lambda_s': 0.0025, 'ratio': 30,  'r_tp_max': 2,  'max_sampling_interval': 0.0005},
    0.25:  {'lambda_s': 0.0025, 'ratio': 100, 'r_tp_max': 2,  'max_sampling_interval': 0.0005},
    0.8:   {'lambda_s': 0.0025, 'ratio': 300, 'r_tp_max': 2,  'max_sampling_interval': 0.0005},
    2.5:   {'lambda_s': 0.008,  'ratio': 300, 'r_tp_max': 5,  'max_sampling_interval': 0.0015},
    8.0:   {'lambda_s': 0.025,  'ratio': 300, 'r_tp_max': 10, 'max_sampling_interval': 0.005},
}


@dataclass
class ProfileFilterResult:
    """轮廓滤波结果"""
    raw_profile: Optional[np.ndarray] = None       # 原始轮廓
    lambda_s_profile: Optional[np.ndarray] = None   # lambda_s滤波后 (原始轮廓)
    roughness_profile: Optional[np.ndarray] = None   # 粗糙度轮廓
    waviness_profile: Optional[np.ndarray] = None    # 波纹度轮廓
    lambda_c: float = 0.8   # mm
    lambda_s: float = 0.0025  # mm
    r_tp_max: int = 2  # um

    def to_dict(self) -> Dict[str, Any]:
        result = {
            'lambda_c': self.lambda_c,
            'lambda_s': self.lambda_s,
            'r_tp_max': self.r_tp_max,
        }
        if self.roughness_profile is not None:
            result['roughness_rms'] = float(np.sqrt(np.mean(self.roughness_profile[:, 1]**2)))
        if self.waviness_profile is not None:
            result['waviness_rms'] = float(np.sqrt(np.mean(self.waviness_profile[:, 1]**2)))
        return result


class ProfileFilterAnalyzer(BaseAnalyzer):
    """
    轮廓滤波器 (GB/T 6062-2009)
    高斯相位修正滤波器, lambda_s和lambda_c滤波
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.lambda_c = self.config.get('lambda_c', 0.8)  # mm
        self.lambda_s = self.config.get('lambda_s', None)  # 自动根据表1

        # 根据GB/T 6062-2009表1确定参数
        lc = self.lambda_c
        if lc in FILTER_TABLE:
            table = FILTER_TABLE[lc]
            if self.lambda_s is None:
                self.lambda_s = table['lambda_s']
            self.r_tp_max = table['r_tp_max']
            self.max_sampling_interval = table['max_sampling_interval']
        else:
            # 找最接近的标准值
            standard_values = sorted(FILTER_TABLE.keys())
            closest = min(standard_values, key=lambda x: abs(x - lc))
            table = FILTER_TABLE[closest]
            if self.lambda_s is None:
                self.lambda_s = table['lambda_s']
            self.r_tp_max = table['r_tp_max']
            self.max_sampling_interval = table['max_sampling_interval']
            self.logger.warning(f"lambda_c={lc}非标准值, 使用最接近的标准值{closest}mm的参数")

    def analyze(self, point_cloud: np.ndarray) -> ProfileFilterResult:
        if not self.validate_input(point_cloud):
            raise ValueError("Invalid point cloud")

        self.logger.info(f"轮廓滤波 (GB/T 6062-2009): lambda_c={self.lambda_c}mm, "
                        f"lambda_s={self.lambda_s}mm, r_tp_max={self.r_tp_max}um")

        # 提取轮廓
        profile = self._extract_profile(point_cloud)

        result = ProfileFilterResult(
            raw_profile=profile,
            lambda_c=self.lambda_c,
            lambda_s=self.lambda_s,
            r_tp_max=self.r_tp_max
        )

        # lambda_s滤波 (短波抑制)
        result.lambda_s_profile = self._gaussian_filter(profile, self.lambda_s)

        # lambda_c滤波 (粗糙度/波纹度分离)
        result.waviness_profile = self._gaussian_filter(result.lambda_s_profile, self.lambda_c)

        # 粗糙度轮廓 = lambda_s滤波后 - 波纹度轮廓
        result.roughness_profile = result.lambda_s_profile.copy()
        result.roughness_profile[:, 1] = result.lambda_s_profile[:, 1] - result.waviness_profile[:, 1]

        return result

    def _extract_profile(self, points: np.ndarray) -> np.ndarray:
        """提取径向轮廓"""
        normalized = self.normalize_point_cloud(points)
        r = np.sqrt(normalized[:, 0]**2 + normalized[:, 1]**2)
        z = normalized[:, 2]
        idx = np.argsort(r)
        profile = np.column_stack([r[idx], z[idx]])
        # 重采样
        n = min(10000, len(profile))
        x_new = np.linspace(profile[:, 0].min(), profile[:, 0].max(), n)
        y_new = np.interp(x_new, profile[:, 0], profile[:, 1])
        return np.column_stack([x_new, y_new])

    def _gaussian_filter(self, profile: np.ndarray, cutoff: float) -> np.ndarray:
        """高斯相位修正滤波器 (GB/T 18777 / ISO 11562)"""
        x, y = profile[:, 0], profile[:, 1]
        dx = x[1] - x[0]
        sigma = cutoff / (2 * np.pi)

        # FFT卷积
        n = len(y)
        x_kernel = np.arange(-n // 2, n // 2) * dx
        kernel = np.exp(-x_kernel**2 / (2 * sigma**2))
        kernel = kernel / kernel.sum()

        y_fft = np.fft.fft(y)
        kernel_fft = np.fft.fft(kernel, n)
        y_filtered = np.fft.ifft(y_fft * kernel_fft).real

        return np.column_stack([x, y_filtered])
