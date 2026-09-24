"""测试v4.0模块导入"""
import sys, os

v4_dir = os.path.dirname(os.path.abspath(__file__))
gui_dir = os.path.join(v4_dir, 'gui')
core_dir = os.path.join(v4_dir, 'core')

for p in [gui_dir, core_dir, v4_dir]:
    if p not in sys.path:
        sys.path.insert(0, p)

print("1. Testing core modules...")

try:
    from precision_analyzer import PrecisionAnalyzer
    print("   [OK] PrecisionAnalyzer")
except Exception as e:
    print(f"   [FAIL] PrecisionAnalyzer: {e}")

try:
    from roughness_analyzer import RoughnessAnalyzer
    print("   [OK] RoughnessAnalyzer")
except Exception as e:
    print(f"   [FAIL] RoughnessAnalyzer: {e}")

try:
    from symmetry_analyzer import SymmetryAnalyzer
    print("   [OK] SymmetryAnalyzer")
except Exception as e:
    print(f"   [FAIL] SymmetryAnalyzer: {e}")

try:
    from thickness_analyzer import ThicknessAnalyzer
    print("   [OK] ThicknessAnalyzer")
except Exception as e:
    print(f"   [FAIL] ThicknessAnalyzer: {e}")

print("\n2. Testing v3.0 GUI import...")

try:
    from hrg_complete_analyzer_gui_v3 import HRGCompleteAnalyzerGUIV3
    print("   [OK] v3.0 GUI")
except Exception as e:
    print(f"   [FAIL] v3.0 GUI: {e}")

try:
    from hrg_complete_analyzer_gui_v3_with_export import HRGCompleteAnalyzerGUIV3WithExport
    print("   [OK] v3.0 GUI with export")
except Exception as e:
    print(f"   [FAIL] v3.0 GUI with export: {e}")

print("\nAll core imports done!")
