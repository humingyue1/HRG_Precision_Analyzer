"""
HRG振子点云完整处理分析流程
=====================================
流程：处理点云 → 数据分析 → STL对比
支持多进程加速处理

作者: HRG Analysis Team
版本: 1.0.0
"""

import numpy as np
import trimesh
import matplotlib.pyplot as plt
from matplotlib import cm
from mpl_toolkits.mplot3d import Axes3D
import open3d as o3d
from advanced_algorithms import AdvancedGeometryAnalyzer
import json
import time
import os
from multiprocessing import Pool, cpu_count
from typing import Tuple, Dict, Optional
import warnings
warnings.filterwarnings('ignore')

# 设置matplotlib
plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False


# ==================== 阶段1: 点云处理 ====================

class PointCloudProcessor:
    """点云预处理模块"""
    
    def __init__(self, num_processes: int = None):
        self.num_processes = num_processes or max(1, cpu_count() - 1)
        print(f"点云处理器初始化，使用 {self.num_processes} 个进程")
    
    def load_asc_file(self, file_path: str, sample_rate: int = 50) -> np.ndarray:
        """
        加载ASC文件并进行单位转换
        
        参数:
            file_path: ASC文件路径
            sample_rate: 采样率（每N个点取1个）
        """
        print(f"\n{'='*70}")
        print("阶段1.1: 加载ASC点云数据")
        print(f"{'='*70}")
        print(f"文件: {file_path}")
        print(f"采样率: 1/{sample_rate}")

        start_time = time.time()
        points_list = []

        # 读取文件头信息
        x_size = 0
        y_size = 0
        pixel_size = 0.001  # 默认值
        file_format = 1  # 默认格式1（索引格式）

        # Try to find RAW_DATA marker
        raw_data_found = False
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                if 'RAW_DATA' in line:
                    raw_data_found = True
                    break

        if raw_data_found:
            # Wyko ASC format
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                first_line = f.readline().strip()
                if 'Format 2' in first_line:
                    file_format = 2

                for i in range(19):
                    line = f.readline().strip()
                    if 'X Size' in line:
                        parts = line.split()
                        x_size = int(parts[-1])
                    elif 'Y Size' in line:
                        parts = line.split()
                        y_size = int(parts[-1])
                    elif 'Pixel_size' in line:
                        parts = line.split()
                        pixel_size = float(parts[-1])
                    elif 'RAW_DATA' in line:
                        break

            print(f"  文件格式: Wyko ASC Format {file_format} ({'X/Y已是mm' if file_format == 2 else 'X/Y是索引'})")
            print(f"  图像尺寸: {x_size} x {y_size}")
            print(f"  像素大小: {pixel_size} mm")

            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    if 'RAW_DATA' in line:
                        break

                count = 0
                for line in f:
                    count += 1
                    line = line.strip()

                    if not line or 'Bad' in line or 'Intensity' in line:
                        continue

                    if count % sample_rate != 0:
                        continue

                    parts = line.split()
                    if len(parts) >= 3:
                        try:
                            if file_format == 2:
                                x = float(parts[0])
                                y = float(parts[1])
                                z = float(parts[2]) / 1e6
                            else:
                                ix = int(parts[0])
                                iy = int(parts[1])
                                z_nm = float(parts[2])
                                x = ix * pixel_size
                                y = iy * pixel_size
                                z = z_nm / 1e6
                            points_list.append([x, y, z])
                        except:
                            pass

                    if count % 10000000 == 0:
                        print(f"  已读取 {count:,} 行, 提取 {len(points_list):,} 点...")
        else:
            # Simple XYZ format: X(mm) Y(mm) Z(mm)
            print(f"  文件格式: Simple XYZ (X Y Z in mm)")
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                count = 0
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    count += 1
                    if count % sample_rate != 0:
                        continue
                    parts = line.split()
                    if len(parts) >= 3:
                        try:
                            x = float(parts[0])
                            y = float(parts[1])
                            z = float(parts[2])
                            points_list.append([x, y, z])
                        except:
                            pass
                    if count % 10000000 == 0:
                        print(f"  已读取 {count:,} 行, 提取 {len(points_list):,} 点...")

        points = np.array(points_list)
        elapsed = time.time() - start_time

        print(f"\n加载完成:")
        print(f"  点数: {len(points):,}")

        if len(points) > 0:
            print(f"  X范围: [{points[:,0].min():.3f}, {points[:,0].max():.3f}] mm")
            print(f"  Y范围: [{points[:,1].min():.3f}, {points[:,1].max():.3f}] mm")
            print(f"  Z范围: [{points[:,2].min():.3f}, {points[:,2].max():.3f}] mm")
        print(f"  耗时: {elapsed:.1f} 秒")

        return points
    
    def remove_plane(self, points: np.ndarray, z_threshold: float = -0.1) -> np.ndarray:
        """
        删除半球上方的平面部分
        
        参数:
            points: 点云数据
            z_threshold: Z轴阈值，高于此值的点将被删除
        """
        print(f"\n{'='*70}")
        print("阶段1.2: 删除平面部分")
        print(f"{'='*70}")
        
        start_time = time.time()
        
        # 统计平面区域
        plane_mask = points[:, 2] > z_threshold
        hemisphere_mask = points[:, 2] <= z_threshold
        
        plane_count = np.sum(plane_mask)
        hemisphere_points = points[hemisphere_mask]
        
        print(f"  Z阈值: {z_threshold} mm")
        print(f"  删除平面点数: {plane_count:,}")
        print(f"  保留半球点数: {len(hemisphere_points):,}")
        print(f"  耗时: {time.time() - start_time:.1f} 秒")
        
        return hemisphere_points
    
    def denoise_parallel(self, points: np.ndarray, 
                         nb_neighbors: int = 30, 
                         std_ratio: float = 2.0) -> np.ndarray:
        """
        多进程去噪处理
        
        参数:
            points: 点云数据
            nb_neighbors: 邻近点数
            std_ratio: 标准差比率
        """
        print(f"\n{'='*70}")
        print("阶段1.3: 统计滤波去噪")
        print(f"{'='*70}")
        
        start_time = time.time()
        
        # 使用Open3D进行去噪
        pcd = o3d.geometry.PointCloud()
        pcd.points = o3d.utility.Vector3dVector(points)
        
        filtered_pcd, _ = pcd.remove_statistical_outlier(
            nb_neighbors=nb_neighbors, 
            std_ratio=std_ratio
        )
        
        filtered_points = np.asarray(filtered_pcd.points)
        
        print(f"  原始点数: {len(points):,}")
        print(f"  去噪后点数: {len(filtered_points):,}")
        print(f"  删除噪声点: {len(points) - len(filtered_points):,}")
        print(f"  耗时: {time.time() - start_time:.1f} 秒")
        
        return filtered_points
    
    def process_pipeline(self, asc_path: str, 
                        sample_rate: int = 50,
                        z_threshold: float = -0.1,
                        save_intermediate: bool = True) -> np.ndarray:
        """
        完整的点云处理流程
        """
        print(f"\n{'='*70}")
        print("阶段1: 点云预处理")
        print(f"{'='*70}")
        
        total_start = time.time()
        
        # 1. 加载ASC文件
        points = self.load_asc_file(asc_path, sample_rate)
        
        # 2. 删除平面
        points = self.remove_plane(points, z_threshold)
        
        # 3. 去噪
        points = self.denoise_parallel(points)
        
        # 保存中间结果
        if save_intermediate:
            output_path = "output/zp1_processed.xyz"
            np.savetxt(output_path, points, fmt="%.6f", delimiter=" ")
            print(f"\n  已保存处理后的点云: {output_path}")
        
        print(f"\n阶段1完成，总耗时: {time.time() - total_start:.1f} 秒")
        
        return points


