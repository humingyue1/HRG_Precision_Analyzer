"""
HRG谐振陀螺专用分析器
====================
针对谐振陀螺+装配结构的复合点云进行分离分析

分析内容:
1. 区域分割 - 分离谐振陀螺和装配结构
2. 装配误差 - 齿状底部与装配面的距离偏差
3. 圆度误差 - 谐振陀螺的圆度
4. 球度误差 - 仅谐振陀螺部分的球度
"""

import numpy as np
from typing import Dict, Tuple
import time


class HRGSpecialAnalyzer:
    """HRG谐振陀螺专用分析器"""
    
    def __init__(self):
        pass
    
    def segment_hrg_and_assembly(self, points: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        分离谐振陀螺和装配结构
        
        策略:
        1. 根据Z坐标分离 - 底部装配面通常Z值较大(较平)
        2. 根据密度聚类 - 谐振陀螺是密集的半球结构
        3. 根据几何特征 - 谐振陀螺有齿状结构
        
        Returns:
            hrg_points: 谐振陀螺点云
            assembly_points: 装配结构点云
            bottom_plane: 底部装配面
        """
        print(f"\n{'='*70}")
        print("阶段1: 区域分割 - 分离谐振陀螺和装配结构")
        print(f"{'='*70}")
        
        start_time = time.time()
        
        # 1. Z坐标分析
        z_values = points[:, 2]
        z_min, z_max = z_values.min(), z_values.max()
        z_range = z_max - z_min
        
        print(f"  Z范围: [{z_min:.3f}, {z_max:.3f}] mm")
        print(f"  Z跨度: {z_range:.3f} mm")
        
        # 2. 直方图分析 - 找到装配面和谐振陀螺的分界
        hist, bin_edges = np.histogram(z_values, bins=100)
        bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
        
        # 找到Z坐标的峰值 - 通常有两个峰:装配面和谐振陀螺
        from scipy.signal import find_peaks
        peaks, properties = find_peaks(hist, height=len(points)*0.01, distance=10)
        
        print(f"  发现 {len(peaks)} 个Z坐标峰值")
        
        if len(peaks) >= 2:
            # 找到最高的两个峰
            peak_heights = hist[peaks]
            top_two_peaks_idx = np.argsort(peak_heights)[-2:]
            top_two_peaks = peaks[top_two_peaks_idx]
            top_two_peaks_sorted = np.sort(top_two_peaks)
            
            # 分界点在两个峰之间
            valley_start = top_two_peaks_sorted[0]
            valley_end = top_two_peaks_sorted[1]
            
            # 找到谷底(分界点)
            valley_region = hist[valley_start:valley_end]
            valley_idx = valley_start + np.argmin(valley_region)
            z_threshold = bin_centers[valley_idx]
            
            print(f"  峰值1 Z: {bin_centers[top_two_peaks_sorted[0]]:.3f} mm")
            print(f"  峰值2 Z: {bin_centers[top_two_peaks_sorted[1]]:.3f} mm")
            print(f"  分界点 Z: {z_threshold:.3f} mm")
        else:
            # 如果找不到两个峰,使用Z坐标的中位数作为分界
            z_threshold = np.median(z_values)
            print(f"  使用中位数作为分界点 Z: {z_threshold:.3f} mm")
        
        # 3. 初步分割
        # 假设谐振陀螺在Z值较小的区域(半球凹陷)
        # 装配面在Z值较大的区域(平面)
        
        # 但需要根据实际情况调整 - 从图像看,底部白色是装配面
        # 所以装配面应该是Z值最大的一部分
        
        # 找到Z值最大的10%作为装配面
        z_top_threshold = np.percentile(z_values, 90)
        bottom_plane_mask = z_values >= z_top_threshold
        bottom_plane = points[bottom_plane_mask]
        
        print(f"  底部装配面点数: {len(bottom_plane):,}")
        
        # 剩余部分包含谐振陀螺和其他装配结构
        remaining_points = points[~bottom_plane_mask]
        
        # 4. XY平面上的聚类分析 - 分离谐振陀螺
        # 谐振陀螺通常在中心区域,装配结构在周围
        
        xy_coords = remaining_points[:, :2]
        xy_center = np.mean(xy_coords, axis=0)
        
        # 计算到中心的距离
        distances_to_center = np.linalg.norm(xy_coords - xy_center, axis=1)
        
        # 使用直方图找到谐振陀螺的边界
        dist_hist, dist_bin_edges = np.histogram(distances_to_center, bins=100)
        dist_bin_centers = (dist_bin_edges[:-1] + dist_bin_edges[1:]) / 2
        
        # 找到距离的峰值 - 谐振陀螺应该有一个明显的峰
        dist_peaks, _ = find_peaks(dist_hist, height=len(remaining_points)*0.01, distance=10)
        
        if len(dist_peaks) > 0:
            # 找到最内层的峰(谐振陀螺)
            innermost_peak = dist_peaks[0]
            
            # 找到这个峰之后的谷底(谐振陀螺边界)
            if innermost_peak < len(dist_hist) - 10:
                valley_region = dist_hist[innermost_peak:innermost_peak+20]
                valley_idx = innermost_peak + np.argmin(valley_region)
                r_threshold = dist_bin_centers[valley_idx]
            else:
                r_threshold = dist_bin_centers[innermost_peak] * 1.5
            
            print(f"  谐振陀螺半径阈值: {r_threshold:.3f} mm")
        else:
            # 使用距离的中位数
            r_threshold = np.percentile(distances_to_center, 50)
            print(f"  使用中位数作为半径阈值: {r_threshold:.3f} mm")
        
        # 分离谐振陀螺和周围装配结构
        hrg_mask = distances_to_center <= r_threshold
        hrg_points = remaining_points[hrg_mask]
        assembly_points = remaining_points[~hrg_mask]
        
        print(f"  谐振陀螺点数: {len(hrg_points):,}")
        print(f"  周围装配结构点数: {len(assembly_points):,}")
        print(f"  耗时: {time.time() - start_time:.1f} 秒")
        
        return hrg_points, assembly_points, bottom_plane
    
    def analyze_assembly_error(self, hrg_points: np.ndarray, bottom_plane: np.ndarray) -> Dict:
        """
        分析装配误差 - 齿状底部与装配面的距离偏差
        
        策略:
        1. 找到谐振陀螺的齿状底部(最外圈的点)
        2. 计算这些点到底部装配面的距离
        3. 统计距离偏差
        """
        print(f"\n{'='*70}")
        print("阶段2: 装配误差分析")
        print(f"{'='*70}")
        
        start_time = time.time()
        
        # 1. 找到谐振陀螺的齿状底部
        # 齿状底部是最外圈的点,在XY平面上距离中心最远
        
        xy_center = np.mean(hrg_points[:, :2], axis=0)
        distances_to_center = np.linalg.norm(hrg_points[:, :2] - xy_center, axis=1)
        
        # 找到最外圈的点(距离中心最远的20%)
        outer_threshold = np.percentile(distances_to_center, 80)
        outer_mask = distances_to_center >= outer_threshold
        teeth_bottom = hrg_points[outer_mask]
        
        print(f"  齿状底部点数: {len(teeth_bottom):,}")
        
        # 2. 计算齿状底部到底部装配面的距离
        # 对于每个齿状底部的点,找到最近的装配面点
        
        if len(bottom_plane) > 0:
            # 使用KD树加速最近邻搜索
            from scipy.spatial import cKDTree
            tree = cKDTree(bottom_plane)
            
            # 查询每个齿状底部点的最近邻
            distances, indices = tree.query(teeth_bottom)
            
            # 统计距离
            mean_distance = np.mean(distances)
            std_distance = np.std(distances)
            min_distance = np.min(distances)
            max_distance = np.max(distances)
            
            print(f"  平均距离: {mean_distance:.3f} mm")
            print(f"  距离标准差: {std_distance:.3f} mm")
            print(f"  最小距离: {min_distance:.3f} mm")
            print(f"  最大距离: {max_distance:.3f} mm")
            print(f"  耗时: {time.time() - start_time:.1f} 秒")
            
            return {
                'mean_distance': mean_distance,
                'std_distance': std_distance,
                'min_distance': min_distance,
                'max_distance': max_distance,
                'distances': distances
            }
        else:
            print("  警告: 未找到底部装配面")
            return {}
    
    def analyze_roundness(self, points: np.ndarray) -> Dict:
        """
        分析圆度误差
        
        策略:
        1. 在多个Z高度上切片
        2. 对每个切片进行圆拟合
        3. 计算圆度误差
        4. 取最大圆度误差作为结果
        """
        print(f"\n{'='*70}")
        print("阶段3: 圆度误差分析")
        print(f"{'='*70}")
        
        start_time = time.time()
        
        # 1. Z坐标分层
        z_values = points[:, 2]
        z_min, z_max = z_values.min(), z_values.max()
        
        # 分成10层
        n_layers = 10
        z_levels = np.linspace(z_min, z_max, n_layers + 1)
        
        roundness_errors = []
        fitted_circles = []
        
        for i in range(n_layers):
            # 提取当前层的点
            z_low, z_high = z_levels[i], z_levels[i+1]
            layer_mask = (z_values >= z_low) & (z_values < z_high)
            layer_points = points[layer_mask]
            
            if len(layer_points) < 100:
                continue
            
            # 2. 在XY平面上进行圆拟合
            xy_points = layer_points[:, :2]
            
            # 使用最小二乘圆拟合
            def fit_circle_least_squares(points):
                """最小二乘圆拟合"""
                x = points[:, 0]
                y = points[:, 1]
                
                # 构建方程组
                A = np.column_stack([2*x, 2*y, np.ones_like(x)])
                b = x**2 + y**2
                
                # 求解
                try:
                    result = np.linalg.lstsq(A, b, rcond=None)
                    a, b_c, c = result[0]
                    
                    # 圆心和半径
                    x0 = a
                    y0 = b_c
                    r = np.sqrt(c + x0**2 + y0**2)
                    
                    return x0, y0, r
                except:
                    return None, None, None
            
            x0, y0, radius = fit_circle_least_squares(xy_points)
            
            if x0 is None:
                continue
            
            # 3. 计算圆度误差
            distances = np.sqrt((xy_points[:, 0] - x0)**2 + (xy_points[:, 1] - y0)**2)
            roundness_error = np.max(distances) - np.min(distances)
            
            roundness_errors.append(roundness_error)
            fitted_circles.append({
                'z_level': (z_low + z_high) / 2,
                'center': [x0, y0],
                'radius': radius,
                'roundness_error': roundness_error
            })
            
            print(f"  层 {i+1}: Z={(z_low + z_high)/2:.3f} mm, "
                  f"半径={radius:.3f} mm, 圆度误差={roundness_error*1000:.2f} μm")
        
        # 4. 统计结果
        if roundness_errors:
            max_roundness = np.max(roundness_errors)
            mean_roundness = np.mean(roundness_errors)
            
            print(f"\n  最大圆度误差: {max_roundness*1000:.2f} μm")
            print(f"  平均圆度误差: {mean_roundness*1000:.2f} μm")
            print(f"  耗时: {time.time() - start_time:.1f} 秒")
            
            return {
                'max_roundness_error': max_roundness,
                'mean_roundness_error': mean_roundness,
                'roundness_errors': roundness_errors,
                'fitted_circles': fitted_circles
            }
        else:
            print("  警告: 无法计算圆度误差")
            return {}
    
    def analyze_sphericity_hrg_only(self, points: np.ndarray) -> Dict:
        """
        分析谐振陀螺的球度误差(仅针对谐振陀螺部分)
        """
        print(f"\n{'='*70}")
        print("阶段4: 球度误差分析(仅谐振陀螺)")
        print(f"{'='*70}")
        
        start_time = time.time()
        
        # 使用改进的Kasa球拟合
        from scipy.optimize import least_squares
        
        def sphere_residuals(params, points):
            """球拟合残差"""
            x0, y0, z0, r = params
            distances = np.sqrt((points[:, 0] - x0)**2 + 
                               (points[:, 1] - y0)**2 + 
                               (points[:, 2] - z0)**2)
            return distances - r
        
        # 初始猜测
        center = np.mean(points, axis=0)
        radius_guess = np.mean(np.linalg.norm(points - center, axis=1))
        initial_params = [center[0], center[1], center[2], radius_guess]
        
        # 最小二乘拟合
        result = least_squares(sphere_residuals, initial_params, args=(points,))
        x0, y0, z0, radius = result.x
        
        # 计算球度误差
        distances = np.sqrt((points[:, 0] - x0)**2 + 
                           (points[:, 1] - y0)**2 + 
                           (points[:, 2] - z0)**2)
        
        sphericity_error = np.max(distances) - np.min(distances)
        
        print(f"  拟合球心: [{x0:.6f}, {y0:.6f}, {z0:.6f}] mm")
        print(f"  拟合半径: {radius:.6f} mm")
        print(f"  球度误差: {sphericity_error:.6f} mm ({sphericity_error*1000:.2f} μm)")
        print(f"  耗时: {time.time() - start_time:.1f} 秒")
        
        return {
            'center': [x0, y0, z0],
            'radius': radius,
            'sphericity_error': sphericity_error,
            'max_distance': np.max(distances),
            'min_distance': np.min(distances),
            'mean_distance': np.mean(distances),
            'std_distance': np.std(distances)
        }
    
    def full_analysis(self, points: np.ndarray) -> Dict:
        """
        完整分析流程
        """
        print(f"\n{'='*70}")
        print("HRG谐振陀螺完整分析")
        print(f"{'='*70}")
        print(f"总点数: {len(points):,}")
        
        # 1. 区域分割
        hrg_points, assembly_points, bottom_plane = self.segment_hrg_and_assembly(points)
        
        results = {
            'segmentation': {
                'hrg_points': len(hrg_points),
                'assembly_points': len(assembly_points),
                'bottom_plane_points': len(bottom_plane)
            }
        }
        
        # 2. 装配误差分析
        if len(bottom_plane) > 0:
            assembly_error = self.analyze_assembly_error(hrg_points, bottom_plane)
            results['assembly_error'] = assembly_error
        
        # 3. 圆度误差分析
        roundness = self.analyze_roundness(hrg_points)
        results['roundness'] = roundness
        
        # 4. 球度误差分析(仅谐振陀螺)
        sphericity = self.analyze_sphericity_hrg_only(hrg_points)
        results['sphericity_hrg'] = sphericity
        
        return results
