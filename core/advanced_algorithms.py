"""
高级几何评定算法模块
实现符合国标的高精度圆度和球度评定算法

包含：
1. 改进Kasa代数球拟合法
2. 圆心搜索算法（变步长策略）
3. Gauss-Newton迭代优化
4. 最小区域法评定

符合标准：
- GB/T 7235-2004 圆度测量
- GB/T 24630-2009 球度测量

作者: Point Cloud Analysis Team
版本: 2.0.0
"""

import numpy as np
from scipy.optimize import minimize
import logging
from typing import Tuple, Dict, Optional


class AdvancedGeometryAnalyzer:
    """
    高级几何评定算法类
    
    实现符合国标的高精度几何误差评定算法
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        初始化高级分析器
        
        参数:
            logger: 日志记录器
        """
        self.logger = logger or logging.getLogger('AdvancedGeometryAnalyzer')
    
    # ==================== 改进Kasa代数球拟合 ====================
    
    def improved_kasa_sphere_fit(self, points: np.ndarray) -> Tuple[np.ndarray, float, Dict]:
        """
        改进Kasa代数球拟合法
        
        算法说明:
            传统Kasa方法对球心偏移敏感，改进版本通过坐标平移提高数值稳定性
            
        参数:
            points: 点云数据，Nx3数组
        
        返回:
            (球心坐标, 半径, 拟合信息字典)
        """
        self.logger.info("使用改进Kasa代数球拟合法")
        
        # 坐标平移到质心，提高数值稳定性
        centroid = np.mean(points, axis=0)
        points_centered = points - centroid
        
        # 构建设计矩阵
        x = points_centered[:, 0]
        y = points_centered[:, 1]
        z = points_centered[:, 2]
        
        # Kasa方法：最小化 ||x² + y² + z² - 2ax - 2by - 2cz - d||²
        A = np.column_stack([x, y, z, np.ones(len(points))])
        b = x**2 + y**2 + z**2
        
        # 使用SVD求解，提高数值稳定性
        U, S, Vt = np.linalg.svd(A, full_matrices=False)
        params = Vt.T @ np.diag(1/S) @ U.T @ b
        
        # 提取参数
        a, b_coef, c, d = params
        
        # 计算球心和半径
        center_centered = np.array([a, b_coef, c])
        radius_squared = a**2 + b_coef**2 + c**2 + d
        
        if radius_squared < 0:
            self.logger.warning("拟合失败，半径平方为负，使用传统方法")
            # 回退到传统最小二乘
            return self._traditional_sphere_fit(points)
        
        radius = np.sqrt(radius_squared)
        
        # 转换回原始坐标系
        center = center_centered + centroid
        
        # 计算拟合质量
        distances = np.linalg.norm(points - center, axis=1)
        residuals = distances - radius
        rmse = np.sqrt(np.mean(residuals**2))
        
        fit_info = {
            'method': 'Improved Kasa',
            'rmse': rmse,
            'max_residual': np.max(np.abs(residuals)),
            'centroid_shift': centroid
        }
        
        self.logger.info(f"改进Kasa拟合完成，RMSE: {rmse:.6f} mm")
        
        return center, radius, fit_info
    
    def _traditional_sphere_fit(self, points: np.ndarray) -> Tuple[np.ndarray, float, Dict]:
        """
        传统最小二乘球拟合（作为回退方法）
        """
        # 构建线性方程组
        A = np.column_stack([
            2 * points[:, 0],
            2 * points[:, 1],
            2 * points[:, 2],
            np.ones(len(points))
        ])
        b = points[:, 0]**2 + points[:, 1]**2 + points[:, 2]**2
        
        x, _, _, _ = np.linalg.lstsq(A, b, rcond=None)
        
        center = x[:3]
        radius = np.sqrt(x[3] + np.sum(center**2))
        
        distances = np.linalg.norm(points - center, axis=1)
        residuals = distances - radius
        rmse = np.sqrt(np.mean(residuals**2))
        
        fit_info = {
            'method': 'Traditional Least Squares',
            'rmse': rmse,
            'max_residual': np.max(np.abs(residuals))
        }
        
        return center, radius, fit_info
    
    # ==================== Gauss-Newton迭代优化 ====================
    
    def gauss_newton_sphere_optimization(self, points: np.ndarray,
                                        initial_center: np.ndarray,
                                        initial_radius: float,
                                        max_iterations: int = 3) -> Tuple[np.ndarray, float, Dict]:
        """
        Gauss-Newton迭代优化球拟合
        
        用法:
            以改进Kasa法结果为初值，进行1-3次迭代优化
        
        参数:
            points: 点云数据
            initial_center: 初始球心
            initial_radius: 初始半径
            max_iterations: 最大迭代次数
        
        返回:
            (优化球心, 优化半径, 优化信息字典)
        """
        self.logger.info(f"开始Gauss-Newton迭代优化，最大迭代次数: {max_iterations}")
        
        center = initial_center.copy()
        radius = initial_radius
        
        for iteration in range(max_iterations):
            # 计算残差和雅可比矩阵
            residuals = []
            jacobian = []
            
            for point in points:
                diff = point - center
                dist = np.linalg.norm(diff)
                
                # 残差
                residual = dist - radius
                residuals.append(residual)
                
                # 雅可比矩阵
                if dist > 1e-10:
                    jac = np.array([
                        -diff[0] / dist,
                        -diff[1] / dist,
                        -diff[2] / dist,
                        -1.0
                    ])
                else:
                    jac = np.array([0, 0, 0, -1.0])
                jacobian.append(jac)
            
            residuals = np.array(residuals)
            J = np.array(jacobian)
            
            # Gauss-Newton更新
            JTJ = J.T @ J
            JTr = J.T @ residuals
            
            try:
                delta = np.linalg.solve(JTJ, -JTr)
            except np.linalg.LinAlgError:
                self.logger.warning(f"迭代{iteration+1}: 矩阵奇异，停止迭代")
                break
            
            # 更新参数
            center += delta[:3]
            radius += delta[3]
            
            # 确保半径为正
            if radius <= 0:
                radius = initial_radius
                self.logger.warning(f"迭代{iteration+1}: 半径为负，恢复初始值")
                break
            
            # 计算当前RMSE
            current_rmse = np.sqrt(np.mean(residuals**2))
            self.logger.info(f"迭代{iteration+1}: RMSE = {current_rmse:.6f} mm")
        
        # 计算最终结果
        distances = np.linalg.norm(points - center, axis=1)
        final_residuals = distances - radius
        final_rmse = np.sqrt(np.mean(final_residuals**2))
        
        opt_info = {
            'method': 'Gauss-Newton Optimization',
            'iterations': iteration + 1,
            'rmse': final_rmse,
            'max_residual': np.max(np.abs(final_residuals)),
            'initial_rmse': np.sqrt(np.mean((np.linalg.norm(points - initial_center, axis=1) - initial_radius)**2))
        }
        
        self.logger.info(f"Gauss-Newton优化完成，最终RMSE: {final_rmse:.6f} mm")
        
        return center, radius, opt_info
    
    # ==================== 圆心搜索算法（变步长策略） ====================
    
    def circle_center_search(self, points_2d: np.ndarray,
                            initial_center: np.ndarray,
                            initial_radius: float,
                            initial_roundness: float,
                            coarse_step: float = 0.0001,  # 100nm
                            fine_step: float = 0.00001,   # 10nm
                            search_range_factor: float = 5.0) -> Tuple[np.ndarray, float, Dict]:
        """
        圆心搜索算法（变步长策略）
        
        算法说明:
            1. 以LSC结果为初始值
            2. 搜索范围覆盖LSC圆心±5倍初始圆度误差
            3. 大步长粗搜 + 小步长精搜
        
        参数:
            points_2d: 2D点集
            initial_center: 初始圆心（LSC结果）
            initial_radius: 初始半径
            initial_roundness: 初始圆度误差
            coarse_step: 粗搜索步长（默认100nm）
            fine_step: 精搜索步长（默认10nm）
            search_range_factor: 搜索范围因子
        
        返回:
            (最优圆心, 最优半径, 搜索信息字典)
        """
        self.logger.info("开始圆心搜索算法（变步长策略）")
        self.logger.info(f"初始圆度误差: {initial_roundness:.6f} mm")
        self.logger.info(f"搜索范围: ±{search_range_factor * initial_roundness:.6f} mm")
        
        # 计算搜索范围
        search_range = search_range_factor * initial_roundness
        
        # 阶段1：大步长粗搜
        self.logger.info(f"阶段1：粗搜索，步长 {coarse_step*1000:.1f} nm")
        best_center, best_radius, best_roundness = self._grid_search(
            points_2d, initial_center, search_range, coarse_step
        )
        
        # 阶段2：小步长精搜
        self.logger.info(f"阶段2：精搜索，步长 {fine_step*1000:.1f} nm")
        # 在粗搜索结果附近进行精搜索
        fine_search_range = coarse_step * 2
        best_center, best_radius, best_roundness = self._grid_search(
            points_2d, best_center, fine_search_range, fine_step
        )
        
        search_info = {
            'method': 'Circle Center Search',
            'initial_roundness': initial_roundness,
            'final_roundness': best_roundness,
            'improvement': initial_roundness - best_roundness,
            'coarse_step': coarse_step,
            'fine_step': fine_step,
            'search_range': search_range
        }
        
        self.logger.info(f"圆心搜索完成，圆度误差: {initial_roundness:.6f} -> {best_roundness:.6f} mm")
        self.logger.info(f"改进量: {search_info['improvement']:.6f} mm")
        
        return best_center, best_radius, search_info
    
    def _grid_search(self, points_2d: np.ndarray,
                     center: np.ndarray,
                     search_range: float,
                     step: float) -> Tuple[np.ndarray, float, float]:
        """
        网格搜索最优圆心
        """
        best_center = center.copy()
        best_radius = 0
        best_roundness = float('inf')
        
        # 生成搜索网格
        num_steps = int(np.ceil(search_range / step))
        x_offsets = np.linspace(-search_range, search_range, 2*num_steps+1)
        y_offsets = np.linspace(-search_range, search_range, 2*num_steps+1)
        
        for dx in x_offsets:
            for dy in y_offsets:
                # 测试圆心
                test_center = center + np.array([dx, dy])
                
                # 计算半径和圆度
                distances = np.linalg.norm(points_2d - test_center, axis=1)
                test_radius = np.mean(distances)
                test_roundness = np.max(distances) - np.min(distances)
                
                if test_roundness < best_roundness:
                    best_roundness = test_roundness
                    best_center = test_center
                    best_radius = test_radius
        
        return best_center, best_radius, best_roundness
    
    # ==================== 最小区域法评定 ====================
    
    def minimum_zone_sphericity(self, points: np.ndarray,
                               initial_center: np.ndarray,
                               initial_radius: float) -> Tuple[float, Dict]:
        """
        最小区域法球度评定
        
        算法说明:
            寻找两个同心球，将所有点夹在中间，且半径差最小
        
        参数:
            points: 点云数据
            initial_center: 初始球心
            initial_radius: 初始半径
        
        返回:
            (球度误差, 评定信息字典)
        """
        self.logger.info("开始最小区域法球度评定")
        
        # 定义优化目标函数
        def objective(params):
            center = params[:3]
            distances = np.linalg.norm(points - center, axis=1)
            return np.max(distances) - np.min(distances)
        
        # 初始参数
        x0 = np.concatenate([initial_center, [initial_radius]])
        
        # 优化
        result = minimize(
            objective,
            x0,
            method='Nelder-Mead',
            options={'maxiter': 1000, 'xatol': 1e-6}
        )
        
        optimal_center = result.x[:3]
        distances = np.linalg.norm(points - optimal_center, axis=1)
        sphericity_error = np.max(distances) - np.min(distances)
        
        mz_info = {
            'method': 'Minimum Zone',
            'optimal_center': optimal_center,
            'outer_radius': np.max(distances),
            'inner_radius': np.min(distances),
            'optimization_success': result.success,
            'function_evaluations': result.nfev
        }
        
        self.logger.info(f"最小区域法评定完成，球度误差: {sphericity_error:.6f} mm")
        
        return sphericity_error, mz_info
    
    def minimum_zone_roundness(self, points_2d: np.ndarray,
                               initial_center: np.ndarray) -> Tuple[float, Dict]:
        """
        最小区域法圆度评定
        
        参数:
            points_2d: 2D点集
            initial_center: 初始圆心
        
        返回:
            (圆度误差, 评定信息字典)
        """
        self.logger.info("开始最小区域法圆度评定")
        
        # 定义优化目标函数
        def objective(center):
            distances = np.linalg.norm(points_2d - center, axis=1)
            return np.max(distances) - np.min(distances)
        
        # 优化
        result = minimize(
            objective,
            initial_center,
            method='Nelder-Mead',
            options={'maxiter': 1000, 'xatol': 1e-6}
        )
        
        optimal_center = result.x
        distances = np.linalg.norm(points_2d - optimal_center, axis=1)
        roundness_error = np.max(distances) - np.min(distances)
        
        mz_info = {
            'method': 'Minimum Zone',
            'optimal_center': optimal_center,
            'outer_radius': np.max(distances),
            'inner_radius': np.min(distances),
            'optimization_success': result.success,
            'function_evaluations': result.nfev
        }
        
        self.logger.info(f"最小区域法评定完成，圆度误差: {roundness_error:.6f} mm")
        
        return roundness_error, mz_info
    
    # ==================== 国标输出格式 ====================
    
    def generate_gb_report(self, 
                          sphericity_ls: float,
                          sphericity_mz: Optional[float],
                          roundness_ls: float,
                          roundness_mz: Optional[float],
                          metadata: Dict) -> Dict:
        """
        生成符合国标的评定报告
        
        符合标准:
            - GB/T 7235-2004 圆度测量
            - GB/T 24630-2009 球度测量
        
        参数:
            sphericity_ls: 最小二乘法球度误差
            sphericity_mz: 最小区域法球度误差（可选）
            roundness_ls: 最小二乘法圆度误差
            roundness_mz: 最小区域法圆度误差（可选）
            metadata: 元数据
        
        返回:
            国标格式报告字典
        """
        report = {
            'standard': {
                'sphericity': 'GB/T 24630-2009',
                'roundness': 'GB/T 7235-2004'
            },
            'sphericity': {
                'least_squares': {
                    'value': sphericity_ls,
                    'unit': 'mm',
                    'description': '最小二乘球拟合法评定结果'
                },
                'minimum_zone': {
                    'value': sphericity_mz,
                    'unit': 'mm',
                    'description': '最小区域法评定结果（仲裁级精度）'
                } if sphericity_mz is not None else None
            },
            'roundness': {
                'least_squares': {
                    'value': roundness_ls,
                    'unit': 'mm',
                    'description': '最小二乘圆拟合法评定结果'
                },
                'minimum_zone': {
                    'value': roundness_mz,
                    'unit': 'mm',
                    'description': '最小区域法评定结果（仲裁级精度）'
                } if roundness_mz is not None else None
            },
            'metadata': metadata,
            'note': '最小区域法结果为仲裁级精度，建议用于最终评定'
        }
        
        return report