# ==================== 阶段2: 数据分析 ====================

class DataAnalyzer:
    """数据分析模块"""
    
    def __init__(self):
        self.geometry_analyzer = AdvancedGeometryAnalyzer()
    
    def analyze_sphericity(self, points: np.ndarray) -> Dict:
        """
        球度分析
        """
        print(f"\n{'='*70}")
        print("阶段2.1: 球度分析")
        print(f"{'='*70}")
        
        start_time = time.time()
        
        # 球拟合
        center, radius, info = self.geometry_analyzer.improved_kasa_sphere_fit(points)
        
        # 计算球度误差
        distances = np.linalg.norm(points - center, axis=1)
        sphericity_error = np.max(distances) - np.min(distances)
        
        result = {
            'center': center,
            'radius': radius,
            'sphericity_error': sphericity_error,
            'max_distance': np.max(distances),
            'min_distance': np.min(distances),
            'mean_distance': np.mean(distances),
            'std_distance': np.std(distances),
            'rmse': info.get('rmse', 0)
        }
        
        print(f"  拟合球心: [{center[0]:.6f}, {center[1]:.6f}, {center[2]:.6f}] mm")
        print(f"  拟合半径: {radius:.6f} mm")
        print(f"  球度误差: {sphericity_error:.6f} mm ({sphericity_error*1000:.3f} μm)")
        print(f"  耗时: {time.time() - start_time:.1f} 秒")
        
        return result
    
    def analyze_geometry(self, points: np.ndarray) -> Dict:
        """
        几何特征分析
        """
        print(f"\n{'='*70}")
        print("阶段2.2: 几何特征分析")
        print(f"{'='*70}")
        
        start_time = time.time()
        
        # 基本统计
        centroid = np.mean(points, axis=0)
        x_span = points[:, 0].max() - points[:, 0].min()
        y_span = points[:, 1].max() - points[:, 1].min()
        z_span = points[:, 2].max() - points[:, 2].min()
        
        # 计算主成分
        centered = points - centroid
        cov = np.cov(centered.T)
        eigenvalues, eigenvectors = np.linalg.eigh(cov)
        
        result = {
            'centroid': centroid,
            'x_span': x_span,
            'y_span': y_span,
            'z_span': z_span,
            'xy_ratio': x_span / y_span,
            'eigenvalues': eigenvalues,
            'point_count': len(points)
        }
        
        print(f"  质心: [{centroid[0]:.3f}, {centroid[1]:.3f}, {centroid[2]:.3f}] mm")
        print(f"  X跨度: {x_span:.3f} mm")
        print(f"  Y跨度: {y_span:.3f} mm")
        print(f"  Z跨度: {z_span:.3f} mm")
        print(f"  X/Y比: {x_span/y_span:.3f}")
        print(f"  耗时: {time.time() - start_time:.1f} 秒")
        
        return result
    
    def analyze_pipeline(self, points: np.ndarray) -> Dict:
        """
        完整的数据分析流程
        """
        print(f"\n{'='*70}")
        print("阶段2: 数据分析")
        print(f"{'='*70}")
        
        total_start = time.time()
        
        results = {}
        
        # 1. 球度分析
        results['sphericity'] = self.analyze_sphericity(points)
        
        # 2. 几何特征分析
        results['geometry'] = self.analyze_geometry(points)
        
        print(f"\n阶段2完成，总耗时: {time.time() - total_start:.1f} 秒")
        
        return results


