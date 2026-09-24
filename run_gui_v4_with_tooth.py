"""
启动HRG Precision Analyzer v4.0 GUI
支持齿状结构分析功能
"""
import sys
import os

script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

from PyQt5.QtWidgets import QApplication
from gui.hrg_precision_analyzer_gui_v4 import HRGPrecisionAnalyzerGUIV4

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    window = HRGPrecisionAnalyzerGUIV4()
    window.show()
    
    sys.exit(app.exec_())
