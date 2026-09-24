"""
HRG谐振陀螺加工精度分析系统 - 主分析器
版本: v4.0
"""

import numpy as np
import yaml
import json
from typing import Optional, Dict, Any, Tuple
from pathlib import Path
from dataclasses import dataclass, asdict, field
from collections import namedtuple
import logging
import time
import os

try:
    from .base_analyzer import (
        RoughnessResult, WavinessResult, SymmetryResult,
        ThicknessResult, ResonanceResult, QualityResult
    )
    from .roughness_analyzer import RoughnessAnalyzer
    from .waviness_analyzer import WavinessAnalyzer
    from .symmetry_analyzer import SymmetryAnalyzer
    from .thickness_analyzer import ThicknessAnalyzer
    from .resonance_analyzer import ResonanceAnalyzer
    from .quality_evaluator import QualityEvaluator
    from .flatness_analyzer import FlatnessAnalyzer, FlatnessResult
    from .roundness_full_analyzer import RoundnessFullAnalyzer, RoundnessFullResult
    from .profile_filter_analyzer import ProfileFilterAnalyzer, ProfileFilterResult
    from .tooth_analysis_simple import analyze_tooth_structure, ToothAnalysisResult
except ImportError:
    from base_analyzer import (
        RoughnessResult, WavinessResult, SymmetryResult,
        ThicknessResult, ResonanceResult, QualityResult
    )
    from roughness_analyzer import RoughnessAnalyzer
    from waviness_analyzer import WavinessAnalyzer
    from symmetry_analyzer import SymmetryAnalyzer
    from thickness_analyzer import ThicknessAnalyzer
    from resonance_analyzer import ResonanceAnalyzer
    from quality_evaluator import QualityEvaluator
    from flatness_analyzer import FlatnessAnalyzer, FlatnessResult
    from roundness_full_analyzer import RoundnessFullAnalyzer, RoundnessFullResult
    from profile_filter_analyzer import ProfileFilterAnalyzer, ProfileFilterResult
    from tooth_analysis_simple import analyze_tooth_structure, ToothAnalysisResult


ASCHeaderInfo = namedtuple('ASCHeaderInfo', ['file_format', 'x_size', 'y_size', 'pixel_size', 'header_end_marker'])


@dataclass
class ASCProcessingConfig:
    sample_rate: int = 50
    z_threshold: float = -0.1
    denoise_nb_neighbors: int = 30
    denoise_std_ratio: float = 2.0
    ghost_z_threshold: float = -0.1
    assembly_z_percentile: int = 90
    radius_fallback_percentile: int = 50
    reuse_intermediate: bool = True
    save_intermediate: bool = True


@dataclass
class PrecisionAnalysisResult:
    """综合分析结果"""
    roughness_result: Optional[RoughnessResult] = None
    waviness_result: Optional[WavinessResult] = None
    symmetry_result: Optional[SymmetryResult] = None
    thickness_result: Optional[ThicknessResult] = None
    resonance_result: Optional[ResonanceResult] = None
    quality_result: Optional[QualityResult] = None
    flatness_result: Optional[FlatnessResult] = None         # GB/T 24630
    roundness_full_result: Optional[RoundnessFullResult] = None  # GB/T 7235
    profile_filter_result: Optional[ProfileFilterResult] = None  # GB/T 6062
    tooth_analysis_result: Optional[ToothAnalysisResult] = None  # 齿状结构分析
    analysis_time: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        result = {'analysis_time': self.analysis_time}
        
        if self.roughness_result is not None:
            result['roughness'] = self.roughness_result.to_dict()
        if self.waviness_result is not None:
            result['waviness'] = self.waviness_result.to_dict()
        if self.symmetry_result is not None:
            result['symmetry'] = self.symmetry_result.to_dict()
        if self.thickness_result is not None:
            result['thickness'] = self.thickness_result.to_dict()
        if self.resonance_result is not None:
            result['resonance'] = self.resonance_result.to_dict()
        if self.quality_result is not None:
            result['quality'] = self.quality_result.to_dict()
        if self.flatness_result is not None:
            result['flatness'] = self.flatness_result.to_dict()
        if self.roundness_full_result is not None:
            result['roundness_full'] = self.roundness_full_result.to_dict()
        if self.profile_filter_result is not None:
            result['profile_filter'] = self.profile_filter_result.to_dict()
        if self.tooth_analysis_result is not None:
            result['tooth_analysis'] = self.tooth_analysis_result.to_dict()
        
        return result
    
    def to_json(self, filepath: str) -> None:
        """保存为JSON文件"""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)


