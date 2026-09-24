"""
HRG谐振陀螺加工精度分析系统 - 质量评价器
版本: v4.0
"""

import numpy as np
from typing import Optional, Dict, Any, List
# 支持相对导入和绝对导入
try:
    from .base_analyzer import BaseAnalyzer, QualityResult
    from .roughness_analyzer import RoughnessResult
    from .symmetry_analyzer import SymmetryResult
    from .thickness_analyzer import ThicknessResult
    from .waviness_analyzer import WavinessResult
    from .resonance_analyzer import ResonanceResult
except ImportError:
    from base_analyzer import BaseAnalyzer, QualityResult
    from roughness_analyzer import RoughnessResult
    from symmetry_analyzer import SymmetryResult
    from thickness_analyzer import ThicknessResult
    from waviness_analyzer import WavinessResult
    from resonance_analyzer import ResonanceResult


class QualityEvaluator(BaseAnalyzer):
    """
    质量评价器
    实现多指标加权评分和质量等级评定
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化质量评价器
        
        Args:
            config: 配置参数，包含：
                - weights: 各指标权重
                - grade_thresholds: 质量等级阈值
                - thresholds: 各指标阈值
        """
        super().__init__(config)
        
        # 默认权重
        self.weights = self.config.get('weights', {
            'roughness': 0.25,
            'symmetry': 0.25,
            'thickness': 0.20,
            'waviness': 0.15,
            'resonance': 0.15
        })
        
        # 默认等级阈值
        self.grade_thresholds = self.config.get('grade_thresholds', {
            'excellent': 90,
            'good': 75,
            'medium': 60
        })
        
        # 默认指标阈值
        self.thresholds = self.config.get('thresholds', {
            'roughness': {
                'ra_excellent': 0.4,
                'ra_good': 0.8,
                'ra_medium': 1.6
            },
            'symmetry': {
                'error_excellent': 0.01,
                'error_good': 0.02,
                'error_medium': 0.05
            },
            'thickness': {
                'uniformity_excellent': 0.02,
                'uniformity_good': 0.05,
                'uniformity_medium': 0.10
            }
        })
        
    def analyze(self, 
                roughness_result: Optional[RoughnessResult] = None,
                symmetry_result: Optional[SymmetryResult] = None,
                thickness_result: Optional[ThicknessResult] = None,
                waviness_result: Optional[WavinessResult] = None,
                resonance_result: Optional[ResonanceResult] = None) -> QualityResult:
        """
        执行质量评价
        
        Args:
            roughness_result: 粗糙度分析结果
            symmetry_result: 对称性分析结果
            thickness_result: 壁厚分析结果
            waviness_result: 波纹度分析结果
            resonance_result: 谐振参数分析结果
            
        Returns:
            QualityResult对象
        """
        self.logger.info("开始质量评价...")
        
        try:
            # 1. 计算各项指标得分
            individual_scores = {}
            
            if roughness_result is not None:
                individual_scores['roughness'] = self._score_roughness(roughness_result)
            
            if symmetry_result is not None:
                individual_scores['symmetry'] = self._score_symmetry(symmetry_result)
            
            if thickness_result is not None:
                individual_scores['thickness'] = self._score_thickness(thickness_result)
            
            if waviness_result is not None:
                individual_scores['waviness'] = self._score_waviness(waviness_result)
            
            if resonance_result is not None:
                individual_scores['resonance'] = self._score_resonance(resonance_result)
            
            # 2. 计算加权综合评分
            total_score = self._compute_total_score(individual_scores)
            
            # 3. 确定质量等级
            grade = self._determine_grade(total_score)
            
            # 4. 生成改进建议
            suggestions = self._generate_suggestions(
                individual_scores,
                roughness_result,
                symmetry_result,
                thickness_result
            )
            
            # 5. 创建结果
            result = QualityResult(
                total_score=total_score,
                grade=grade,
                individual_scores=individual_scores,
                improvement_suggestions=suggestions
            )
            
            self.log_result(result)
            return result
            
        except Exception as e:
            self.handle_error(e, "质量评价失败")
            raise
    
    def _score_roughness(self, result: RoughnessResult) -> float:
        """
        计算粗糙度得分
        
        Args:
            result: 粗糙度分析结果
            
        Returns:
            得分 (0-100)
        """
        ra = result.ra
        thresholds = self.thresholds['roughness']
        
        if ra <= thresholds['ra_excellent']:
            score = 100
        elif ra <= thresholds['ra_good']:
            # 线性插值
            score = 90 + 10 * (thresholds['ra_good'] - ra) / (thresholds['ra_good'] - thresholds['ra_excellent'])
        elif ra <= thresholds['ra_medium']:
            score = 75 + 15 * (thresholds['ra_medium'] - ra) / (thresholds['ra_medium'] - thresholds['ra_good'])
        else:
            # 低于中等
            score = max(0, 60 - 10 * (ra - thresholds['ra_medium']))
        
        return float(min(100, max(0, score)))
    
    def _score_symmetry(self, result: SymmetryResult) -> float:
        """
        计算对称性得分
        
        Args:
            result: 对称性分析结果
            
        Returns:
            得分 (0-100)
        """
        # 使用最小对称性误差
        min_error = min(result.symmetry_errors.values())
        thresholds = self.thresholds['symmetry']
        
        if min_error <= thresholds['error_excellent']:
            score = 100
        elif min_error <= thresholds['error_good']:
            score = 90 + 10 * (thresholds['error_good'] - min_error) / (thresholds['error_good'] - thresholds['error_excellent'])
        elif min_error <= thresholds['error_medium']:
            score = 75 + 15 * (thresholds['error_medium'] - min_error) / (thresholds['error_medium'] - thresholds['error_good'])
        else:
            score = max(0, 60 - 20 * (min_error - thresholds['error_medium']))
        
        return float(min(100, max(0, score)))
    
    def _score_thickness(self, result: ThicknessResult) -> float:
        """
        计算壁厚得分
        
        Args:
            result: 壁厚分析结果
            
        Returns:
            得分 (0-100)
        """
        uniformity = result.uniformity
        thresholds = self.thresholds['thickness']
        
        if uniformity <= thresholds['uniformity_excellent']:
            score = 100
        elif uniformity <= thresholds['uniformity_good']:
            score = 90 + 10 * (thresholds['uniformity_good'] - uniformity) / (thresholds['uniformity_good'] - thresholds['uniformity_excellent'])
        elif uniformity <= thresholds['uniformity_medium']:
            score = 75 + 15 * (thresholds['uniformity_medium'] - uniformity) / (thresholds['uniformity_medium'] - thresholds['uniformity_good'])
        else:
            score = max(0, 60 - 30 * (uniformity - thresholds['uniformity_medium']))
        
        return float(min(100, max(0, score)))
    
    def _score_waviness(self, result: WavinessResult) -> float:
        """
        计算波纹度得分
        
        Args:
            result: 波纹度分析结果
            
        Returns:
            得分 (0-100)
        """
        # 简化：使用波纹度幅值
        amplitude = result.waviness_amplitude
        
        # 假设阈值
        if amplitude <= 1.0:
            score = 100
        elif amplitude <= 2.0:
            score = 90 - 10 * (amplitude - 1.0)
        elif amplitude <= 5.0:
            score = 80 - 15 * (amplitude - 2.0)
        else:
            score = max(0, 35 - 5 * (amplitude - 5.0))
        
        return float(min(100, max(0, score)))
    
    def _score_resonance(self, result: ResonanceResult) -> float:
        """
        计算谐振参数得分
        
        Args:
            result: 谐振参数分析结果
            
        Returns:
            得分 (0-100)
        """
        # 使用质量分布均匀性
        uniformity = result.mass_uniformity
        
        # 直接映射到0-100
        score = uniformity * 100
        
        return float(score)
    
    def _compute_total_score(self, individual_scores: Dict[str, float]) -> float:
        """
        计算加权综合评分
        
        Args:
            individual_scores: 各项得分
            
        Returns:
            综合得分 (0-100)
        """
        # 归一化权重
        available_weights = {k: v for k, v in self.weights.items() if k in individual_scores}
        total_weight = sum(available_weights.values())
        
        if total_weight == 0:
            return 0
        
        # 计算加权平均
        total_score = 0
        for key, score in individual_scores.items():
            weight = available_weights.get(key, 0)
            total_score += weight * score
        
        total_score /= total_weight
        
        return float(total_score)
    
    def _determine_grade(self, total_score: float) -> str:
        """
        确定质量等级
        
        Args:
            total_score: 综合得分
            
        Returns:
            质量等级 (优、良、中、差)
        """
        if total_score >= self.grade_thresholds['excellent']:
            return "优"
        elif total_score >= self.grade_thresholds['good']:
            return "良"
        elif total_score >= self.grade_thresholds['medium']:
            return "中"
        else:
            return "差"
    
    def _generate_suggestions(self,
                             individual_scores: Dict[str, float],
                             roughness_result: Optional[RoughnessResult],
                             symmetry_result: Optional[SymmetryResult],
                             thickness_result: Optional[ThicknessResult]) -> List[str]:
        """
        生成改进建议
        
        Args:
            individual_scores: 各项得分
            roughness_result: 粗糙度结果
            symmetry_result: 对称性结果
            thickness_result: 壁厚结果
            
        Returns:
            改进建议列表
        """
        suggestions = []
        
        # 找出得分最低的指标
        if individual_scores:
            min_key = min(individual_scores, key=individual_scores.get)
            min_score = individual_scores[min_key]
            
            if min_score < 60:
                if min_key == 'roughness':
                    suggestions.append("表面粗糙度较差，建议优化加工工艺，降低表面粗糙度")
                    if roughness_result:
                        suggestions.append(f"当前Ra={roughness_result.ra:.3f}μm，目标Ra<0.8μm")
                
                elif min_key == 'symmetry':
                    suggestions.append("对称性误差较大，建议检查加工设备的对称性精度")
                    if symmetry_result:
                        max_order = max(symmetry_result.symmetry_errors, 
                                      key=symmetry_result.symmetry_errors.get)
                        suggestions.append(f"{max_order}阶对称性误差最大，需重点关注")
                
                elif min_key == 'thickness':
                    suggestions.append("壁厚均匀性较差，建议优化加工参数，提高壁厚一致性")
                    if thickness_result:
                        suggestions.append(f"当前不均匀度={thickness_result.uniformity:.3f}，目标<0.05")
                
                elif min_key == 'waviness':
                    suggestions.append("波纹度较大，建议检查刀具磨损和加工稳定性")
                
                elif min_key == 'resonance':
                    suggestions.append("质量分布均匀性较差，可能影响谐振性能")
        
        # 如果所有指标都很好
        if all(score >= 90 for score in individual_scores.values()):
            suggestions.append("加工质量优秀，各项指标均达标")
        
        return suggestions
