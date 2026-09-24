"""
HRG完整分析GUI v3.0
==================
改进:
1. 修复STL对比内存错误
2. 对比谐振陀螺的圆度/球度误差
3. 添加每步可视化(剖面图+3D图)
"""

import sys
import os

# 设置路径
script_dir = os.path.dirname(os.path.abspath(__file__))
package_dir = os.path.dirname(script_dir)
core_dir = os.path.join(package_dir, 'core')
v1_core_dir = os.path.join(package_dir, 'v1.0_Special_Analyzer', 'core')

# 添加所有需要的路径
paths_to_add = [
    script_dir,   # 添加script_dir以找到同目录下的模块
    package_dir,  # 添加package_dir以找到advanced_alignment.py
    core_dir,
    v1_core_dir
]

for path in paths_to_add:
    if path not in sys.path and os.path.exists(path):
        sys.path.insert(0, path)

import time
import json
import numpy as np
from datetime import datetime

# 检查PyQt5
try:
    from PyQt5.QtWidgets import *
    from PyQt5.QtCore import *
    from PyQt5.QtGui import *
except ImportError:
    print("请安装PyQt5: pip install PyQt5")
    sys.exit(1)

# 检查matplotlib
try:
    import matplotlib
    matplotlib.use('Qt5Agg')
    from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.figure import Figure
    import matplotlib.pyplot as plt
except ImportError:
    print("请安装matplotlib: pip install matplotlib")
    sys.exit(1)

# 导入核心模块
try:
    from complete_pipeline import PointCloudProcessor
    from hrg_special_analyzer import HRGSpecialAnalyzer
    from advanced_alignment import try_multiple_alignments
except ImportError as e:
    print(f"导入错误: {e}")
    sys.exit(1)


