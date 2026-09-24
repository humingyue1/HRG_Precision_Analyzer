"""
齿状结构分析集成器
将齿状结构分析模块集成到v4.0 PrecisionAnalyzer系统
核心算法因项目保密暂不开放
"""
import numpy as np
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
import time

try:
    from .tooth_identifier import ToothIdentifier
    from .tooth_flatness_analyzer import ToothFlatnessAnalyzer
    from .geometry_calculator import GeometryCalculator
except ImportError:
    from tooth_identifier import ToothIdentifier
    from tooth_flatness_analyzer import ToothFlatnessAnalyzer
    from geometry_calculator import GeometryCalculator