class ASCPreprocessor:
    """ASC文件预处理模块 - 步骤1: ASC文件 -> 半球点云"""

    def __init__(self, config: Dict):
        asc_cfg = config.get('asc_processing', {})
        self.sample_rate = asc_cfg.get('sample_rate', 50)
        self.z_threshold = asc_cfg.get('z_threshold', -0.1)
        self.nb_neighbors = asc_cfg.get('denoise_nb_neighbors', 30)
        self.std_ratio = asc_cfg.get('denoise_std_ratio', 2.0)
        self.save_intermediate = asc_cfg.get('save_intermediate', True)
        self.reuse_intermediate = asc_cfg.get('reuse_intermediate', True)
        memory_limit_mb = config.get('performance', {}).get('memory_limit', 500)
        self.memory_limit = memory_limit_mb * 1024 * 1024
        self.logger = logging.getLogger('ASCPreprocessor')

    def _parse_asc_header(self, filepath: str) -> ASCHeaderInfo:
        """解析ASC文件头，提取Format/X Size/Y Size/Pixel_size等参数"""
        x_size = 0
        y_size = 0
        pixel_size = 0.001
        file_format = 1
        header_end_marker = 'RAW_DATA'

        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            first_line = f.readline().strip()
            if 'Format 2' in first_line:
                file_format = 2

            for _ in range(20):
                line = f.readline()
                if not line:
                    break
                line_stripped = line.strip()
                if 'X Size' in line_stripped:
                    parts = line_stripped.split()
                    x_size = int(parts[-1])
                elif 'Y Size' in line_stripped:
                    parts = line_stripped.split()
                    y_size = int(parts[-1])
                elif 'Pixel_size' in line_stripped:
                    parts = line_stripped.split()
                    pixel_size = float(parts[-1])
                elif 'RAW_DATA' in line_stripped:
                    header_end_marker = 'RAW_DATA'
                    break

        if x_size == 0 and y_size == 0 and pixel_size == 0.001:
            if file_format == 1:
                raise ValueError("ASC文件头解析失败: 无法识别文件头格式")

        return ASCHeaderInfo(
            file_format=file_format,
            x_size=x_size,
            y_size=y_size,
            pixel_size=pixel_size,
            header_end_marker=header_end_marker
        )

    def _read_asc_data(self, filepath: str, header_info: ASCHeaderInfo, sample_rate: int) -> np.ndarray:
        """逐行读取ASC数据区，执行Bad/Intensity过滤、Z坐标转换、采样"""
        points_list = []
        count = 0
        skipped_bad = 0
        skipped_short = 0
        skipped_error = 0

        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                if 'RAW_DATA' in line:
                    break

            for line in f:
                count += 1
                line = line.strip()

                if not line:
                    continue
                if 'Bad' in line or 'Intensity' in line:
                    skipped_bad += 1
                    continue

                # BUG-001修复: 采样率过滤（与v3.0逻辑一致）
                if count % sample_rate != 0:
                    continue

                parts = line.split()
                if len(parts) < 3:
                    skipped_short += 1
                    continue

                try:
                    if header_info.file_format == 2:
                        x = float(parts[0])
                        y = float(parts[1])
                        z = float(parts[2]) / 1e6
                    else:
                        ix = int(parts[0])
                        iy = int(parts[1])
                        z_nm = float(parts[2])
                        x = ix * header_info.pixel_size
                        y = iy * header_info.pixel_size
                        z = z_nm / 1e6
                    points_list.append([x, y, z])
                except (ValueError, IndexError):
                    skipped_error += 1
                    continue

                if count % 100000000 == 0:
                    self.logger.info(f"  已读取 {count:,} 行, 提取 {len(points_list):,} 点...")

        if len(points_list) == 0:
            raise ValueError("ASC文件无有效数据点")

        points = np.array(points_list)
        total_skipped = skipped_bad + skipped_short + skipped_error
        self.logger.info(f"  有效点数: {len(points):,}, 跳过无效行: {total_skipped:,} "
                        f"(Bad={skipped_bad}, 短行={skipped_short}, 解析错误={skipped_error}), "
                        f"采样率: 1/{sample_rate}")
        return points

    def load_asc_file(self, filepath: str, sample_rate: int = None) -> np.ndarray:
        """加载ASC文件：解析文件头 + 读取数据区"""
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"ASC文件不存在: {filepath}")

        if sample_rate is None:
            sample_rate = self.sample_rate

        self.logger.info(f"[1/4] ASC文件头解析: {filepath}")
        header_info = self._parse_asc_header(filepath)
        self.logger.info(f"  文件格式: Format {header_info.file_format}, "
                        f"图像尺寸: {header_info.x_size}x{header_info.y_size}, "
                        f"像素大小: {header_info.pixel_size} mm")

        points = self._read_asc_data(filepath, header_info, sample_rate)
        return points

    def remove_plane(self, points: np.ndarray, z_threshold: float = None) -> np.ndarray:
        """Z阈值平面去除"""
        if z_threshold is None:
            z_threshold = self.z_threshold

        mask = points[:, 2] <= z_threshold
        hemisphere_points = points[mask]
        plane_count = len(points) - len(hemisphere_points)

        self.logger.info(f"[2/4] 平面去除: Z阈值={z_threshold} mm, "
                        f"删除平面点={plane_count:,}, 保留半球点={len(hemisphere_points):,}, "
                        f"去除比例={plane_count/len(points)*100:.1f}%")
        return hemisphere_points

    def denoise(self, points: np.ndarray, nb_neighbors: int = None, std_ratio: float = None) -> np.ndarray:
        """Open3D统计滤波去噪"""
        import open3d as o3d

        if nb_neighbors is None:
            nb_neighbors = self.nb_neighbors
        if std_ratio is None:
            std_ratio = self.std_ratio

        pcd = o3d.geometry.PointCloud()
        pcd.points = o3d.utility.Vector3dVector(points)
        filtered_pcd, _ = pcd.remove_statistical_outlier(
            nb_neighbors=nb_neighbors,
            std_ratio=std_ratio
        )
        filtered_points = np.asarray(filtered_pcd.points)

        if len(filtered_points) < 1000:
            self.logger.warning("去噪后点云过少")

        self.logger.info(f"[3/4] 统计滤波去噪: 去噪前={len(points):,}, "
                        f"去噪后={len(filtered_points):,}, "
                        f"删除离群点={len(points)-len(filtered_points):,}")
        return filtered_points

    def process_step1(self, filepath: str, output_dir: str) -> np.ndarray:
        """步骤1完整流程: ASC文件 -> 半球点云"""
        source_name = Path(filepath).stem
        hemisphere_path = os.path.join(output_dir, f"{source_name}_hemisphere_only.xyz")

        if self.reuse_intermediate and os.path.exists(hemisphere_path):
            self.logger.info(f"复用已有半球点云: {hemisphere_path}")
            points = np.loadtxt(hemisphere_path)
            self.logger.info(f"  加载点数: {len(points):,}")
            return points

        total_start = time.time()

        t0 = time.time()
        points = self.load_asc_file(filepath)
        t1 = time.time()
        self.logger.info(f"  [1/4] 耗时: {t1-t0:.1f}s, 点数: {len(points):,}")

        t0 = time.time()
        points = self.remove_plane(points)
        t1 = time.time()
        self.logger.info(f"  [2/4] 耗时: {t1-t0:.1f}s, 点数: {len(points):,}")

        t0 = time.time()
        points = self.denoise(points)
        t1 = time.time()
        self.logger.info(f"  [3/4] 耗时: {t1-t0:.1f}s, 点数: {len(points):,}")

        if self.save_intermediate:
            t0 = time.time()
            os.makedirs(output_dir, exist_ok=True)
            tmp_path = hemisphere_path + '.tmp'
            np.savetxt(tmp_path, points, fmt='%.6f', delimiter=' ')
            os.replace(tmp_path, hemisphere_path)
            t1 = time.time()
            self.logger.info(f"  [4/4] 半球点云保存: {hemisphere_path}, 耗时: {t1-t0:.1f}s")
        else:
            self.logger.info(f"  [4/4] 跳过中间文件保存")

        self.logger.info(f"步骤1完成，总耗时: {time.time()-total_start:.1f}s")
        return points


