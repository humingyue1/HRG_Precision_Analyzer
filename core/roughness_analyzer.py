"""
HRG谐振陀螺加工精度分析系统 - 表面粗糙度分析器
版本: v4.1
符合GB/T 3505-2009标准（轮廓最大高度Rz定义）
符合GB/T 6062-2009标准（λs/λc双滤波器传输特性）
"""

import numpy as np
import warnings
from scipy import signal
from typing import Optional, Dict, Any, List
try:
    from .base_analyzer import BaseAnalyzer, RoughnessResult
except ImportError:
    from base_analyzer import BaseAnalyzer, RoughnessResult


class RoughnessAnalyzer(BaseAnalyzer):
    """
    表面粗糙度分析器
    实现Ra、Rq、Rz、RSm参数计算
    GB/T 3505-2009: Rz为轮廓最大高度(Rp+Rv)，非旧版十点高度
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.sampling_length = self.config.get('sampling_length', 0.8)
        self.evaluation_length = self.config.get('evaluation_length', 4.0)
        self.cutoff_wavelength = self.config.get('cutoff_wavelength', 0.8)
        self.lambda_s = self.config.get('lambda_s', 0.0025)
        self.lambda_c = self.config.get('lambda_c', 0.8)
        self.use_fft = self.config.get('use_fft', True)

    def analyze(self, point_cloud: np.ndarray) -> RoughnessResult:
        """
        执行表面粗糙度分析
        GB/T 3505-2009: 取样长度内独立计算参数，按国标规则聚合

        Args:
            point_cloud: 点云数据 (N, 3)

        Returns:
            RoughnessResult对象
        """
        if not self.validate_input(point_cloud):
            raise ValueError("无效的点云数据")

        self.logger.info("开始表面粗糙度分析...")

        try:
            profile = self.extract_profile(point_cloud)

            roughness_profile = self.lambda_s_lambda_c_filter(
                profile, self.lambda_s, self.lambda_c
            )

            lr = self.lambda_c
            x = roughness_profile[:, 0]
            total_length = x[-1] - x[0]

            num_sampling = max(1, int(total_length / lr))
            if total_length < lr:
                self.logger.warning(
                    f"评定长度({total_length:.4f}mm)不足一个取样长度({lr:.4f}mm)，使用完整轮廓"
                )
                num_sampling = 1

            per_ra = []
            per_rq = []
            per_rz = []
            per_rsm = []

            for i in range(num_sampling):
                x_start = x[0] + i * lr
                x_end = x_start + lr
                if i == num_sampling - 1:
                    x_end = x[-1]

                mask = (x >= x_start) & (x <= x_end)
                segment = roughness_profile[mask]

                if len(segment) < 10:
                    continue

                ra_seg = self.compute_ra(segment)
                rq_seg = self.compute_rq(segment)
                rz_seg = self.compute_rz(segment)
                rsm_seg = self.compute_rsm(segment, rz_value=rz_seg)

                per_ra.append(ra_seg)
                per_rq.append(rq_seg)
                per_rz.append(rz_seg)
                per_rsm.append(rsm_seg)

            if not per_ra:
                ra = self.compute_ra(roughness_profile)
                rq = self.compute_rq(roughness_profile)
                rz = self.compute_rz(roughness_profile)
                rsm = self.compute_rsm(roughness_profile, rz_value=rz)
                per_rz = [rz]
                per_rsm = [rsm]
            else:
                ra = float(np.mean(per_ra))
                rq = float(np.mean(per_rq))
                rz = float(np.max(per_rz))
                rsm = float(np.mean(per_rsm))

            result = RoughnessResult(
                ra=ra,
                rq=rq,
                rz=rz,
                rsm=rsm,
                profile_data=roughness_profile,
                baseline_data=np.zeros_like(roughness_profile),
                sampling_length=lr,
                num_sampling_lengths=num_sampling,
                per_sampling_rz=per_rz,
                per_sampling_rsm=per_rsm,
                lambda_s=self.lambda_s,
                lambda_c=self.lambda_c,
            )

            self.log_result(result)
            return result

        except Exception as e:
            self.handle_error(e, "表面粗糙度分析失败")
            raise

    def extract_profile(self, point_cloud: np.ndarray,
                       direction: str = 'radial') -> np.ndarray:
        """从3D点云提取2D轮廓曲线"""
        normalized = self.normalize_point_cloud(point_cloud)

        if direction == 'radial':
            r = np.sqrt(normalized[:, 0]**2 + normalized[:, 1]**2)
            z = normalized[:, 2]
            idx = np.argsort(r)
            profile = np.column_stack([r[idx], z[idx]])

        elif direction == 'axial':
            z = normalized[:, 2]
            r = np.sqrt(normalized[:, 0]**2 + normalized[:, 1]**2)
            idx = np.argsort(z)
            profile = np.column_stack([z[idx], r[idx]])

        else:
            r = np.sqrt(normalized[:, 0]**2 + normalized[:, 1]**2)
            mean_r = np.mean(r)
            mask = np.abs(r - mean_r) < 0.1 * mean_r
            selected = normalized[mask]
            theta = np.arctan2(selected[:, 1], selected[:, 0])
            z = selected[:, 2]
            idx = np.argsort(theta)
            profile = np.column_stack([theta[idx], z[idx]])

        profile = self.resample_profile(profile)
        return profile

    def resample_profile(self, profile: np.ndarray,
                        num_points: int = 10000) -> np.ndarray:
        """重采样轮廓到均匀间隔"""
        x = profile[:, 0]
        y = profile[:, 1]
        x_new = np.linspace(x.min(), x.max(), num_points)
        y_new = np.interp(x_new, x, y)
        return np.column_stack([x_new, y_new])

    def lambda_s_lambda_c_filter(self, profile: np.ndarray,
                                  lambda_s: float = 0.0025,
                                  lambda_c: float = 0.8) -> np.ndarray:
        """
        λs/λc双级高斯滤波器
        GB/T 6062-2009 第3.1.4条/3.1.6条, GB/T 18777-2002

        流程: 原始信号 → λs滤波器(抑制短波噪声) → λc滤波器(抑制长波成分)
              → 粗糙度轮廓 = λs输出 - λc长波成分
        传输频带: λs ~ λc，截止波长处传输率50% (GB/T 18777-2002)

        Args:
            profile: 原始轮廓 (N, 2)
            lambda_s: 短波截止波长 (mm)
            lambda_c: 长波截止波长 (mm)

        Returns:
            粗糙度轮廓 (N, 2)
        """
        if lambda_s >= lambda_c:
            raise ValueError(f"λs({lambda_s})必须小于λc({lambda_c})")

        ratio = lambda_c / lambda_s
        if ratio not in [100, 300]:
            if ratio < 50 or ratio > 1000:
                self.logger.warning(
                    f"λc/λs比例{ratio:.0f}不在常用范围{{100,300}}附近，请确认"
                )

        x = profile[:, 0]
        y = profile[:, 1]
        dx = x[1] - x[0]

        sigma_s = lambda_s / (2 * np.pi)
        y_primary = self._gaussian_lowpass(y, sigma_s, dx)

        sigma_c = lambda_c / (2 * np.pi)
        y_roughness_mean = self._gaussian_lowpass(y_primary, sigma_c, dx)

        roughness = y_primary - y_roughness_mean

        return np.column_stack([x, roughness])

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

    def gaussian_filter(self, profile: np.ndarray) -> np.ndarray:
        """
        [已废弃] 单级高斯滤波器，请使用 lambda_s_lambda_c_filter
        GB/T 6062-2009 要求双级滤波器(λs+λc)
        保留此方法以保持向后兼容
        """
        warnings.warn(
            "gaussian_filter已废弃，请使用lambda_s_lambda_c_filter。"
            "GB/T 6062-2009要求λs/λc双级滤波器。",
            DeprecationWarning,
            stacklevel=2
        )
        return self.lambda_s_lambda_c_filter(profile, self.lambda_s, self.lambda_c)

    def compute_ra(self, profile: np.ndarray) -> float:
        """
        计算轮廓算术平均偏差 Ra
        GB/T 3505-2009 第4.2.1条: Ra = (1/l) * ∫|Z(x)|dx

        Args:
            profile: 粗糙度轮廓 (N, 2)

        Returns:
            Ra值 (μm)
        """
        x = profile[:, 0]
        y = profile[:, 1]
        l = x[-1] - x[0]
        if l <= 0:
            return 0.0
        ra = np.trapz(np.abs(y), x) / l
        return float(ra * 1000)

    def compute_rq(self, profile: np.ndarray) -> float:
        """
        计算轮廓均方根偏差 Rq
        GB/T 3505-2009 第4.2.2条: Rq = sqrt((1/l) * ∫Z²(x)dx)

        Args:
            profile: 粗糙度轮廓 (N, 2)

        Returns:
            Rq值 (μm)
        """
        x = profile[:, 0]
        y = profile[:, 1]
        l = x[-1] - x[0]
        if l <= 0:
            return 0.0
        rq_squared = np.trapz(y**2, x) / l
        rq = np.sqrt(max(rq_squared, 0))
        return float(rq * 1000)

    def compute_rz(self, profile: np.ndarray) -> float:
        """
        计算轮廓最大高度 Rz
        GB/T 3505-2009 第4.1.3条:
        Rz = 在一个取样长度内，最大轮廓峰高(Rp)与最大轮廓谷深(Rv)之和
        即 Rz = Rp + Rv

        注: GB/T 3505-1983中Rz曾表示"十点高度"，2009版已修正为"轮廓最大高度"

        Args:
            profile: 粗糙度轮廓 (N, 2)

        Returns:
            Rz值 (μm)
        """
        y = profile[:, 1]
        rp = np.max(y)
        rv = np.abs(np.min(y))
        rz = rp + rv
        return float(rz * 1000)

    def compute_rsm(self, profile: np.ndarray,
                     rz_value: Optional[float] = None,
                     height_resolution_ratio: float = 0.1,
                     spacing_resolution_ratio: float = 0.01) -> float:
        """
        计算轮廓单元的平均宽度 RSm
        GB/T 3505-2009 第4.3.1条: RSm = (1/m) * ∑Xsi
        其中Xsi为轮廓单元宽度（峰+谷组合为一个轮廓单元）

        分辨力判据（GB/T 3505-2009 第4.3.1注）:
        - 高度分辨力: 缺省按Rz的10%选取
        - 水平间距分辨力: 缺省按取样长度的1%选取

        Args:
            profile: 粗糙度轮廓 (N, 2)
            rz_value: Rz值(用于高度分辨力判据)，若None则自行计算
            height_resolution_ratio: 高度分辨力比例(默认0.1，即10%×Rz)
            spacing_resolution_ratio: 间距分辨力比例(默认0.01，即1%×lr)

        Returns:
            RSm值 (mm)
        """
        x = profile[:, 0]
        y = profile[:, 1]

        if rz_value is None:
            rz_value = self.compute_rz(profile) / 1000.0

        sampling_length = x[-1] - x[0]
        height_threshold = height_resolution_ratio * rz_value if rz_value > 0 else 1e-10
        spacing_threshold = spacing_resolution_ratio * sampling_length

        zero_crossings = []
        for i in range(len(y) - 1):
            if y[i] * y[i + 1] < 0:
                x_cross = x[i] - y[i] * (x[i + 1] - x[i]) / (y[i + 1] - y[i])
                zero_crossings.append(x_cross)
            elif y[i] == 0 and y[i + 1] != 0:
                zero_crossings.append(x[i])

        if len(zero_crossings) < 2:
            self.logger.warning("轮廓与中线交点不足，无法计算RSm")
            return 0.0

        element_widths = []
        for i in range(len(zero_crossings) - 1):
            width = zero_crossings[i + 1] - zero_crossings[i]

            start_idx = np.searchsorted(x, zero_crossings[i])
            end_idx = np.searchsorted(x, zero_crossings[i + 1])
            start_idx = min(start_idx, len(y) - 1)
            end_idx = min(end_idx, len(y) - 1)

            segment_y = y[start_idx:end_idx + 1]
            if len(segment_y) < 2:
                continue

            element_height = np.max(segment_y) - np.min(segment_y)

            if element_height >= height_threshold and width >= spacing_threshold:
                element_widths.append(width)

        if not element_widths:
            self.logger.warning("无有效轮廓单元，RSm=0")
            return 0.0

        rsm = float(np.mean(element_widths))
        return rsm
