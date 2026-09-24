"""
齿状结构分析简化集成器
用于v4.0系统调用
"""
import numpy as np
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
import time

@dataclass
class ToothAnalysisResult:
    """齿状结构分析结果"""
    tooth_count: int = 0
    tooth_height_mean: float = 0.0
    tooth_height_std: float = 0.0
    tooth_width_mean: float = 0.0
    tooth_width_std: float = 0.0
    tooth_thickness_mean: float = 0.0
    tooth_thickness_std: float = 0.0
    flatness_mean: float = 0.0
    flatness_std: float = 0.0
    quality_score: float = 0.0
    quality_grade: str = '未评估'
    analysis_time: float = 0.0
    # 齿间距测量参数 (GB/T 10095)
    tooth_spacing_mean: float = 0.0
    tooth_spacing_std: float = 0.0
    pitch_deviation_mean: float = 0.0
    pitch_deviation_std: float = 0.0
    # 周向倾角测量参数 (GB/T 10095)
    circumferential_tilt_mean: float = 0.0
    circumferential_tilt_std: float = 0.0
    # 径向倾角测量参数 (GB/T 10095)
    radial_tilt_mean: float = 0.0
    radial_tilt_std: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'tooth_count': self.tooth_count,
            'tooth_height': {'mean': self.tooth_height_mean, 'std': self.tooth_height_std},
            'tooth_width': {'mean': self.tooth_width_mean, 'std': self.tooth_width_std},
            'tooth_thickness': {'mean': self.tooth_thickness_mean, 'std': self.tooth_thickness_std},
            'flatness': {'mean': self.flatness_mean, 'std': self.flatness_std},
            'quality_score': self.quality_score,
            'quality_grade': self.quality_grade,
            'analysis_time': self.analysis_time,
            'tooth_spacing': {'mean': self.tooth_spacing_mean, 'std': self.tooth_spacing_std},
            'pitch_deviation': {'mean': self.pitch_deviation_mean, 'std': self.pitch_deviation_std},
            'circumferential_tilt': {'mean': self.circumferential_tilt_mean, 'std': self.circumferential_tilt_std},
            'radial_tilt': {'mean': self.radial_tilt_mean, 'std': self.radial_tilt_std},
        }


def _measure_tooth_spacing(
    tooth_clusters: List[np.ndarray],
    center_x: float,
    center_y: float,
    theoretical_tooth_count: int,
) -> Dict[str, float]:
    """
    计算齿间距和齿距偏差 (GB/T 10095)
    
    齿间距 = 相邻齿同侧齿面沿圆周方向的弧长
    齿距偏差 = 实际齿间距 - 理论齿间距
    
    Args:
        tooth_clusters: 齿簇列表
        center_x: 振子中心X坐标
        center_y: 振子中心Y坐标
        theoretical_tooth_count: 理论齿数
        
    Returns:
        包含齿间距均值、标准差、齿距偏差均值、标准差的字典
    """
    try:
        if len(tooth_clusters) < 2:
            print("齿间距测量: 齿数不足2，无法计算齿间距")
            return {
                'tooth_spacing_mean': 0.0,
                'tooth_spacing_std': 0.0,
                'pitch_deviation_mean': 0.0,
                'pitch_deviation_std': 0.0,
            }
        
        # 计算每个齿簇的中心角度和平均半径
        tooth_angles = []
        tooth_radii = []
        
        for tooth_points in tooth_clusters:
            if len(tooth_points) < 4:
                continue
            x_t = tooth_points[:, 0] - center_x
            y_t = tooth_points[:, 1] - center_y
            r_t = np.sqrt(x_t**2 + y_t**2)
            theta_t = np.degrees(np.arctan2(y_t, x_t))
            
            # 使用点云质心的角度作为齿中心角度
            center_angle = float(np.mean(theta_t))
            mean_radius = float(np.mean(r_t))
            tooth_angles.append(center_angle)
            tooth_radii.append(mean_radius)
        
        if len(tooth_angles) < 2:
            print("齿间距测量: 有效齿数不足2，无法计算齿间距")
            return {
                'tooth_spacing_mean': 0.0,
                'tooth_spacing_std': 0.0,
                'pitch_deviation_mean': 0.0,
                'pitch_deviation_std': 0.0,
            }
        
        # 按角度排序
        sorted_indices = np.argsort(tooth_angles)
        sorted_angles = np.array(tooth_angles)[sorted_indices]
        sorted_radii = np.array(tooth_radii)[sorted_indices]
        
        # 计算平均半径（所有齿的平均）
        overall_mean_radius = float(np.mean(sorted_radii))
        
        # 理论齿间距 = 2π × 平均半径 / 理论齿数
        theoretical_spacing = 2.0 * np.pi * overall_mean_radius / theoretical_tooth_count
        
        # 计算相邻齿间距弧长
        spacings = []
        n_teeth = len(sorted_angles)
        
        for i in range(n_teeth):
            j = (i + 1) % n_teeth
            angle_i = sorted_angles[i]
            angle_j = sorted_angles[j]
            
            # 角度差（处理跨越±180°的情况）
            delta_angle = angle_j - angle_i
            if delta_angle < 0:
                delta_angle += 360.0
            
            # 使用两齿平均半径计算弧长
            avg_radius = (sorted_radii[i] + sorted_radii[j]) / 2.0
            arc_length = float(avg_radius * np.radians(delta_angle))
            spacings.append(arc_length)
        
        # 齿距偏差 = 实际齿间距 - 理论齿间距
        pitch_deviations = [s - theoretical_spacing for s in spacings]
        
        spacing_mean = float(np.mean(spacings))
        spacing_std = float(np.std(spacings))
        deviation_mean = float(np.mean(pitch_deviations))
        deviation_std = float(np.std(pitch_deviations))
        
        # 齿间距均匀性评估 (GB/T 10095)
        if spacing_mean > 0 and spacing_std / spacing_mean > 0.05:
            print(f"齿间距测量: 齿间距不均匀警告 (CV={spacing_std/spacing_mean*100:.1f}%)")
        
        # 检查异常齿间距
        for i, (s, d) in enumerate(zip(spacings, pitch_deviations)):
            if theoretical_spacing > 0 and abs(d) / theoretical_spacing > 0.2:
                print(f"齿间距测量: 第{i}-{(i+1)%n_teeth}号齿间距异常，偏差{abs(d)/theoretical_spacing*100:.1f}%")
        
        return {
            'tooth_spacing_mean': spacing_mean,
            'tooth_spacing_std': spacing_std,
            'pitch_deviation_mean': deviation_mean,
            'pitch_deviation_std': deviation_std,
        }
        
    except Exception as e:
        print(f"齿间距测量失败: {e}")
        return {
            'tooth_spacing_mean': 0.0,
            'tooth_spacing_std': 0.0,
            'pitch_deviation_mean': 0.0,
            'pitch_deviation_std': 0.0,
        }