# ==================== 阶段3: STL对比 ====================

class STLComparator:
    """STL模型对比模块"""
    
    def __init__(self, stl_path: str):
        self.stl_path = stl_path
        self.ideal_mesh = None
    
    def load_stl(self):
        """加载STL模型"""
        print(f"\n{'='*70}")
        print("阶段3.1: 加载STL理想模型")
        print(f"{'='*70}")
        
        if os.path.exists(self.stl_path):
            self.ideal_mesh = trimesh.load(self.stl_path)
            print(f"  已加载: {self.stl_path}")
            print(f"  顶点数: {len(self.ideal_mesh.vertices):,}")
            print(f"  面数: {len(self.ideal_mesh.faces):,}")
        else:
            print(f"  [WARNING] STL文件不存在: {self.stl_path}")
    
    def compute_deviation(self, points: np.ndarray) -> np.ndarray:
        """
        计算点云与理想模型的偏差
        """
        print(f"\n{'='*70}")
        print("阶段3.2: 计算模型偏差")
        print(f"{'='*70}")
        
        if self.ideal_mesh is None:
            print("  [WARNING] 未加载STL模型，跳过偏差计算")
            return None
        
        start_time = time.time()
        
        # 计算每个点到模型表面的最近距离
        closest, distances, _ = trimesh.proximity.closest_point(
            self.ideal_mesh, points
        )
        
        print(f"  偏差范围: [{distances.min()*1000:.3f}, {distances.max()*1000:.3f}] μm")
        print(f"  平均偏差: {np.mean(distances)*1000:.3f} μm")
        print(f"  标准差: {np.std(distances)*1000:.3f} μm")
        print(f"  耗时: {time.time() - start_time:.1f} 秒")
        
        return distances
    
    def compare_pipeline(self, points: np.ndarray) -> Dict:
        """
        完整的STL对比流程
        """
        print(f"\n{'='*70}")
        print("阶段3: STL模型对比")
        print(f"{'='*70}")
        
        total_start = time.time()
        
        results = {}
        
        # 1. 加载STL
        self.load_stl()
        
        # 2. 计算偏差
        deviations = self.compute_deviation(points)
        
        if deviations is not None:
            results['deviations'] = {
                'min': np.min(deviations),
                'max': np.max(deviations),
                'mean': np.mean(deviations),
                'std': np.std(deviations)
            }
        
        print(f"\n阶段3完成，总耗时: {time.time() - total_start:.1f} 秒")
        
        return results


