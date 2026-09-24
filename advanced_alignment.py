"""
高级点云对齐工具
提供多种对齐策略,解决ICP配准问题
"""

import numpy as np
from scipy.spatial import cKDTree
from scipy.linalg import svd

def best_fit_transform(A, B):
    """
    计算最佳刚体变换(使用SVD)
    将A变换到B
    
    Returns:
        R: 旋转矩阵
        t: 平移向量
    """
    assert A.shape == B.shape
    
    # 计算重心
    centroid_A = np.mean(A, axis=0)
    centroid_B = np.mean(B, axis=0)
    
    # 中心化
    AA = A - centroid_A
    BB = B - centroid_B
    
    # 计算旋转矩阵
    H = AA.T @ BB
    U, S, Vt = svd(H)
    R = Vt.T @ U.T
    
    # 处理反射情况
    if np.linalg.det(R) < 0:
        Vt[2, :] *= -1
        R = Vt.T @ U.T
    
    # 计算平移
    t = centroid_B - R @ centroid_A
    
    return R, t

def icp(A, B, max_iterations=50, tolerance=1e-6):
    """
    ICP算法
    
    Args:
        A: 源点云
        B: 目标点云
        max_iterations: 最大迭代次数
        tolerance: 收敛阈值
        
    Returns:
        T: 变换矩阵
        distances: 最终距离
        i: 迭代次数
    """
    # 确保是numpy数组
    A = np.array(A)
    B = np.array(B)
    
    # 初始化
    m = A.shape[1]
    
    # 创建KD树
    tree = cKDTree(B)
    
    # 初始变换
    T = np.eye(m+1)
    
    # 复制点云
    A_transformed = A.copy()
    
    distances = np.zeros(A.shape[0])
    
    for i in range(max_iterations):
        # 找最近点
        distances, indices = tree.query(A_transformed)
        
        # 计算变换
        R, t = best_fit_transform(A_transformed, B[indices])
        
        # 应用变换
        A_transformed = (R @ A_transformed.T).T + t
        
        # 更新变换矩阵
        T_new = np.eye(m+1)
        T_new[:m, :m] = R
        T_new[:m, m] = t
        T = T_new @ T
        
        # 检查收敛
        mean_error = np.mean(distances)
        if i > 0 and abs(prev_error - mean_error) < tolerance:
            break
        prev_error = mean_error
    
    return T, distances, i

def try_multiple_alignments(asc_points, stl_points):
    """
    尝试多种对齐策略
    
    Returns:
        best_aligned: 最佳对齐结果
        best_error: 最佳误差
        strategy: 使用的策略
    """
    print("  尝试多种对齐策略...")
    
    strategies = []
    
    # 策略1: 直接ICP
    print("    策略1: 直接ICP...")
    T, distances, iters = icp(stl_points, asc_points, max_iterations=100)
    R = T[:3, :3]
    t = T[:3, 3]
    aligned1 = (R @ stl_points.T).T + t
    error1 = np.mean(distances)
    strategies.append(('直接ICP', aligned1, error1))
    print(f"      误差: {error1:.6f} mm")
    
    # 策略2: 先重心对齐,再ICP
    print("    策略2: 重心对齐 + ICP...")
    asc_center = np.mean(asc_points, axis=0)
    stl_center = np.mean(stl_points, axis=0)
    offset = asc_center - stl_center
    stl_centered = stl_points + offset
    
    T, distances, iters = icp(stl_centered, asc_points, max_iterations=100)
    R = T[:3, :3]
    t = T[:3, 3]
    aligned2 = (R @ stl_centered.T).T + t
    error2 = np.mean(distances)
    strategies.append(('重心+ICP', aligned2, error2))
    print(f"      误差: {error2:.6f} mm")
    
    # 策略3-6: 尝试不同旋转
    rotations = [
        ('旋转X90', np.array([[1,0,0], [0,0,-1], [0,1,0]])),
        ('旋转Y90', np.array([[0,0,1], [0,1,0], [-1,0,0]])),
        ('旋转Z90', np.array([[0,-1,0], [1,0,0], [0,0,1]])),
        ('旋转X180', np.array([[1,0,0], [0,-1,0], [0,0,-1]])),
    ]
    
    for name, R_init in rotations:
        print(f"    策略: {name} + ICP...")
        stl_rotated = (R_init @ stl_points.T).T
        
        # 重心对齐
        stl_center = np.mean(stl_rotated, axis=0)
        offset = asc_center - stl_center
        stl_rotated = stl_rotated + offset
        
        # ICP
        T, distances, iters = icp(stl_rotated, asc_points, max_iterations=100)
        R = T[:3, :3]
        t = T[:3, 3]
        aligned = (R @ stl_rotated.T).T + t
        error = np.mean(distances)
        strategies.append((name+'+ICP', aligned, error))
        print(f"      误差: {error:.6f} mm")
    
    # 选择最佳策略
    best_strategy = min(strategies, key=lambda x: x[2])
    
    print(f"\n  最佳策略: {best_strategy[0]}")
    print(f"  最佳误差: {best_strategy[2]:.6f} mm")
    
    return best_strategy[1], best_strategy[2], best_strategy[0]

if __name__ == '__main__':
    # 测试
    print("高级点云对齐工具")
    print("=" * 70)