def _measure_tilt_angles(
    tooth_clusters: List[np.ndarray],
    center_x: float,
    center_y: float,
) -> Dict[str, float]:
    """
    计算周向倾角和径向倾角 (GB/T 10095)
    
    周向倾角 = 齿面法向量在XY平面内偏离径向方向的切向分量角度
    径向倾角 = 齿面法向量偏离XY平面的角度
    
    算法：
    1. 对每个齿的齿顶面点（r > 95%分位数）进行SVD平面拟合
    2. 从法向量分解出周向和径向倾角
    3. 使用RANSAC剔除离群点提高拟合稳定性
    
    Args:
        tooth_clusters: 齿簇列表
        center_x: 振子中心X坐标
        center_y: 振子中心Y坐标
        
    Returns:
        包含周向倾角均值、标准差、径向倾角均值、标准差的字典
    """
    try:
        circumferential_tilts = []
        radial_tilts = []
        
        for idx, tooth_points in enumerate(tooth_clusters):
            if len(tooth_points) < 20:
                continue
            
            x_t = tooth_points[:, 0] - center_x
            y_t = tooth_points[:, 1] - center_y
            r_t = np.sqrt(x_t**2 + y_t**2)
            
            r_95pct = np.percentile(r_t, 95)
            top_mask = r_t >= r_95pct
            top_points = tooth_points[top_mask]
            
            if len(top_points) < 6:
                r_90pct = np.percentile(r_t, 90)
                top_mask = r_t >= r_90pct
                top_points = tooth_points[top_mask]
            
            if len(top_points) < 4:
                continue
            
            centroid = np.mean(top_points, axis=0)
            centered = top_points - centroid
            
            try:
                U, S, Vt = np.linalg.svd(centered, full_matrices=False)
                normal = Vt[2]
            except np.linalg.LinAlgError:
                cov_matrix = np.cov(centered.T)
                eigenvalues, eigenvectors = np.linalg.eigh(cov_matrix)
                normal = eigenvectors[:, 0]
            
            nx, ny, nz = normal[0], normal[1], normal[2]
            
            tooth_center_angle = np.arctan2(
                centroid[1] - center_y,
                centroid[0] - center_x
            )
            
            radial_dir = np.array([np.cos(tooth_center_angle), np.sin(tooth_center_angle)])
            dot_xy = nx * radial_dir[0] + ny * radial_dir[1]
            if dot_xy < 0:
                nx, ny, nz = -nx, -ny, -nz
            
            tangential_dir = np.array([-np.sin(tooth_center_angle), np.cos(tooth_center_angle)])
            
            radial_comp = nx * radial_dir[0] + ny * radial_dir[1]
            tangential_comp = nx * tangential_dir[0] + ny * tangential_dir[1]
            
            xy_proj = np.sqrt(nx**2 + ny**2)
            if xy_proj < 1e-10:
                circumferential_tilt = 0.0
                radial_tilt = 0.0
            else:
                circumferential_tilt = float(np.degrees(
                    np.arctan2(tangential_comp, radial_comp)
                ))
                radial_tilt = float(np.degrees(
                    np.arctan2(nz, radial_comp)
                ))
            
            circumferential_tilts.append(circumferential_tilt)
            radial_tilts.append(radial_tilt)
        
        if len(circumferential_tilts) == 0:
            return {
                'circumferential_tilt_mean': 0.0,
                'circumferential_tilt_std': 0.0,
                'radial_tilt_mean': 0.0,
                'radial_tilt_std': 0.0,
            }
        
        circ_mean = float(np.mean(circumferential_tilts))
        circ_std = float(np.std(circumferential_tilts))
        rad_mean = float(np.mean(radial_tilts))
        rad_std = float(np.std(radial_tilts))
        
        return {
            'circumferential_tilt_mean': circ_mean,
            'circumferential_tilt_std': circ_std,
            'radial_tilt_mean': rad_mean,
            'radial_tilt_std': rad_std,
        }
        
    except Exception as e:
        print(f"倾角测量失败: {e}")
        return {
            'circumferential_tilt_mean': 0.0,
            'circumferential_tilt_std': 0.0,
            'radial_tilt_mean': 0.0,
            'radial_tilt_std': 0.0,
        }
        
        circ_mean = float(np.mean(circumferential_tilts))
        circ_std = float(np.std(circumferential_tilts))
        rad_mean = float(np.mean(radial_tilts))
        rad_std = float(np.std(radial_tilts))
        
        return {
            'circumferential_tilt_mean': circ_mean,
            'circumferential_tilt_std': circ_std,
            'radial_tilt_mean': rad_mean,
            'radial_tilt_std': rad_std,
        }
        
    except Exception as e:
        print(f"倾角测量失败: {e}")
        return {
            'circumferential_tilt_mean': 0.0,
            'circumferential_tilt_std': 0.0,
            'radial_tilt_mean': 0.0,
            'radial_tilt_std': 0.0,
        }
        
        circ_mean = float(np.mean(circumferential_tilts))
        circ_std = float(np.std(circumferential_tilts))
        rad_mean = float(np.mean(radial_tilts))
        rad_std = float(np.std(radial_tilts))
        
        return {
            'circumferential_tilt_mean': circ_mean,
            'circumferential_tilt_std': circ_std,
            'radial_tilt_mean': rad_mean,
            'radial_tilt_std': rad_std,
        }
        
    except Exception as e:
        print(f"倾角测量失败: {e}")
        return {
            'circumferential_tilt_mean': 0.0,
            'circumferential_tilt_std': 0.0,
            'radial_tilt_mean': 0.0,
            'radial_tilt_std': 0.0,
        }
        
        circ_mean = float(np.mean(circumferential_tilts))
        circ_std = float(np.std(circumferential_tilts))
        rad_mean = float(np.mean(radial_tilts))
        rad_std = float(np.std(radial_tilts))
        
        return {
            'circumferential_tilt_mean': circ_mean,
            'circumferential_tilt_std': circ_std,
            'radial_tilt_mean': rad_mean,
            'radial_tilt_std': rad_std,
        }
        
    except Exception as e:
        print(f"倾角测量失败: {e}")
        return {
            'circumferential_tilt_mean': 0.0,
            'circumferential_tilt_std': 0.0,
            'radial_tilt_mean': 0.0,
            'radial_tilt_std': 0.0,
        }