# ==================== 可视化模块 ====================

class Visualizer:
    """可视化模块"""
    
    def __init__(self, output_dir: str = "output"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
    
    def visualize_3d(self, points: np.ndarray, title: str, filename: str):
        """3D可视化"""
        print(f"\n绘制3D视图: {filename}")
        
        fig = plt.figure(figsize=(16, 12))
        
        views = [
            {'name': 'Isometric', 'elev': 30, 'azim': 45},
            {'name': 'Front (X-Z)', 'elev': 0, 'azim': 0},
            {'name': 'Top (X-Y)', 'elev': 90, 'azim': 0},
            {'name': 'Side (Y-Z)', 'elev': 0, 'azim': 90}
        ]
        
        for i, view in enumerate(views, 1):
            ax = fig.add_subplot(2, 2, i, projection='3d')
            
            # Z值着色
            z_norm = (points[:, 2] - points[:, 2].min()) / (points[:, 2].max() - points[:, 2].min() + 1e-10)
            colors = cm.coolwarm(z_norm)
            
            ax.scatter(points[:, 0], points[:, 1], points[:, 2],
                      c=colors, s=0.5, alpha=0.6)
            
            ax.set_xlabel('X (mm)')
            ax.set_ylabel('Y (mm)')
            ax.set_zlabel('Z (mm)')
            ax.set_title(view['name'])
            ax.view_init(elev=view['elev'], azim=view['azim'])
        
        fig.suptitle(f'{title}\nPoints: {len(points):,}', fontsize=14)
        plt.tight_layout()
        plt.savefig(os.path.join(self.output_dir, filename), dpi=200)
        plt.close()
    
    def visualize_sphericity(self, points: np.ndarray, 
                            sphericity_result: Dict, 
                            filename: str):
        """球度误差可视化"""
        print(f"\n绘制球度可视化: {filename}")
        
        fig = plt.figure(figsize=(18, 6))
        
        center = sphericity_result['center']
        radius = sphericity_result['radius']
        distances = np.linalg.norm(points - center, axis=1)
        deviations = (distances - radius) * 1000  # μm
        
        # 3D偏差着色
        ax1 = fig.add_subplot(131, projection='3d')
        scatter = ax1.scatter(points[:, 0], points[:, 1], points[:, 2],
                             c=deviations, cmap='RdBu', s=0.5, alpha=0.6)
        plt.colorbar(scatter, ax=ax1, shrink=0.6, label='Deviation (μm)')
        ax1.set_xlabel('X (mm)')
        ax1.set_ylabel('Y (mm)')
        ax1.set_zlabel('Z (mm)')
        ax1.set_title('Sphericity Error Distribution')
        
        # 距离分布
        ax2 = fig.add_subplot(132)
        ax2.hist(distances, bins=50, color='steelblue', alpha=0.7, edgecolor='black')
        ax2.axvline(radius, color='red', linestyle='--', linewidth=2, 
                   label=f'R = {radius:.3f} mm')
        ax2.set_xlabel('Distance to Center (mm)')
        ax2.set_ylabel('Count')
        ax2.set_title('Distance Distribution')
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        
        # 统计信息
        ax3 = fig.add_subplot(133)
        stats_text = f"""
Sphericity Analysis (GB/T 24630-2009)
{'='*40}

Fitted Center:
  X: {center[0]:.6f} mm
  Y: {center[1]:.6f} mm
  Z: {center[2]:.6f} mm

Fitted Radius: {radius:.6f} mm

Sphericity Error: {sphericity_result['sphericity_error']*1000:.3f} μm

Max Deviation: {np.max(deviations):.3f} μm
Min Deviation: {np.min(deviations):.3f} μm
Mean Deviation: {np.mean(deviations):.3f} μm
Std Deviation: {np.std(deviations):.3f} μm
"""
        ax3.text(0.1, 0.5, stats_text, fontsize=10, family='monospace', 
                verticalalignment='center')
        ax3.axis('off')
        ax3.set_title('Statistics')
        
        plt.tight_layout()
        plt.savefig(os.path.join(self.output_dir, filename), dpi=200)
        plt.close()
    
    def visualize_deviation(self, points: np.ndarray, 
                           deviations: np.ndarray, 
                           filename: str):
        """偏差分布可视化"""
        if deviations is None:
            return
        
        print(f"\n绘制偏差可视化: {filename}")
        
        fig = plt.figure(figsize=(14, 10))
        ax = fig.add_subplot(111, projection='3d')
        
        deviations_um = deviations * 1000
        
        scatter = ax.scatter(points[:, 0], points[:, 1], points[:, 2],
                            c=deviations_um, cmap='RdBu', s=1, alpha=0.6)
        
        cbar = plt.colorbar(scatter, ax=ax, shrink=0.6)
        cbar.set_label('Deviation (μm)', fontsize=12)
        
        ax.set_xlabel('X (mm)', fontsize=12)
        ax.set_ylabel('Y (mm)', fontsize=12)
        ax.set_zlabel('Z (mm)', fontsize=12)
        ax.set_title('Deviation from Ideal Model', fontsize=14)
        
        plt.tight_layout()
        plt.savefig(os.path.join(self.output_dir, filename), dpi=200)
        plt.close()


# ==================== 主流程 ====================

class CompletePipeline:
    """完整处理流程"""
    
    def __init__(self, 
                 asc_path: str,
                 stl_path: str = "micro shell48.STL",
                 num_processes: int = None):
        
        self.asc_path = asc_path
        self.stl_path = stl_path
        
        # 初始化各模块
        self.processor = PointCloudProcessor(num_processes)
        self.analyzer = DataAnalyzer()
        self.comparator = STLComparator(stl_path)
        self.visualizer = Visualizer()
    
    def run(self, 
            sample_rate: int = 50,
            z_threshold: float = -0.1):
        """
        运行完整流程
        """
        print(f"\n{'='*70}")
        print("HRG振子点云完整处理分析流程")
        print(f"{'='*70}")
        print(f"ASC文件: {self.asc_path}")
        print(f"STL文件: {self.stl_path}")
        
        total_start = time.time()
        
        # 阶段1: 点云处理
        points = self.processor.process_pipeline(
            self.asc_path, 
            sample_rate=sample_rate,
            z_threshold=z_threshold
        )
        
        # 阶段2: 数据分析
        analysis_results = self.analyzer.analyze_pipeline(points)
        
        # 阶段3: STL对比
        comparison_results = self.comparator.compare_pipeline(points)
        
        # 可视化
        print(f"\n{'='*70}")
        print("生成可视化结果")
        print(f"{'='*70}")
        
        self.visualizer.visualize_3d(points, "Processed Point Cloud", "point_cloud_3d.png")
        self.visualizer.visualize_sphericity(points, analysis_results['sphericity'], "sphericity.png")
        
        if 'deviations' in comparison_results:
            deviations = comparison_results['deviations']
            # 重新计算偏差数组用于可视化
            if self.comparator.ideal_mesh is not None:
                _, dist, _ = trimesh.proximity.closest_point(self.comparator.ideal_mesh, points)
                self.visualizer.visualize_deviation(points, dist, "deviation.png")
        
        # 生成报告
        self._generate_report(points, analysis_results, comparison_results, 
                             time.time() - total_start)
        
        print(f"\n{'='*70}")
        print("分析完成")
        print(f"{'='*70}")
        print(f"总耗时: {time.time() - total_start:.1f} 秒")
        print(f"\n输出文件:")
        print(f"  - output/zp1_processed.xyz")
        print(f"  - output/point_cloud_3d.png")
        print(f"  - output/sphericity.png")
        print(f"  - output/deviation.png")
        print(f"  - output/analysis_report.json")
    
    def _generate_report(self, points, analysis_results, comparison_results, elapsed):
        """生成分析报告"""
        report = {
            "Analysis Report": {
                "Data File": self.asc_path,
                "Standard": {
                    "Sphericity": "GB/T 24630-2009",
                    "Roundness": "GB/T 7235-2004"
                },
                "Data Statistics": {
                    "Total Points": len(points),
                    "X Range (mm)": [float(points[:, 0].min()), float(points[:, 0].max())],
                    "Y Range (mm)": [float(points[:, 1].min()), float(points[:, 1].max())],
                    "Z Range (mm)": [float(points[:, 2].min()), float(points[:, 2].max())]
                },
                "Sphericity Analysis": {
                    "Fitted Center (mm)": analysis_results['sphericity']['center'].tolist(),
                    "Fitted Radius (mm)": float(analysis_results['sphericity']['radius']),
                    "Sphericity Error (μm)": float(analysis_results['sphericity']['sphericity_error'] * 1000)
                },
                "Geometry Analysis": {
                    "Centroid (mm)": analysis_results['geometry']['centroid'].tolist(),
                    "X Span (mm)": float(analysis_results['geometry']['x_span']),
                    "Y Span (mm)": float(analysis_results['geometry']['y_span']),
                    "Z Span (mm)": float(analysis_results['geometry']['z_span'])
                },
                "Model Comparison": comparison_results.get('deviations', {}),
                "Analysis Time (seconds)": f"{elapsed:.2f}"
            }
        }
        
        with open("output/analysis_report.json", "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"\n报告已保存: output/analysis_report.json")


# ==================== 主程序 ====================

def main():
    """主程序"""
    
    # 创建输出目录
    os.makedirs("output", exist_ok=True)
    
    # 创建处理流程
    pipeline = CompletePipeline(
        asc_path="zp1.ASC",
        stl_path="micro shell48.STL",
        num_processes=None  # 自动检测CPU核心数
    )
    
    # 运行完整流程
    pipeline.run(
        sample_rate=50,      # 采样率
        z_threshold=-0.1     # 平面删除阈值
    )


if __name__ == "__main__":
    main()
