"""
聚类分割算法
基于聚类方法的点云分割
"""
import numpy as np
from typing import List, Tuple
from sklearn.cluster import DBSCAN


def clustering_segmentation(
    points: np.ndarray,
    eps: float = 0.5,
    min_samples: int = 10,
    method: str = 'dbscan'
) -> List[np.ndarray]:
    """
    基于聚类的点云分割
    
    Args:
        points: 点云数组，形状为(n, 3)
        eps: DBSCAN邻域半径
        min_samples: DBSCAN最小样本数
        method: 聚类方法
        
    Returns:
        聚类簇列表，每个元素为一个簇的点云
    """
    points = np.asarray(points)
    
    if method == 'dbscan':
        clustering = DBSCAN(eps=eps, min_samples=min_samples)
        labels = clustering.fit_predict(points)
    else:
        raise ValueError(f"不支持的聚类方法：{method}")
    
    unique_labels = np.unique(labels)
    unique_labels = unique_labels[unique_labels != -1]
    
    clusters = []
    for label in unique_labels:
        mask = labels == label
        clusters.append(points[mask])
    
    return clusters
