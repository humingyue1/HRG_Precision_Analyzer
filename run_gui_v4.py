"""启动HRG谐振陀螺分析系统 v4.0 GUI"""
import sys
import os

v4_dir = os.path.dirname(os.path.abspath(__file__))
gui_dir = os.path.join(v4_dir, 'gui')
core_dir = os.path.join(v4_dir, 'core')
report_export_dir = os.path.join(v4_dir, 'report_export')

for p in [gui_dir, core_dir, report_export_dir, v4_dir]:
    if p not in sys.path:
        sys.path.insert(0, p)

from hrg_precision_analyzer_gui_v4 import HRGPrecisionAnalyzerGUIV4

if __name__ == '__main__':
    from PyQt5.QtWidgets import QApplication
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    window = HRGPrecisionAnalyzerGUIV4()
    window.show()
    sys.exit(app.exec_())