class VisualizationWidget(QWidget):
    """可视化窗口"""
    
    def __init__(self):
        super().__init__()
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # 创建matplotlib图形
        self.figure = Figure(figsize=(12, 8))
        self.canvas = FigureCanvas(self.figure)
        layout.addWidget(self.canvas)
        
    def plot_point_cloud(self, points, title="点云"):
        """绘制点云(剖面图+3D图)"""
        self.figure.clear()
        
        if len(points) == 0:
            return
            
        # 2x2布局
        ax1 = self.figure.add_subplot(221)
        ax1.scatter(points[:,0], points[:,1], s=0.1, alpha=0.5)
        ax1.set_xlabel('X (mm)')
        ax1.set_ylabel('Y (mm)')
        ax1.set_title(f'{title} - XY剖面(俯视)')
        ax1.grid(True, alpha=0.3)
        ax1.set_aspect('equal')
        
        ax2 = self.figure.add_subplot(222)
        ax2.scatter(points[:,0], points[:,2], s=0.1, alpha=0.5)
        ax2.set_xlabel('X (mm)')
        ax2.set_ylabel('Z (mm)')
        ax2.set_title(f'{title} - XZ剖面(侧视)')
        ax2.grid(True, alpha=0.3)
        
        ax3 = self.figure.add_subplot(223)
        ax3.scatter(points[:,1], points[:,2], s=0.1, alpha=0.5)
        ax3.set_xlabel('Y (mm)')
        ax3.set_ylabel('Z (mm)')
        ax3.set_title(f'{title} - YZ剖面(正视)')
        ax3.grid(True, alpha=0.3)
        
        ax4 = self.figure.add_subplot(224, projection='3d')
        if len(points) > 10000:
            idx = np.random.choice(len(points), 10000, replace=False)
            points_sample = points[idx]
        else:
            points_sample = points
        ax4.scatter(points_sample[:,0], points_sample[:,1], points_sample[:,2], s=0.5, alpha=0.5)
        ax4.set_xlabel('X (mm)')
        ax4.set_ylabel('Y (mm)')
        ax4.set_zlabel('Z (mm)')
        ax4.set_title(f'{title} - 3D视图')
        
        self.figure.tight_layout()
        self.canvas.draw()
        
    def plot_comparison(self, points1, points2, title1="ASC", title2="STL"):
        """绘制两个点云的对比可视化"""
        self.figure.clear()
        
        if len(points1) == 0 or len(points2) == 0:
            return
            
        # 降采样
        if len(points1) > 10000:
            idx1 = np.random.choice(len(points1), 10000, replace=False)
            points1_sample = points1[idx1]
        else:
            points1_sample = points1
            
        if len(points2) > 10000:
            idx2 = np.random.choice(len(points2), 10000, replace=False)
            points2_sample = points2[idx2]
        else:
            points2_sample = points2
        
        # XY剖面对比
        ax1 = self.figure.add_subplot(221)
        ax1.scatter(points1_sample[:,0], points1_sample[:,1], s=0.5, alpha=0.5, c='blue', label=title1)
        ax1.scatter(points2_sample[:,0], points2_sample[:,1], s=0.5, alpha=0.5, c='red', label=title2)
        ax1.set_xlabel('X (mm)')
        ax1.set_ylabel('Y (mm)')
        ax1.set_title(f'{title1} vs {title2} - XY剖面(俯视)')
        ax1.grid(True, alpha=0.3)
        ax1.legend()
        ax1.set_aspect('equal')
        
        # XZ剖面对比
        ax2 = self.figure.add_subplot(222)
        ax2.scatter(points1_sample[:,0], points1_sample[:,2], s=0.5, alpha=0.5, c='blue', label=title1)
        ax2.scatter(points2_sample[:,0], points2_sample[:,2], s=0.5, alpha=0.5, c='red', label=title2)
        ax2.set_xlabel('X (mm)')
        ax2.set_ylabel('Z (mm)')
        ax2.set_title(f'{title1} vs {title2} - XZ剖面(侧视)')
        ax2.grid(True, alpha=0.3)
        ax2.legend()
        
        # YZ剖面对比
        ax3 = self.figure.add_subplot(223)
        ax3.scatter(points1_sample[:,1], points1_sample[:,2], s=0.5, alpha=0.5, c='blue', label=title1)
        ax3.scatter(points2_sample[:,1], points2_sample[:,2], s=0.5, alpha=0.5, c='red', label=title2)
        ax3.set_xlabel('Y (mm)')
        ax3.set_ylabel('Z (mm)')
        ax3.set_title(f'{title1} vs {title2} - YZ剖面(正视)')
        ax3.grid(True, alpha=0.3)
        ax3.legend()
        
        # 3D对比
        ax4 = self.figure.add_subplot(224, projection='3d')
        ax4.scatter(points1_sample[:,0], points1_sample[:,1], points1_sample[:,2], s=0.5, alpha=0.5, c='blue', label=title1)
        ax4.scatter(points2_sample[:,0], points2_sample[:,1], points2_sample[:,2], s=0.5, alpha=0.5, c='red', label=title2)
        ax4.set_xlabel('X (mm)')
        ax4.set_ylabel('Y (mm)')
        ax4.set_zlabel('Z (mm)')
        ax4.set_title(f'{title1} vs {title2} - 3D对比')
        ax4.legend()
        
        self.figure.tight_layout()
        self.canvas.draw()