class HRGExtractor:
    """HRG谐振子提取模块 - 步骤2: 半球点云 -> 纯HRG谐振子"""

    def __init__(self, config: Dict):
        asc_cfg = config.get('asc_processing', {})
        self.ghost_z_threshold = asc_cfg.get('ghost_z_threshold', -0.1)
        self.assembly_z_percentile = asc_cfg.get('assembly_z_percentile', 90)
        self.radius_fallback_percentile = asc_cfg.get('radius_fallback_percentile', 50)
        self.save_intermediate = asc_cfg.get('save_intermediate', True)
        self.logger = logging.getLogger('HRGExtractor')

    @staticmethod
    def _import_hrg_special_analyzer():
        """
        多级fallback import HRGSpecialAnalyzer

        尝试顺序:
        1. 绝对import: from HRG_Analyzer_Package.core.hrg_special_analyzer
        2. 相对import: from ...core.hrg_special_analyzer (v4.0作为包内子模块)
        3. 路径推导import: 基于当前文件位置计算HRG_Analyzer_Package/core路径
        """
        import importlib
        import sys

        # 尝试1: 绝对import（需sys.path包含项目根目录）
        try:
            from HRG_Analyzer_Package.core.hrg_special_analyzer import HRGSpecialAnalyzer
            return HRGSpecialAnalyzer
        except ImportError:
            pass

        # 尝试2: 相对import（v4.0作为包内子模块运行）
        try:
            from ...core.hrg_special_analyzer import HRGSpecialAnalyzer
            return HRGSpecialAnalyzer
        except (ImportError, ValueError):
            pass

        # 尝试3: 基于当前文件位置的路径推导
        current_dir = None
        try:
            # precision_analyzer.py位于 v4.0_Precision_Analyzer/core/
            # 上溯2级到v4.0_Precision_Analyzer/，再上溯1级到HRG_Analyzer_Package/
            current_dir = Path(__file__).resolve().parent  # v4.0/core/
            hrg_package_core = current_dir.parent.parent / 'core'  # HRG_Analyzer_Package/core/

            if (hrg_package_core / 'hrg_special_analyzer.py').exists():
                if str(hrg_package_core) not in sys.path:
                    sys.path.insert(0, str(hrg_package_core))
                from hrg_special_analyzer import HRGSpecialAnalyzer
                return HRGSpecialAnalyzer
        except ImportError:
            pass

        # 全部失败：提供明确错误信息
        raise ImportError(
            "无法导入HRGSpecialAnalyzer。请确保以下路径之一可用:\n"
            "  1. HRG_Analyzer_Package.core.hrg_special_analyzer 在sys.path中可解析\n"
            "  2. HRG_Analyzer_Package/core/hrg_special_analyzer.py 文件存在\n"
            f"  当前文件位置: {__file__}\n"
            f"  尝试路径推导: {current_dir.parent.parent / 'core' / 'hrg_special_analyzer.py' if current_dir else 'N/A'}"
        )

    def segment_hrg(self, points: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """HRG谐振子与装配结构分割"""
        HRGSpecialAnalyzer = self._import_hrg_special_analyzer()

        analyzer = HRGSpecialAnalyzer()
        hrg_points, assembly_points, bottom_plane = analyzer.segment_hrg_and_assembly(points)

        if len(hrg_points) == 0:
            raise ValueError("分割失败：未找到谐振陀螺部分")

        total = len(points)
        self.logger.info(f"  HRG谐振子: {len(hrg_points):,} ({len(hrg_points)/total*100:.1f}%), "
                        f"装配结构: {len(assembly_points):,} ({len(assembly_points)/total*100:.1f}%), "
                        f"底部平面: {len(bottom_plane):,} ({len(bottom_plane)/total*100:.1f}%)")
        return hrg_points, assembly_points, bottom_plane

    def _clean_by_z_threshold(self, hrg_points: np.ndarray, z_threshold: float) -> Tuple[np.ndarray, np.ndarray]:
        """Z阈值法虚影点识别"""
        ghost_mask = hrg_points[:, 2] > z_threshold
        ghost_points = hrg_points[ghost_mask]
        clean_points = hrg_points[~ghost_mask]
        self.logger.info(f"  Z阈值法: 虚影点={len(ghost_points):,} ({len(ghost_points)/len(hrg_points)*100:.1f}%)")
        return clean_points, ghost_points

    def _clean_by_statistical(self, hrg_points: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """统计离群法虚影点识别（辅助信息）"""
        z = hrg_points[:, 2]
        z_neg = z[z < 0]
        if len(z_neg) == 0:
            self.logger.info(f"  统计离群法: 无Z<0的点，跳过")
            return hrg_points, np.empty((0, 3))

        z_mean = np.mean(z_neg)
        z_std = np.std(z_neg)
        z_outlier_threshold = z_mean + 3 * z_std
        ghost_mask = z > z_outlier_threshold
        ghost_points = hrg_points[ghost_mask]
        clean_points = hrg_points[~ghost_mask]
        self.logger.info(f"  统计离群法: Z均值={z_mean:.3f}, Z标准差={z_std:.3f}, "
                        f"阈值={z_outlier_threshold:.3f}, 离群点={len(ghost_points):,}")
        return clean_points, ghost_points

    def clean_ghost_points(self, hrg_points: np.ndarray, z_threshold: float = None) -> Tuple[np.ndarray, np.ndarray]:
        """虚影点清理主方法：Z阈值法清理 + 统计离群法辅助信息"""
        if z_threshold is None:
            z_threshold = self.ghost_z_threshold

        clean_points, ghost_points = self._clean_by_z_threshold(hrg_points, z_threshold)

        self._clean_by_statistical(hrg_points)

        return clean_points, ghost_points

    def process_step2(self, hemisphere_points: np.ndarray, output_dir: str, source_name: str) -> np.ndarray:
        """步骤2完整流程: 半球点云 -> 纯HRG谐振子"""
        total_start = time.time()

        t0 = time.time()
        hrg_points, assembly_points, bottom_plane = self.segment_hrg(hemisphere_points)
        t1 = time.time()
        self.logger.info(f"  [1/3] HRG分割耗时: {t1-t0:.1f}s, HRG点数: {len(hrg_points):,}")

        t0 = time.time()
        clean_points, ghost_points = self.clean_ghost_points(hrg_points)
        t1 = time.time()
        self.logger.info(f"  [2/3] 虚影清理耗时: {t1-t0:.1f}s, 清理后点数: {len(clean_points):,}")

        if len(clean_points) < 1000:
            self.logger.warning("清理后HRG谐振子点云过少")

        cleaned_path = os.path.join(output_dir, f"{source_name}_hrg_only_cleaned.xyz")
        if self.save_intermediate:
            t0 = time.time()
            os.makedirs(output_dir, exist_ok=True)
            tmp_path = cleaned_path + '.tmp'
            np.savetxt(tmp_path, clean_points, fmt='%.6f', delimiter=' ')
            os.replace(tmp_path, cleaned_path)
            t1 = time.time()
            self.logger.info(f"  [3/3] 纯HRG保存: {cleaned_path}, 耗时: {t1-t0:.1f}s")
        else:
            self.logger.info(f"  [3/3] 跳过中间文件保存")

        self.logger.info(f"步骤2完成，总耗时: {time.time()-total_start:.1f}s")
        return clean_points


class PrecisionAnalyzer:
    """
    加工精度主分析器
    整合所有分析模块，提供统一的分析接口
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        初始化主分析器
        
        Args:
            config_path: 配置文件路径
        """
        # 加载配置
        self.config = self._load_config(config_path)
        
        # 设置日志
        self._setup_logging()
        
        # 初始化各分析器
        self.roughness_analyzer = RoughnessAnalyzer(
            self.config.get('roughness', {})
        )
        self.waviness_analyzer = WavinessAnalyzer(
            self.config.get('waviness', {})
        )
        self.symmetry_analyzer = SymmetryAnalyzer(
            self.config.get('symmetry', {})
        )
        self.thickness_analyzer = ThicknessAnalyzer(
            self.config.get('thickness', {})
        )
        self.resonance_analyzer = ResonanceAnalyzer(
            self.config.get('resonance', {})
        )
        self.quality_evaluator = QualityEvaluator(
            self.config.get('quality', {})
        )
        
        self.logger = logging.getLogger('PrecisionAnalyzer')

        self.asc_preprocessor = ASCPreprocessor(self.config)
        self.hrg_extractor = HRGExtractor(self.config)
    
    def _load_config(self, config_path: Optional[str]) -> Dict[str, Any]:
        """加载配置文件"""
        if config_path is None:
            # 使用默认配置
            config_path = Path(__file__).parent.parent / 'config' / 'default_config.yaml'
        
        if Path(config_path).exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        else:
            self.logger.warning(f"配置文件不存在: {config_path}，使用默认配置")
            return {}
    
    def _setup_logging(self):
        """设置日志"""
        log_config = self.config.get('logging', {})
        level = log_config.get('level', 'INFO')
        
        logging.basicConfig(
            level=getattr(logging, level),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    def analyze(self, point_cloud: np.ndarray,
               enable_roughness: bool = True,
               enable_waviness: bool = True,
               enable_symmetry: bool = True,
               enable_thickness: bool = True,
               enable_resonance: bool = True,
               enable_quality: bool = True,
               enable_flatness: bool = True,
               enable_roundness_full: bool = True,
               enable_profile_filter: bool = True,
               enable_tooth_analysis: bool = True) -> PrecisionAnalysisResult:
        """
        执行完整的加工精度分析
        
        Args:
            point_cloud: 点云数据 (N, 3)
            enable_roughness: 是否启用粗糙度分析
            enable_waviness: 是否启用波纹度分析
            enable_symmetry: 是否启用对称性分析
            enable_thickness: 是否启用壁厚分析
            enable_resonance: 是否启用谐振参数分析
            enable_quality: 是否启用质量评价
            enable_flatness: 是否启用平面度分析 (GB/T 24630)
            enable_roundness_full: 是否启用圆度完整评定 (GB/T 7235)
            enable_profile_filter: 是否启用轮廓滤波 (GB/T 6062)
            
        Returns:
            PrecisionAnalysisResult对象
        """
        self.logger.info("=" * 60)
        self.logger.info("开始HRG谐振陀螺加工精度分析")
        self.logger.info(f"点云数量: {len(point_cloud)}")
        self.logger.info("=" * 60)
        
        start_time = time.time()
        
        result = PrecisionAnalysisResult()
        
        try:
            # 1. 表面粗糙度分析
            if enable_roughness:
                self.logger.info("\n[1/10] 表面粗糙度分析 (GB/T 3505)...")
                result.roughness_result = self.roughness_analyzer.analyze(point_cloud)
                self.logger.info(f"Ra = {result.roughness_result.ra:.3f} um")
                self.logger.info(f"Rq = {result.roughness_result.rq:.3f} um")
                self.logger.info(f"Rz = {result.roughness_result.rz:.3f} um")
                self.logger.info(f"RSm = {result.roughness_result.rsm:.3f} mm")
            
            # 2. 波纹度分析
            if enable_waviness:
                self.logger.info("\n[2/10] 波纹度分析...")
                result.waviness_result = self.waviness_analyzer.analyze(point_cloud)
                self.logger.info(f"波纹度幅值 = {result.waviness_result.waviness_amplitude:.3f} um")
            
            # 3. 对称性分析
            if enable_symmetry:
                self.logger.info("\n[3/10] 对称性分析...")
                result.symmetry_result = self.symmetry_analyzer.analyze(point_cloud)
                for order, error in result.symmetry_result.symmetry_errors.items():
                    self.logger.info(f"{order}阶对称性误差 = {error:.4f}")
            
            # 4. 壁厚分析
            if enable_thickness:
                self.logger.info("\n[4/10] 壁厚分析...")
                result.thickness_result = self.thickness_analyzer.analyze(point_cloud)
                self.logger.info(f"平均壁厚 = {result.thickness_result.mean_thickness:.3f} mm")
                self.logger.info(f"壁厚不均匀度 = {result.thickness_result.uniformity:.4f}")
            
            # 5. 谐振参数分析
            if enable_resonance:
                self.logger.info("\n[5/10] 谐振参数分析...")
                result.resonance_result = self.resonance_analyzer.analyze(point_cloud)
                self.logger.info(f"质量分布均匀性 = {result.resonance_result.mass_uniformity:.4f}")
            
            # 6. 平面度分析 (GB/T 24630)
            if enable_flatness:
                self.logger.info("\n[6/10] 平面度分析 (GB/T 24630.1-2024)...")
                flatness_analyzer = FlatnessAnalyzer(self.config.get('flatness', {}))
                result.flatness_result = flatness_analyzer.analyze(point_cloud)
                self.logger.info(f"FLTt(MZPL) = {result.flatness_result.flt_t_mz:.3f} um")
                self.logger.info(f"FLTt(LSPL) = {result.flatness_result.flt_t_ls:.3f} um")
            
            # 7. 圆度完整评定 (GB/T 7235)
            if enable_roundness_full:
                self.logger.info("\n[7/10] 圆度完整评定 (GB/T 7235-2004)...")
                roundness_full_analyzer = RoundnessFullAnalyzer(self.config.get('roundness_full', {}))
                result.roundness_full_result = roundness_full_analyzer.analyze(point_cloud)
                self.logger.info(f"MZC = {result.roundness_full_result.mzc_error:.3f} um")
                self.logger.info(f"LSC = {result.roundness_full_result.lsc_error:.3f} um")
            
            # 8. 轮廓滤波 (GB/T 6062)
            if enable_profile_filter:
                self.logger.info("\n[8/10] 轮廓滤波 (GB/T 6062-2009)...")
                profile_filter_analyzer = ProfileFilterAnalyzer(self.config.get('profile_filter', {}))
                result.profile_filter_result = profile_filter_analyzer.analyze(point_cloud)
                self.logger.info(f"lambda_c = {result.profile_filter_result.lambda_c} mm")
            
            # 9. 质量评价
            if enable_quality:
                self.logger.info("\n[9/10] 质量评价...")
                result.quality_result = self.quality_evaluator.analyze(
                    roughness_result=result.roughness_result,
                    symmetry_result=result.symmetry_result,
                    thickness_result=result.thickness_result,
                    waviness_result=result.waviness_result,
                    resonance_result=result.resonance_result
                )
                self.logger.info(f"综合评分 = {result.quality_result.total_score:.1f} 分")
                self.logger.info(f"质量等级 = {result.quality_result.grade}")
            
            # 10. 齿状结构分析
            if enable_tooth_analysis:
                self.logger.info("\n[10/10] 齿状结构分析...")
                tooth_count = self.config.get('tooth_analysis', {}).get('theoth_count', 48)
                result.tooth_analysis_result = analyze_tooth_structure(point_cloud, tooth_count)
                if result.tooth_analysis_result and result.tooth_analysis_result.tooth_count > 0:
                    self.logger.info(f"齿数 = {result.tooth_analysis_result.tooth_count}")
                    self.logger.info(f"齿高 = {result.tooth_analysis_result.tooth_height_mean:.3f} ± {result.tooth_analysis_result.tooth_height_std:.3f} mm")
                    self.logger.info(f"齿宽 = {result.tooth_analysis_result.tooth_width_mean:.3f} ± {result.tooth_analysis_result.tooth_width_std:.3f} mm")
                    self.logger.info(f"齿厚 = {result.tooth_analysis_result.tooth_thickness_mean:.3f} ± {result.tooth_analysis_result.tooth_thickness_std:.3f} mm")
                    self.logger.info(f"平面度 = {result.tooth_analysis_result.flatness_mean:.6f} mm")
                    self.logger.info(f"质量评分 = {result.tooth_analysis_result.quality_score:.1f} 分")
                    self.logger.info(f"质量等级 = {result.tooth_analysis_result.quality_grade}")
                else:
                    self.logger.info("齿状结构分析未检测到齿或已禁用")
                
                if result.quality_result.improvement_suggestions:
                    self.logger.info("\n改进建议:")
                    for i, suggestion in enumerate(result.quality_result.improvement_suggestions, 1):
                        self.logger.info(f"  {i}. {suggestion}")
            
            # 计算总时间
            result.analysis_time = time.time() - start_time
            
            self.logger.info("\n" + "=" * 60)
            self.logger.info(f"分析完成，总耗时: {result.analysis_time:.2f} 秒")
            self.logger.info("=" * 60)
            
            return result
            
        except Exception as e:
            self.logger.error(f"分析失败: {str(e)}", exc_info=True)
            raise
    
    def analyze_from_file(self, filepath: str, **kwargs) -> PrecisionAnalysisResult:
        """
        从文件加载点云并分析
        
        Args:
            filepath: 点云文件路径
            **kwargs: 传递给analyze的参数
            
        Returns:
            PrecisionAnalysisResult对象
        """
        self.logger.info(f"从文件加载点云: {filepath}")
        
        # 加载点云
        point_cloud = self._load_point_cloud(filepath)
        
        # 执行分析
        return self.analyze(point_cloud, **kwargs)
    
    def _process_asc_pipeline(self, filepath: str) -> np.ndarray:
        """ASC完整两步处理流程"""
        filepath_obj = Path(filepath)
        source_name = filepath_obj.stem
        output_dir = str(filepath_obj.parent)

        hemisphere_points = self.asc_preprocessor.process_step1(filepath, output_dir)
        hrg_points = self.hrg_extractor.process_step2(hemisphere_points, output_dir, source_name)
        return hrg_points

    def _load_point_cloud(self, filepath: str) -> np.ndarray:
        """加载点云文件"""
        filepath = Path(filepath)
        
        if filepath.suffix == '.xyz':
            # XYZ格式
            point_cloud = np.loadtxt(filepath)
        elif filepath.suffix in ('.asc', '.ASC'):
            # ASC格式 - 使用完整两步处理流程
            point_cloud = self._process_asc_pipeline(str(filepath))
        elif filepath.suffix == '.txt':
            # TXT格式
            point_cloud = np.loadtxt(filepath)
        else:
            raise ValueError(f"不支持的文件格式: {filepath.suffix}")
        
        return point_cloud
    
    def save_result(self, result: PrecisionAnalysisResult, 
                   output_path: str,
                   format: str = 'json') -> None:
        """
        保存分析结果
        
        Args:
            result: 分析结果
            output_path: 输出路径
            format: 输出格式 ('json', 'yaml')
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        if format == 'json':
            result.to_json(output_path)
        elif format == 'yaml':
            with open(output_path, 'w', encoding='utf-8') as f:
                yaml.dump(result.to_dict(), f, allow_unicode=True)
        else:
            raise ValueError(f"不支持的输出格式: {format}")
        
        self.logger.info(f"结果已保存到: {output_path}")
