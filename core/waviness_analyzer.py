"""
HRG谐振陀螺加工精度分析系统 - 波纹度分析器
版本: v4.1
符合GB/T 3505-2009标准第3.1.7条（λf+λc两级滤波+标称形状去除）
"""

import numpy as np
from typing import Optional, Dict, Any, Tuple
try:
    from .base_analyzer import BaseAnalyzer, WavinessResult
except ImportError:
    from base_analyzer import BaseAnalyzer, WavinessResult


class WavinessAnalyzer(BaseAnalyzer):
    """
    波纹度分析器
    GB/T 3505-2009 第3.1.7条: 使用λf和λc两个轮廓滤波器分离波纹度成分
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化波纹度分析器

        Args:
            config: 配置参数，包含：
                - lambda_f: 长波截止波长 (mm), GB/T 3505-2009 3.1.7
                - lambda_c: 短波截止波长 (mm), GB/T 3505-2009 3.1.7
        """
        super().__init__(config)

        self.lambda_f = self.config.get('lambda_f', 8.0)
        self.lambda_c = self.config.get('lambda_c', 2.5)

        if self.lambda_f <= self.lambda_c:
            raise ValueError(
                f"λf({self.lambda_f})必须大于λc({self.lambda_c})"
            )

    def analyze(self, point_cloud: np.ndarray) -> WavinessResult:
        """
        执行波纹度分析

        Args:
            point_cloud: 点云数据 (N, 3)

        Returns:
            WavinessResult对象
        """
        if not self.validate_input(point_cloud):
            raise ValueError("无效的点云数据")

        self.logger.info("开始波纹度分析...")

        try:
            profile = self._extract_profile(point_cloud)

            waviness_profile, nominal_removed = self._separate_waviness(
                profile, self.lambda_f, self.lambda_c
            )

            amplitude = self._compute_amplitude(waviness_profile)

            result = WavinessResult(
                waviness_amplitude=amplitude,
                waviness_profile=waviness_profile,
                lambda_f=self.lambda_f,
                lambda_c=self.lambda_c,
                nominal_shape_removed=nominal_removed,
            )

            self.log_result(result)
            return result

        except Exception as e:
            self.handle_error(e, "波纹度分析失败")
            raise

    def _extract_profile(self, point_cloud: np.ndarray) -> np.ndarray:
        """提取轮廓曲线"""
        normalized = self.normalize_point_cloud(point_cloud)
        r = np.sqrt(normalized[:, 0]**2 + normalized[:, 1]**2)
        z = normalized[:, 2]
        idx = np.argsort(r)
        return np.column_stack([r[idx], z[idx]])

    def _remove_nominal_shape(self, profile: np.ndarray) -> Tuple[np.ndarray, bool]:
        """
        去除标称形状
        GB/T 3505-2009 第3.1.7注1: 在用λf滤波器分离波纹度轮廓以前，
        应首先用最小二乘法的最佳拟合从总轮廓中提取标称的形状，
        并将形状成分从总轮廓中去除

        Args:
            profile: 原始轮廓 (N, 2)

        Returns:
            (残差轮廓, 是否成功去除标称形状)
        """
        x = profile[:, 0]
        y = profile[:, 1]

        try:
            A = np.column_stack([x, np.ones(len(x))])
            coeffs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
            y_nominal = A @ coeffs
            y_residual = y - y_nominal
            return np.column_stack([x, y_residual]), True
        except Exception as e:
            self.logger.warning(f"标称形状去除失败: {e}，使用原始轮廓")
            return profile, False

    def _separate_waviness(self, profile: np.ndarray,
                            lambda_f: float,
                            lambda_c: float) -> Tuple[np.ndarray, bool]:
        """
        两级滤波分离波纹度成分
        GB/T 3505-2009 第3.1.7条:
        1) 去除标称形状（最小二乘法拟合）
        2) λf轮廓滤波器抑制长波成分
        3) λc轮廓滤波器抑制短波成分
        波纹度轮廓在λf~λc波长范围内

        Args:
            profile: 原始轮廓 (N, 2)
            lambda_f: 长波截止波长 (mm)
            lambda_c: 短波截止波长 (mm)

        Returns:
            (波纹度轮廓, 是否成功去除标称形状)
        """
        if lambda_f <= lambda_c:
            raise ValueError(f"λf({lambda_f})必须大于λc({lambda_c})")

        residual_profile, nominal_removed = self._remove_nominal_shape(profile)

        x = residual_profile[:, 0]
        y = residual_profile[:, 1]
        dx = x[1] - x[0]

        sigma_f = lambda_f / (2 * np.pi)
        y_lowcut = self._gaussian_lowpass(y, sigma_f, dx)

        sigma_c = lambda_c / (2 * np.pi)
        y_highcut = self._gaussian_lowpass(y_lowcut, sigma_c, dx)

        waviness = y_lowcut - y_highcut

        return np.column_stack([x, waviness]), nominal_removed

    def _gaussian_lowpass(self, y: np.ndarray, sigma: float,
                           dx: float) -> np.ndarray:
        """高斯低通滤波器（GB/T 18777-2002 相位修正滤波器近似）"""
        n = len(y)
        x_kernel = np.arange(-n // 2, n // 2) * dx
        kernel = np.exp(-x_kernel**2 / (2 * sigma**2))
        kernel = kernel / kernel.sum()
        y_fft = np.fft.fft(y)
        kernel_fft = np.fft.fft(kernel, n)
        return np.fft.ifft(y_fft * kernel_fft).real

    def _compute_amplitude(self, waviness_profile: np.ndarray) -> float:
        """计算波纹度幅值"""
        y = waviness_profile[:, 1]
        amplitude = (np.max(y) - np.min(y)) / 2
        return float(amplitude * 1000)
