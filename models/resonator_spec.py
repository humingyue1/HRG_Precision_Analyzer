"""
振子规格定义与管理
支持48齿、32齿、16齿三种振子规格
"""
from enum import Enum
from dataclasses import dataclass
from typing import Dict, Any


class ResonatorSpec(Enum):
    """振子规格枚举"""
    SPEC_48_TOOTH = 48
    SPEC_32_TOOTH = 32
    SPEC_16_TOOTH = 16
    
    @classmethod
    def from_tooth_count(cls, count: int) -> 'ResonatorSpec':
        """根据齿数获取规格"""
        for spec in cls:
            if spec.value == count:
                return spec
        raise ValueError(f"不支持的齿数：{count}，仅支持48、32、16齿")


@dataclass
class ResonatorSpecConfig:
    """振子规格配置"""
    spec: ResonatorSpec
    tooth_count: int
    tooth_angle: float
    benchmark_time: float
    min_points_per_tooth: int
    
    def __post_init__(self):
        """初始化后验证"""
        if self.spec.value != self.tooth_count:
            raise ValueError(f"规格{self.spec.name}与齿数{self.tooth_count}不匹配")
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'spec': self.spec.name,
            'tooth_count': self.tooth_count,
            'tooth_angle': self.tooth_angle,
            'benchmark_time': self.benchmark_time,
            'min_points_per_tooth': self.min_points_per_tooth
        }


class SpecManager:
    """规格管理器"""
    
    _configs: Dict[ResonatorSpec, ResonatorSpecConfig] = {}
    
    @classmethod
    def initialize(cls):
        """初始化所有规格配置"""
        cls._configs = {
            ResonatorSpec.SPEC_48_TOOTH: ResonatorSpecConfig(
                spec=ResonatorSpec.SPEC_48_TOOTH,
                tooth_count=48,
                tooth_angle=360.0 / 48,
                benchmark_time=120.0,
                min_points_per_tooth=10000
            ),
            ResonatorSpec.SPEC_32_TOOTH: ResonatorSpecConfig(
                spec=ResonatorSpec.SPEC_32_TOOTH,
                tooth_count=32,
                tooth_angle=360.0 / 32,
                benchmark_time=90.0,
                min_points_per_tooth=8000
            ),
            ResonatorSpec.SPEC_16_TOOTH: ResonatorSpecConfig(
                spec=ResonatorSpec.SPEC_16_TOOTH,
                tooth_count=16,
                tooth_angle=360.0 / 16,
                benchmark_time=60.0,
                min_points_per_tooth=6000
            )
        }
    
    @classmethod
    def get_spec_config(cls, spec: ResonatorSpec) -> ResonatorSpecConfig:
        """获取规格配置"""
        if not cls._configs:
            cls.initialize()
        
        if spec not in cls._configs:
            raise ValueError(f"未知规格：{spec}")
        
        return cls._configs[spec]
    
    @classmethod
    def get_config_by_tooth_count(cls, tooth_count: int) -> ResonatorSpecConfig:
        """根据齿数获取配置"""
        spec = ResonatorSpec.from_tooth_count(tooth_count)
        return cls.get_spec_config(spec)
    
    @classmethod
    def get_all_specs(cls) -> Dict[ResonatorSpec, ResonatorSpecConfig]:
        """获取所有规格配置"""
        if not cls._configs:
            cls.initialize()
        
        return cls._configs


SpecManager.initialize()