class CompleteAnalysisWorkerV3(QThread):
    """完整分析工作线程 v3"""
    
    progress_updated = pyqtSignal(int, str)
    log_message = pyqtSignal(str)
    visualization_ready = pyqtSignal(np.ndarray, str)
    comparison_ready = pyqtSignal(np.ndarray, np.ndarray, str, str)  # 新增: 对比可视化
    analysis_finished = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, asc_path, stl_path=None, sample_rate=100):
        super().__init__()
        self.asc_path = asc_path
        self.stl_path = stl_path
        self.sample_rate = sample_rate
        self.results = {}  # 保存分析结果
        
    def run(self):
        try:
            results = {}
            
            # 步骤1: 加载ASC文件
            self.progress_updated.emit(5, "加载ASC文件...")
            self.log_message.emit(f"[1/7] 加载ASC文件: {os.path.basename(self.asc_path)}")
            
            processor = PointCloudProcessor(num_processes=4)
            points = processor.load_asc_file(self.asc_path, sample_rate=self.sample_rate)
            
            self.log_message.emit(f"  点数: {len(points):,}")
            results['total_points'] = len(points)
            
            # 可视化原始点云
            self.visualization_ready.emit(points, "原始点云")
            
            # 步骤2: 分割点云
            self.progress_updated.emit(15, "分割点云...")
            self.log_message.emit("[2/7] 分割点云...")
            
            analyzer = HRGSpecialAnalyzer()
            hrg_points, assembly_points, bottom_plane = analyzer.segment_hrg_and_assembly(points)
            
            self.log_message.emit(f"  谐振陀螺: {len(hrg_points):,} 点")
            self.log_message.emit(f"  装配结构: {len(assembly_points):,} 点")
            self.log_message.emit(f"  底部平面: {len(bottom_plane):,} 点")
            
            results['segmentation'] = {
                'hrg_points': len(hrg_points),
                'assembly_points': len(assembly_points),
                'bottom_plane_points': len(bottom_plane)
            }
            
            # 可视化分割结果
            self.visualization_ready.emit(hrg_points, "谐振陀螺(分割后)")
            
            # 步骤3: 分析装配误差
            self.progress_updated.emit(25, "分析装配误差...")
            self.log_message.emit("[3/7] 分析装配误差...")
            
            assembly_error = analyzer.analyze_assembly_error(hrg_points, bottom_plane)
            
            self.log_message.emit(f"  平均距离: {assembly_error['mean_distance']*1000:.2f} μm")
            self.log_message.emit(f"  标准差: {assembly_error['std_distance']*1000:.2f} μm")
            
            results['assembly_error'] = assembly_error
            
            # 步骤4: 清理谐振陀螺
            self.progress_updated.emit(35, "清理谐振陀螺点云...")
            self.log_message.emit("[4/7] 清理谐振陀螺点云(去除虚影)...")
            
            z = hrg_points[:,2]
            z_threshold = -0.1
            clean_mask = z <= z_threshold
            hrg_clean = hrg_points[clean_mask]
            
            self.log_message.emit(f"  清理后: {len(hrg_clean):,} 点")
            
            results['hrg_cleaned_points'] = len(hrg_clean)
            
            # 可视化清理后的谐振陀螺
            self.visualization_ready.emit(hrg_clean, "谐振陀螺(清理后)")
            
            # 步骤5: 分析几何误差
            self.progress_updated.emit(50, "分析几何误差...")
            self.log_message.emit("[5/7] 分析谐振陀螺几何误差...")
            
            # 圆度误差
            self.log_message.emit("  分析圆度误差...")
            roundness_result = analyzer.analyze_roundness(hrg_clean)
            roundness = {
                'max_error': roundness_result.get('max_roundness_error', roundness_result.get('max_error', 0)),
                'mean_error': roundness_result.get('mean_roundness_error', roundness_result.get('mean_error', 0))
            }
            
            self.log_message.emit(f"    最大: {roundness['max_error']:.2f} μm")
            self.log_message.emit(f"    平均: {roundness['mean_error']:.2f} μm")
            
            # 球度误差
            self.log_message.emit("  分析球度误差...")
            sphericity_result = analyzer.analyze_sphericity_hrg_only(hrg_clean)
            sphericity = {
                'center': sphericity_result.get('center', [0,0,0]),
                'radius': sphericity_result.get('radius', 0),
                'error': sphericity_result.get('sphericity_error', sphericity_result.get('error', 0))
            }
            
            self.log_message.emit(f"    半径: {sphericity['radius']:.3f} mm")
            self.log_message.emit(f"    误差: {sphericity['error']:.2f} μm")
            
            results['roundness'] = roundness
            results['sphericity'] = sphericity
            
            # 步骤6: STL对比(对比几何误差,不是距离)
            if self.stl_path and os.path.exists(self.stl_path):
                self.progress_updated.emit(70, "与STL对比...")
                self.log_message.emit("[6/7] 与STL模型对比几何误差...")
                
                try:
                    import trimesh
                    
                    self.log_message.emit(f"  加载STL: {os.path.basename(self.stl_path)}")
                    mesh = trimesh.load(self.stl_path)
                    
                    # 从STL提取点云(采样)
                    self.log_message.emit("  从STL提取点云...")
                    stl_points = mesh.sample(10000)  # 采样10000个点
                    
                    self.log_message.emit(f"    STL点数: {len(stl_points):,}")
                    
                    # 点云对齐 - 关键修复！
                    self.log_message.emit("  对齐点云(ICP配准)...")
                    stl_aligned, align_error, strategy = try_multiple_alignments(hrg_clean, stl_points)
                    
                    self.log_message.emit(f"    使用策略: {strategy}")
                    self.log_message.emit(f"    对齐误差: {align_error:.6f} mm ({align_error*1000:.2f} μm)")
                    
                    # 可视化对齐后的STL点云
                    self.visualization_ready.emit(stl_aligned, "STL模型点云(对齐后)")
                    
                    # 可视化ASC与STL对比
                    self.comparison_ready.emit(hrg_clean, stl_aligned, "ASC谐振陀螺", "STL模型(对齐后)")
                    
                    # 分析STL的几何误差
                    self.log_message.emit("  分析STL模型的几何误差...")
                    
                    # STL的圆度误差（使用对齐后的点云）
                    stl_roundness_result = analyzer.analyze_roundness(stl_aligned)
                    stl_roundness = {
                        'max_error': stl_roundness_result.get('max_roundness_error', stl_roundness_result.get('max_error', 0)),
                        'mean_error': stl_roundness_result.get('mean_roundness_error', stl_roundness_result.get('mean_error', 0))
                    }
                    
                    # STL的球度误差（使用对齐后的点云）
                    stl_sphericity_result = analyzer.analyze_sphericity_hrg_only(stl_aligned)
                    stl_sphericity = {
                        'center': stl_sphericity_result.get('center', [0,0,0]),
                        'radius': stl_sphericity_result.get('radius', 0),
                        'error': stl_sphericity_result.get('sphericity_error', stl_sphericity_result.get('error', 0))
                    }
                    
                    # 对比误差
                    self.log_message.emit("  对比结果:")
                    self.log_message.emit(f"    圆度误差差异: {abs(roundness['mean_error'] - stl_roundness['mean_error']):.2f} μm")
                    self.log_message.emit(f"    球度误差差异: {abs(sphericity['error'] - stl_sphericity['error']):.2f} μm")
                    self.log_message.emit(f"    半径差异: {abs(sphericity['radius'] - stl_sphericity['radius']):.3f} mm")
                    
                    results['stl_comparison'] = {
                        'stl_roundness': stl_roundness,
                        'stl_sphericity': stl_sphericity,
                        'roundness_diff': abs(roundness['mean_error'] - stl_roundness['mean_error']),
                        'sphericity_diff': abs(sphericity['error'] - stl_sphericity['error']),
                        'radius_diff': abs(sphericity['radius'] - stl_sphericity['radius']),
                        'alignment_error': align_error,
                        'alignment_strategy': strategy
                    }
                    
                except Exception as e:
                    self.log_message.emit(f"  STL对比失败: {e}")
                    import traceback
                    self.log_message.emit(traceback.format_exc())
            
            # 步骤7: 生成报告
            self.progress_updated.emit(95, "生成报告...")
            self.log_message.emit("[7/7] 生成报告...")
            
            self.progress_updated.emit(100, "完成!")
            self.log_message.emit("\n分析完成!")
            
            results['timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            self.results = results  # 保存结果
            self.analysis_finished.emit(results)
            
        except Exception as e:
            import traceback
            self.error_occurred.emit(f"{str(e)}\n\n{traceback.format_exc()}")


class HRGCompleteAnalyzerGUIV3(QMainWindow):
    """HRG完整分析GUI v3"""
    
    def __init__(self):
        super().__init__()
        self.worker = None
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("HRG完整分析器 v3.0 - 装配误差 + 几何误差 + STL对比 + 可视化")
        self.setGeometry(100, 100, 1400, 900)
        
        # 主窗口
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        
        # 文件选择区域
        file_group = QGroupBox("文件选择")
        file_layout = QGridLayout()
        
        # ASC文件
        file_layout.addWidget(QLabel("ASC文件:"), 0, 0)
        self.asc_edit = QLineEdit()
        self.asc_edit.setPlaceholderText("选择ASC点云文件")
        file_layout.addWidget(self.asc_edit, 0, 1)
        asc_btn = QPushButton("浏览")
        asc_btn.clicked.connect(self.select_asc)
        file_layout.addWidget(asc_btn, 0, 2)
        
        # STL文件
        file_layout.addWidget(QLabel("STL文件:"), 1, 0)
        self.stl_edit = QLineEdit()
        self.stl_edit.setPlaceholderText("选择STL模型文件(可选)")
        file_layout.addWidget(self.stl_edit, 1, 1)
        stl_btn = QPushButton("浏览")
        stl_btn.clicked.connect(self.select_stl)
        file_layout.addWidget(stl_btn, 1, 2)
        
        # 采样率
        file_layout.addWidget(QLabel("采样率:"), 2, 0)
        self.sample_spin = QSpinBox()
        self.sample_spin.setRange(1, 1000)
        self.sample_spin.setValue(100)
        file_layout.addWidget(self.sample_spin, 2, 1)
        file_layout.addWidget(QLabel("(1/N采样,100表示1/100)"), 2, 2)
        
        file_group.setLayout(file_layout)
        layout.addWidget(file_group)
        
        # 控制按钮
        btn_layout = QHBoxLayout()
        
        self.start_btn = QPushButton("开始分析")
        self.start_btn.clicked.connect(self.start_analysis)
        self.start_btn.setStyleSheet("background-color: #4CAF50; color: white; font-size: 14px; padding: 10px;")
        btn_layout.addWidget(self.start_btn)
        
        self.stop_btn = QPushButton("停止")
        self.stop_btn.clicked.connect(self.stop_analysis)
        self.stop_btn.setEnabled(False)
        btn_layout.addWidget(self.stop_btn)
        
        layout.addLayout(btn_layout)
        
        # 进度条
        progress_group = QGroupBox("进度")
        progress_layout = QVBoxLayout()
        
        self.progress_bar = QProgressBar()
        progress_layout.addWidget(self.progress_bar)
        
        self.status_label = QLabel("就绪")
        progress_layout.addWidget(self.status_label)
        
        progress_group.setLayout(progress_layout)
        layout.addWidget(progress_group)
        
        # 主分割器
        splitter = QSplitter(Qt.Horizontal)
        
        # 左侧: 日志和结果
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        result_tabs = QTabWidget()
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 9))
        result_tabs.addTab(self.log_text, "运行日志")
        
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setFont(QFont("Consolas", 9))
        result_tabs.addTab(self.result_text, "分析结果")
        
        left_layout.addWidget(result_tabs)
        
        # 右侧: 可视化
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        vis_group = QGroupBox("点云可视化")
        vis_layout = QVBoxLayout()
        
        self.vis_widget = VisualizationWidget()
        vis_layout.addWidget(self.vis_widget)
        
        vis_group.setLayout(vis_layout)
        right_layout.addWidget(vis_group)
        
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setSizes([600, 800])
        
        layout.addWidget(splitter)
        
        # 状态栏
        self.statusBar().showMessage("就绪")
        
    def select_asc(self):
        file, _ = QFileDialog.getOpenFileName(self, "选择ASC文件", "", "ASC Files (*.ASC *.asc)")
        if file:
            self.asc_edit.setText(file)
            
    def select_stl(self):
        file, _ = QFileDialog.getOpenFileName(self, "选择STL文件", "", "STL Files (*.stl *.STL)")
        if file:
            self.stl_edit.setText(file)
            
    def start_analysis(self):
        asc_path = self.asc_edit.text()
        if not asc_path or not os.path.exists(asc_path):
            QMessageBox.warning(self, "警告", "请选择有效的ASC文件")
            return
            
        stl_path = self.stl_edit.text() if self.stl_edit.text() else None
        sample_rate = self.sample_spin.value()
        
        # 清空
        self.log_text.clear()
        self.result_text.clear()
        
        # 创建工作线程
        self.worker = CompleteAnalysisWorkerV3(asc_path, stl_path, sample_rate)
        self.worker.progress_updated.connect(self.update_progress)
        self.worker.log_message.connect(self.add_log)
        self.worker.visualization_ready.connect(self.update_visualization)
        self.worker.comparison_ready.connect(self.update_comparison)  # 新增
        self.worker.analysis_finished.connect(self.analysis_complete)
        self.worker.error_occurred.connect(self.show_error)
        
        # 启动
        self.worker.start()
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.statusBar().showMessage("分析中...")
        
    def stop_analysis(self):
        if self.worker:
            self.worker.terminate()
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.statusBar().showMessage("已停止")
        
    def update_progress(self, value, text):
        self.progress_bar.setValue(value)
        self.status_label.setText(text)
        
    def add_log(self, message):
        self.log_text.append(message)
        cursor = self.log_text.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.log_text.setTextCursor(cursor)
        
    def update_visualization(self, points, title):
        """更新可视化"""
        self.vis_widget.plot_point_cloud(points, title)
        
    def update_comparison(self, points1, points2, title1, title2):
        """更新对比可视化"""
        self.vis_widget.plot_comparison(points1, points2, title1, title2)
        
    def analysis_complete(self, results):
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.statusBar().showMessage("分析完成")
        
        # 显示结果
        result_text = "=" * 70 + "\n"
        result_text += "HRG完整分析结果\n"
        result_text += "=" * 70 + "\n\n"
        
        result_text += f"分析时间: {results.get('timestamp', 'N/A')}\n"
        result_text += f"总点数: {results.get('total_points', 0):,}\n\n"
        
        # 分割结果
        seg = results.get('segmentation', {})
        result_text += "-" * 70 + "\n"
        result_text += "1. 点云分割\n"
        result_text += "-" * 70 + "\n"
        result_text += f"  谐振陀螺: {seg.get('hrg_points', 0):,} 点\n"
        result_text += f"  装配结构: {seg.get('assembly_points', 0):,} 点\n"
        result_text += f"  底部平面: {seg.get('bottom_plane_points', 0):,} 点\n"
        result_text += f"  清理后谐振陀螺: {results.get('hrg_cleaned_points', 0):,} 点\n\n"
        
        # 装配误差
        asm = results.get('assembly_error', {})
        result_text += "-" * 70 + "\n"
        result_text += "2. 装配误差\n"
        result_text += "-" * 70 + "\n"
        result_text += f"  平均距离: {asm.get('mean_distance', 0)*1000:.2f} μm\n"
        result_text += f"  标准差: {asm.get('std_distance', 0)*1000:.2f} μm\n"
        result_text += f"  范围: [{asm.get('min_distance', 0)*1000:.2f}, {asm.get('max_distance', 0)*1000:.2f}] μm\n\n"
        
        # 圆度误差
        rnd = results.get('roundness', {})
        result_text += "-" * 70 + "\n"
        result_text += "3. 圆度误差(谐振陀螺)\n"
        result_text += "-" * 70 + "\n"
        result_text += f"  最大误差: {rnd.get('max_error', 0):.2f} μm\n"
        result_text += f"  平均误差: {rnd.get('mean_error', 0):.2f} μm\n\n"
        
        # 球度误差
        sph = results.get('sphericity', {})
        result_text += "-" * 70 + "\n"
        result_text += "4. 球度误差(谐振陀螺)\n"
        result_text += "-" * 70 + "\n"
        result_text += f"  拟合球心: {sph.get('center', [0,0,0])}\n"
        result_text += f"  拟合半径: {sph.get('radius', 0):.3f} mm\n"
        result_text += f"  球度误差: {sph.get('error', 0):.2f} μm\n\n"
        
        # STL对比
        if 'stl_comparison' in results:
            stl = results['stl_comparison']
            result_text += "-" * 70 + "\n"
            result_text += "5. STL模型对比\n"
            result_text += "-" * 70 + "\n"
            
            # 显示对齐信息
            result_text += f"  对齐策略: {stl.get('alignment_strategy', 'N/A')}\n"
            result_text += f"  对齐误差: {stl.get('alignment_error', 0)*1000:.2f} μm\n\n"
            
            stl_rnd = stl.get('stl_roundness', {})
            stl_sph = stl.get('stl_sphericity', {})
            
            result_text += f"  STL圆度误差: {stl_rnd.get('mean_error', 0):.2f} μm\n"
            result_text += f"  STL球度误差: {stl_sph.get('error', 0):.2f} μm\n"
            result_text += f"  STL半径: {stl_sph.get('radius', 0):.3f} mm\n\n"
            
            result_text += f"  【对比结果】\n"
            result_text += f"  圆度误差差异: {stl.get('roundness_diff', 0):.2f} μm\n"
            result_text += f"  球度误差差异: {stl.get('sphericity_diff', 0):.2f} μm\n"
            result_text += f"  半径差异: {stl.get('radius_diff', 0):.3f} mm\n\n"
        
        result_text += "=" * 70 + "\n"
        
        self.result_text.setText(result_text)
        
        # 保存
        output_dir = os.path.join(os.path.dirname(self.asc_edit.text()), 'output')
        os.makedirs(output_dir, exist_ok=True)
        
        report_file = os.path.join(output_dir, 'gui_analysis_report_v3.txt')
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(result_text)
            
        self.add_log(f"\n报告已保存: {report_file}")
        
    def show_error(self, error):
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.statusBar().showMessage("错误")
        
        QMessageBox.critical(self, "错误", error)
        self.add_log(f"\n错误:\n{error}")


if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    window = HRGCompleteAnalyzerGUIV3()
    window.show()
    
    sys.exit(app.exec_())