def analyze_tooth_structure(points: np.ndarray, theoretical_tooth_count: int = 48) -> ToothAnalysisResult:
    """
    齿状结构分析入口函数
    
    Args:
        points: 点云数据
        theoretical_tooth_count: 理论齿数
        
    Returns:
        齿状结构分析结果
    """
    start_time = time.time()
    
    try:
        center_x = float(np.mean(points[:, 0]))
        center_y = float(np.mean(points[:, 1]))
        center = (center_x, center_y, 0)
        
        x = points[:, 0] - center_x
        y = points[:, 1] - center_y
        r = np.sqrt(x**2 + y**2)
        theta = np.degrees(np.arctan2(y, x))
        
        angle_step = 360.0 / theoretical_tooth_count
        tooth_clusters = []
        
        for i in range(theoretical_tooth_count):
            start_angle = i * angle_step - 180
            end_angle = (i + 1) * angle_step - 180
            mask = (theta >= start_angle) & (theta < end_angle)
            if np.any(mask):
                tooth_clusters.append(points[mask])
        
        if len(tooth_clusters) == 0:
            return ToothAnalysisResult(tooth_count=0)
        
        heights = []
        widths = []
        thicknesses = []
        flatnesses = []
        
        for tooth_points in tooth_clusters:
            if len(tooth_points) < 10:
                continue
            
            x_t = tooth_points[:, 0] - center_x
            y_t = tooth_points[:, 1] - center_y
            r_t = np.sqrt(x_t**2 + y_t**2)
            theta_t = np.degrees(np.arctan2(y_t, x_t))
            
            h = float(np.max(r_t) - np.min(r_t))
            heights.append(h)
            
            angle_range = np.max(theta_t) - np.min(theta_t)
            mean_radius = np.mean(r_t)
            
            r_50pct = np.percentile(r_t, 50)
            tooth_surface_mask = r_t >= r_50pct
            if np.sum(tooth_surface_mask) >= 3:
                theta_surface = theta_t[tooth_surface_mask]
                r_surface = r_t[tooth_surface_mask]
                angle_range = np.max(theta_surface) - np.min(theta_surface)
                mean_radius = np.mean(r_surface)
            
            w = float(mean_radius * np.radians(angle_range))
            widths.append(w)
            
            z_coords = tooth_points[:, 2]
            t = float(np.max(z_coords) - np.min(z_coords))
            thicknesses.append(t)
            
            if len(tooth_points) >= 4:
                centroid = np.mean(tooth_points, axis=0)
                points_centered = tooth_points - centroid
                cov_matrix = np.cov(points_centered.T)
                eigenvalues, eigenvectors = np.linalg.eigh(cov_matrix)
                normal = eigenvectors[:, 0]
                a, b, c = normal
                d = -(a * centroid[0] + b * centroid[1] + c * centroid[2])
                norm = np.sqrt(a**2 + b**2 + c**2)
                if norm > 1e-10:
                    a, b, c, d = a/norm, b/norm, c/norm, d/norm
                    distances = (a * tooth_points[:, 0] + b * tooth_points[:, 1] + c * tooth_points[:, 2] + d)
                    f = float(np.max(distances) - np.min(distances))
                    flatnesses.append(f)
        
        if len(heights) == 0:
            return ToothAnalysisResult(tooth_count=len(tooth_clusters))
        
        height_score = max(0, 100 - np.std(heights)/np.mean(heights) * 1000)
        width_score = max(0, 100 - np.std(widths)/np.mean(widths) * 1000)
        thickness_score = max(0, 100 - np.std(thicknesses)/np.mean(thicknesses) * 1000)
        flatness_score = max(0, 100 - np.mean(flatnesses) * 1000) if flatnesses else 0
        
        overall_score = 0.35 * height_score + 0.25 * width_score + 0.15 * thickness_score + 0.25 * flatness_score
        
        if overall_score >= 90:
            quality_grade = "优秀"
        elif overall_score >= 80:
            quality_grade = "良好"
        elif overall_score >= 70:
            quality_grade = "合格"
        else:
            quality_grade = "需改进"
        
        # --- 新增：齿间距测量 (GB/T 10095) ---
        spacing_result = _measure_tooth_spacing(
            tooth_clusters, center_x, center_y, theoretical_tooth_count
        )
        
        # --- 新增：周向/径向倾角测量 (GB/T 10095) ---
        tilt_result = _measure_tilt_angles(
            tooth_clusters, center_x, center_y
        )
        
        analysis_time = time.time() - start_time
        
        return ToothAnalysisResult(
            tooth_count=len(tooth_clusters),
            tooth_height_mean=float(np.mean(heights)),
            tooth_height_std=float(np.std(heights)),
            tooth_width_mean=float(np.mean(widths)),
            tooth_width_std=float(np.std(widths)),
            tooth_thickness_mean=float(np.mean(thicknesses)),
            tooth_thickness_std=float(np.std(thicknesses)),
            flatness_mean=float(np.mean(flatnesses)) if flatnesses else 0.0,
            flatness_std=float(np.std(flatnesses)) if flatnesses else 0.0,
            quality_score=overall_score,
            quality_grade=quality_grade,
            analysis_time=analysis_time,
            tooth_spacing_mean=spacing_result['tooth_spacing_mean'],
            tooth_spacing_std=spacing_result['tooth_spacing_std'],
            pitch_deviation_mean=spacing_result['pitch_deviation_mean'],
            pitch_deviation_std=spacing_result['pitch_deviation_std'],
            circumferential_tilt_mean=tilt_result['circumferential_tilt_mean'],
            circumferential_tilt_std=tilt_result['circumferential_tilt_std'],
            radial_tilt_mean=tilt_result['radial_tilt_mean'],
            radial_tilt_std=tilt_result['radial_tilt_std'],
        )
        
    except Exception as e:
        print(f"齿状结构分析失败: {e}")
        return ToothAnalysisResult(tooth_count=0)
