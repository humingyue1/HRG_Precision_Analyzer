"""
HRG完整分析GUI v4.0 - 统一分析流程
统一步骤编号体系，消除碎片化输出，质量评价置末
"""

import sys
import os

script_dir = os.path.dirname(os.path.abspath(__file__))
package_dir = os.path.dirname(script_dir)
core_dir = os.path.join(package_dir, 'core')
report_export_dir = os.path.join(package_dir, 'report_export')

for p in [script_dir, package_dir, core_dir, report_export_dir]:
    if p not in sys.path:
        sys.path.insert(0, p)

import time
import json
import numpy as np
from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional, List, Dict

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

from hrg_complete_analyzer_gui_v3_with_export import HRGCompleteAnalyzerGUIV3WithExport

try:
    from precision_analyzer import PrecisionAnalyzer, PrecisionAnalysisResult
    PRECISION_ANALYZER_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Precision analyzer not available: {e}")
    PRECISION_ANALYZER_AVAILABLE = False

try:
    import vtk
    from vtk.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
    VTK_AVAILABLE = True
except ImportError:
    VTK_AVAILABLE = False

import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure


class LayoutMode:
    """布局模式枚举"""
    SINGLE = 'single'          # 单点云：纯 matplotlib 2×2
    COMPARISON = 'comparison'   # 对比：左 matplotlib (XY上+XZ/YZ下) + 右 VTK 3D


class VTKVisualizationWidget(QWidget):
    # 布局比例常量
    COMPARISON_SPLITTER_SIZES = [3, 2]  # 左 matplotlib:右 VTK = 3:2
    TIGHT_LAYOUT_PAD = 1.08
    VTK_RENDER_DELAY_MS = 50
    VTK_RENDER_RETRY_MS = 100

    def __init__(self, parent=None):
        super().__init__(parent)

        # 根布局（QVBoxLayout，仅包含 QSplitter）
        self._main_layout = QVBoxLayout(self)
        self._main_layout.setContentsMargins(0, 0, 0, 0)

        # QSplitter 管理 Canvas 和 VTK 容器的布局
        # 单点云模式：Vertical（canvas独占全高），对比模式：Horizontal（左matplotlib右VTK）
        self._splitter = QSplitter(Qt.Vertical)
        self._main_layout.addWidget(self._splitter)

        # matplotlib Canvas（Splitter 上方）
        self.figure = Figure(figsize=(12, 4))
        self.canvas = FigureCanvas(self.figure)
        self._splitter.addWidget(self.canvas)

        # VTK 容器（Splitter 下方）
        self._vtk_container = QWidget()
        vtk_layout = QHBoxLayout(self._vtk_container)
        vtk_layout.setContentsMargins(0, 0, 0, 0)
        self.vtk_widget = QVTKRenderWindowInteractor(self._vtk_container)
        vtk_layout.addWidget(self.vtk_widget)
        self.vtk_renderer = vtk.vtkRenderer()
        self.vtk_renderer.SetBackground(1.0, 1.0, 1.0)
        self.vtk_widget.GetRenderWindow().AddRenderer(self.vtk_renderer)
        self.vtk_widget.Initialize()
        style = vtk.vtkInteractorStyleTrackballCamera()
        self.vtk_widget.SetInteractorStyle(style)

        self._splitter.addWidget(self._vtk_container)

        # 初始状态：单点云模式，VTK 隐藏，Canvas 独占
        self._vtk_container.setVisible(False)
        self._splitter.setSizes([1, 0])

        self._vtk_actors = []
        self._vtk_marker = None
        self._layout_mode = LayoutMode.SINGLE

    def _switch_to_single_mode(self):
        """切换到单点云布局模式：隐藏 VTK，Canvas 独占，Splitter 纵向"""
        if self._layout_mode == LayoutMode.SINGLE:
            return
        self._clear_vtk()
        self._vtk_container.setVisible(False)
        self.canvas.setVisible(True)
        self._splitter.setOrientation(Qt.Vertical)
        self._splitter.setSizes([1, 0])
        self.figure.set_size_inches(12, 8)
        self._layout_mode = LayoutMode.SINGLE

    def _switch_to_comparison_mode(self):
        """切换到对比布局模式：左 matplotlib + 右 VTK，比例 3:2"""
        if self._layout_mode == LayoutMode.COMPARISON:
            return
        self._vtk_container.setVisible(True)
        self.canvas.setVisible(True)
        self._splitter.setOrientation(Qt.Horizontal)
        self.figure.set_size_inches(10, 8)
        self._splitter.setSizes(self.COMPARISON_SPLITTER_SIZES)
        self._layout_mode = LayoutMode.COMPARISON

    def _deferred_vtk_render(self):
        """延迟 VTK 渲染，确保容器已获得有效尺寸"""
        w = self._vtk_container.width()
        h = self._vtk_container.height()
        if w > 10 and h > 10:
            self.vtk_widget.GetRenderWindow().Render()
            self.vtk_widget._Iren.ProcessEvents()
        else:
            QTimer.singleShot(self.VTK_RENDER_RETRY_MS, self._deferred_vtk_render)

    def _clear_vtk(self):
        for actor in self._vtk_actors:
            self.vtk_renderer.RemoveActor(actor)
        self._vtk_actors.clear()
        if self._vtk_marker:
            self._vtk_marker.SetEnabled(0)
            self._vtk_marker = None

    @staticmethod
    def _filter_valid_points(points):
        if len(points) == 0:
            return points
        mask = np.isfinite(points).all(axis=1)
        return points[mask]

    def _add_point_cloud_vtk(self, points, color=(0.3, 0.6, 1.0), point_size=3.0):
        vtk_points = vtk.vtkPoints()
        vertices = vtk.vtkCellArray()
        for i in range(len(points)):
            vtk_points.InsertNextPoint(points[i, 0], points[i, 1], points[i, 2])
            vertices.InsertNextCell(1)
            vertices.InsertCellPoint(i)
        polydata = vtk.vtkPolyData()
        polydata.SetPoints(vtk_points)
        polydata.SetVerts(vertices)

        glyph_filter = vtk.vtkVertexGlyphFilter()
        glyph_filter.SetInputData(polydata)
        glyph_filter.Update()

        mapper = vtk.vtkPolyDataMapper()
        mapper.SetInputConnection(glyph_filter.GetOutputPort())

        actor = vtk.vtkActor()
        actor.SetMapper(mapper)
        actor.GetProperty().SetColor(*color)
        actor.GetProperty().SetOpacity(0.8)
        actor.GetProperty().SetPointSize(point_size)
        self.vtk_renderer.AddActor(actor)
        self._vtk_actors.append(actor)

    def _setup_vtk_camera(self):
        self.vtk_renderer.ResetCamera()

        axes = vtk.vtkAxesActor()
        axes.SetTotalLength(0.5, 0.5, 0.5)
        marker = vtk.vtkOrientationMarkerWidget()
        marker.SetOrientationMarker(axes)
        marker.SetInteractor(self.vtk_widget._Iren)
        marker.SetEnabled(1)
        marker.InteractiveOff()
        self._vtk_marker = marker

    def plot_point_cloud(self, points, title="点云"):
        self._switch_to_single_mode()
        self.figure.clear()

        if len(points) == 0:
            self.canvas.draw()
            return

        self.figure.subplots_adjust(hspace=0.45, wspace=0.35, left=0.08, right=0.96, top=0.93, bottom=0.12)

        ax1 = self.figure.add_subplot(221)
        ax1.scatter(points[:, 0], points[:, 1], s=0.1, alpha=0.5)
        ax1.set_xlabel('X (mm)')
        ax1.set_ylabel('Y (mm)')
        ax1.set_title(f'{title} - XY剖面(俯视)')
        ax1.grid(True, alpha=0.3)
        ax1.set_aspect('equal', adjustable='box')

        ax2 = self.figure.add_subplot(222)
        ax2.scatter(points[:, 0], points[:, 2], s=0.1, alpha=0.5)
        ax2.set_xlabel('X (mm)')
        ax2.set_ylabel('Z (mm)')
        ax2.set_title(f'{title} - XZ剖面(侧视)')
        ax2.grid(True, alpha=0.3)

        ax3 = self.figure.add_subplot(223)
        ax3.scatter(points[:, 1], points[:, 2], s=0.1, alpha=0.5)
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
        ax4.scatter(points_sample[:, 0], points_sample[:, 1], points_sample[:, 2], s=0.5, alpha=0.5)
        ax4.set_xlabel('X (mm)')
        ax4.set_ylabel('Y (mm)')
        ax4.set_zlabel('Z (mm)')
        ax4.set_title(f'{title} - 3D视图')

        self.canvas.draw()

    def plot_comparison(self, points1, points2, title1="ASC", title2="STL"):
        # 根据VTK可用性切换布局模式
        if VTK_AVAILABLE:
            self._switch_to_comparison_mode()
        else:
            self._switch_to_single_mode()

        self.figure.clear()
        self._clear_vtk()

        if len(points1) == 0 or len(points2) == 0:
            self.canvas.draw()
            return

        # 降采样
        if len(points1) > 10000:
            idx1 = np.random.choice(len(points1), 10000, replace=False)
            p1s = points1[idx1]
        else:
            p1s = points1
        if len(points2) > 10000:
            idx2 = np.random.choice(len(points2), 10000, replace=False)
            p2s = points2[idx2]
        else:
            p2s = points2

        if VTK_AVAILABLE:
            from matplotlib.gridspec import GridSpec
            gs = GridSpec(2, 2, figure=self.figure, hspace=0.45, wspace=0.35,
                          left=0.08, right=0.96, top=0.93, bottom=0.12)

            ax1 = self.figure.add_subplot(gs[0, :])
            ax1.scatter(p1s[:, 0], p1s[:, 1], s=0.5, alpha=0.5, c='blue', label=title1)
            ax1.scatter(p2s[:, 0], p2s[:, 1], s=0.5, alpha=0.5, c='red', label=title2)
            ax1.set_xlabel('X (mm)')
            ax1.set_ylabel('Y (mm)')
            ax1.set_title(f'{title1} vs {title2} - XY剖面(俯视)', fontsize=9)
            ax1.grid(True, alpha=0.3)
            ax1.legend(fontsize=7)
            ax1.set_aspect('equal', adjustable='datalim')

            ax2 = self.figure.add_subplot(gs[1, 0])
            ax2.scatter(p1s[:, 0], p1s[:, 2], s=0.5, alpha=0.5, c='blue', label=title1)
            ax2.scatter(p2s[:, 0], p2s[:, 2], s=0.5, alpha=0.5, c='red', label=title2)
            ax2.set_xlabel('X (mm)')
            ax2.set_ylabel('Z (mm)')
            ax2.set_title(f'{title1} vs {title2} - XZ剖面(侧视)', fontsize=9)
            ax2.grid(True, alpha=0.3)
            ax2.legend(fontsize=7)

            ax3 = self.figure.add_subplot(gs[1, 1])
            ax3.scatter(p1s[:, 1], p1s[:, 2], s=0.5, alpha=0.5, c='blue', label=title1)
            ax3.scatter(p2s[:, 1], p2s[:, 2], s=0.5, alpha=0.5, c='red', label=title2)
            ax3.set_xlabel('Y (mm)')
            ax3.set_ylabel('Z (mm)')
            ax3.set_title(f'{title1} vs {title2} - YZ剖面(正视)', fontsize=9)
            ax3.grid(True, alpha=0.3)
            ax3.legend(fontsize=7)

            self.canvas.draw()

            # VTK 3D对比渲染
            dp1 = self._filter_valid_points(points1)
            dp2 = self._filter_valid_points(points2)
            if len(dp1) > 10000:
                dp1 = dp1[np.random.choice(len(dp1), 10000, replace=False)]
            if len(dp2) > 10000:
                dp2 = dp2[np.random.choice(len(dp2), 10000, replace=False)]
            self._add_point_cloud_vtk(dp1, color=(0.0, 0.4, 1.0))
            self._add_point_cloud_vtk(dp2, color=(1.0, 0.0, 0.0))
            self._setup_vtk_camera()
            # 延迟渲染，确保VTK容器已获得有效尺寸
            QTimer.singleShot(self.VTK_RENDER_DELAY_MS, self._deferred_vtk_render)
        else:
            self.figure.subplots_adjust(hspace=0.45, wspace=0.35, left=0.08, right=0.96, top=0.93, bottom=0.12)
            ax1 = self.figure.add_subplot(221)
            ax1.scatter(p1s[:, 0], p1s[:, 1], s=0.5, alpha=0.5, c='blue', label=title1)
            ax1.scatter(p2s[:, 0], p2s[:, 1], s=0.5, alpha=0.5, c='red', label=title2)
            ax1.set_xlabel('X (mm)')
            ax1.set_ylabel('Y (mm)')
            ax1.set_title(f'{title1} vs {title2} - XY剖面(俯视)')
            ax1.grid(True, alpha=0.3)
            ax1.legend()

            ax2 = self.figure.add_subplot(222)
            ax2.scatter(p1s[:, 0], p1s[:, 2], s=0.5, alpha=0.5, c='blue', label=title1)
            ax2.scatter(p2s[:, 0], p2s[:, 2], s=0.5, alpha=0.5, c='red', label=title2)
            ax2.set_xlabel('X (mm)')
            ax2.set_ylabel('Z (mm)')
            ax2.set_title(f'{title1} vs {title2} - XZ剖面(侧视)')
            ax2.grid(True, alpha=0.3)
            ax2.legend()

            ax3 = self.figure.add_subplot(223)
            ax3.scatter(p1s[:, 1], p1s[:, 2], s=0.5, alpha=0.5, c='blue', label=title1)
            ax3.scatter(p2s[:, 1], p2s[:, 2], s=0.5, alpha=0.5, c='red', label=title2)
            ax3.set_xlabel('Y (mm)')
            ax3.set_ylabel('Z (mm)')
            ax3.set_title(f'{title1} vs {title2} - YZ剖面(正视)')
            ax3.grid(True, alpha=0.3)
            ax3.legend()

            ax4 = self.figure.add_subplot(224, projection='3d')
            ax4.scatter(p1s[:, 0], p1s[:, 1], p1s[:, 2], s=0.5, alpha=0.5, c='blue', label=title1)
            ax4.scatter(p2s[:, 0], p2s[:, 1], p2s[:, 2], s=0.5, alpha=0.5, c='red', label=title2)
            ax4.set_xlabel('X (mm)')
            ax4.set_ylabel('Y (mm)')
            ax4.set_zlabel('Z (mm)')
            ax4.set_title(f'{title1} vs {title2} - 3D对比')
            ax4.legend()

            self.canvas.draw()

    def get_vtk_screenshot(self):
        try:
            w2if = vtk.vtkWindowToImageFilter()
            w2if.SetInput(self.vtk_widget.GetRenderWindow())
            w2if.Update()
            vtk_image = w2if.GetOutput()
            h, w, _ = vtk_image.GetDimensions()
            arr = vtk.vtk.util.numpy_support.vtk_to_numpy(vtk_image.GetPointData().GetScalars())
            arr = arr.reshape(h, w, -1)
            arr = arr[:, :, :3]
            arr = np.flipud(arr)
            return arr
        except Exception:
            import logging
            logging.warning("VTK截图失败，将仅导出2D剖面图")
            return None

    def closeEvent(self, event):
        self.vtk_widget.Finalize()
        super().closeEvent(event)


@dataclass
class StepDef:
    step_id: str
    step_name: str
    is_v3: bool
    optional: bool = False
    enabled_check: Optional[str] = None
    execute_fn: Optional[str] = None


class UnifiedAnalysisWorker(QThread):
    progress_updated = pyqtSignal(int, str)
    log_message = pyqtSignal(str)
    visualization_ready = pyqtSignal(np.ndarray, str)
    comparison_ready = pyqtSignal(np.ndarray, np.ndarray, str, str)
    analysis_finished = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)

    ALL_STEPS = [
        StepDef('load', '加载ASC文件', is_v3=True, execute_fn='_execute_load'),
        StepDef('segment', '分割点云', is_v3=True, execute_fn='_execute_segment'),
        StepDef('assembly', '分析装配误差', is_v3=True, execute_fn='_execute_assembly'),
        StepDef('clean', '清理谐振陀螺点云', is_v3=True, execute_fn='_execute_clean'),
        StepDef('geometry', '分析几何误差', is_v3=True, execute_fn='_execute_geometry'),
        StepDef('stl_compare', '与STL模型对比', is_v3=True, optional=True, execute_fn='_execute_stl_compare'),
        StepDef('roughness', '表面粗糙度分析', is_v3=False, enabled_check='enable_roughness', execute_fn='_execute_roughness'),
        StepDef('waviness', '波纹度分析', is_v3=False, enabled_check='enable_waviness', execute_fn='_execute_waviness'),
        StepDef('symmetry', '对称性分析', is_v3=False, enabled_check='enable_symmetry', execute_fn='_execute_symmetry'),
        StepDef('thickness', '壁厚分析', is_v3=False, enabled_check='enable_thickness', execute_fn='_execute_thickness'),
        StepDef('resonance', '谐振参数分析', is_v3=False, enabled_check='enable_resonance', execute_fn='_execute_resonance'),
        StepDef('flatness', '平面度分析', is_v3=False, enabled_check='enable_flatness', execute_fn='_execute_flatness'),
        StepDef('roundness_full', '圆度完整评定', is_v3=False, enabled_check='enable_roundness_full', execute_fn='_execute_roundness_full'),
        StepDef('profile_filter', '轮廓滤波分析', is_v3=False, enabled_check='enable_profile_filter', execute_fn='_execute_profile_filter'),
        StepDef('tooth_analysis', '齿状结构分析', is_v3=False, enabled_check='enable_tooth_analysis', execute_fn='_execute_tooth_analysis'),
        StepDef('quality', '质量评价', is_v3=False, enabled_check='enable_quality', execute_fn='_execute_quality'),
    ]

    def __init__(self, asc_path, stl_path=None, sample_rate=100,
                 precision_analyzer=None, step_config=None):
        super().__init__()
        self.asc_path = asc_path
        self.stl_path = stl_path
        self.sample_rate = sample_rate
        self.precision_analyzer = precision_analyzer
        self.step_config = step_config or {}
        self.v3_results = {}
        self.precision_result = None
        self.hrg_points_data = None
        self.failed_steps = {}
        self._data_type = None  # 新增: 缓存数据类型

    def identify_data_type(self, file_path: str) -> str:
        """
        根据文件名前缀识别数据类型
        
        识别规则:
        - 文件名以 'fake_tooth_' 开头: 齿结构仿真数据
        - 文件名以 'fake_surface_' 开头: 表面结构仿真数据（粗糙度+波纹度）
        - 文件名以 'fake_plane_' 开头: 平面度数据
        - 其他情况: HRG球度数据
        
        参数:
            file_path: 文件路径
            
        返回:
            'tooth': 齿结构仿真数据
            'surface': 表面结构仿真数据
            'flatness': 平面度数据
            'hrg': HRG球度数据
            
        示例:
            >>> identify_data_type('/path/to/fake_tooth_hp2um.asc')
            'tooth'
            >>> identify_data_type('/path/to/fake_surface_sample.asc')
            'surface'
            >>> identify_data_type('/path/to/fake_plane_sample.asc')
            'flatness'
            >>> identify_data_type('/path/to/hrg_data.asc')
            'hrg'
        """
        filename = os.path.basename(file_path).lower()
        
        # 检查文件名前缀
        if filename.startswith('fake_tooth_'):
            return 'tooth'
        if filename.startswith('fake_surface_'):
            return 'surface'
        if filename.startswith('fake_plane_'):
            return 'flatness'
        
        return 'hrg'

    def _build_enabled_steps(self):
        enabled = []
        
        data_type = self.identify_data_type(self.asc_path)
        
        hrg_only_steps = {'segment', 'assembly', 'clean', 'geometry', 'stl_compare'}
        
        for step in self.ALL_STEPS:
            if data_type in ('flatness', 'surface', 'tooth') and step.step_id in hrg_only_steps:
                continue
            
            if step.optional:
                if step.step_id == 'stl_compare':
                    if not (self.stl_path and os.path.exists(self.stl_path)):
                        continue
            if step.enabled_check:
                if not self.step_config.get(step.enabled_check, True):
                    continue
            enabled.append(step)
        has_v4_data = any(
            s for s in enabled
            if not s.is_v3 and s.step_id != 'quality'
            and self.step_config.get(s.enabled_check, True)
        )
        if not has_v4_data:
            quality_step = next((s for s in enabled if s.step_id == 'quality'), None)
            if quality_step:
                enabled.remove(quality_step)
        return enabled

    def run(self):
        start_time = time.time()
        try:
            enabled_steps = self._build_enabled_steps()
            total = len(enabled_steps)

            for i, step in enumerate(enabled_steps, 1):
                step_start = time.time()
                pct = int(i / total * 100)
                self.progress_updated.emit(pct, step.step_name)
                self.log_message.emit(f"[{i}/{total}] {step.step_name}")

                try:
                    fn = getattr(self, step.execute_fn)
                    fn()
                except Exception as e:
                    import traceback
                    err_msg = f"{str(e)}\n{traceback.format_exc()}"
                    if step.is_v3:
                        self.error_occurred.emit(err_msg)
                        return
                    else:
                        self.failed_steps[step.step_id] = str(e)
                        self.log_message.emit(f"  失败: {str(e)}")

                step_time = time.time() - step_start
                if step.step_id not in self.failed_steps:
                    self.log_message.emit(f"  完成 (耗时: {step_time:.2f}s)")

            total_time = time.time() - start_time
            self.log_message.emit(f"\n分析流程结束 (总耗时: {total_time:.2f}s)")

            combined = self.v3_results.copy()
            if self.precision_result is not None:
                combined['v4_precision_analysis'] = self.precision_result.to_dict()
            combined['timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            combined['total_time'] = total_time
            self.analysis_finished.emit(combined)

        except Exception as e:
            import traceback
            self.error_occurred.emit(f"{str(e)}\n\n{traceback.format_exc()}")

    def _execute_load(self):
        from complete_pipeline import PointCloudProcessor
        processor = PointCloudProcessor(num_processes=4)
        
        data_type = self.identify_data_type(self.asc_path)
        if data_type in ('flatness', 'surface', 'tooth'):
            effective_sample_rate = 1
        else:
            effective_sample_rate = self.sample_rate
        
        points = processor.load_asc_file(self.asc_path, sample_rate=effective_sample_rate)
        
        # 空数据检测
        if len(points) == 0:
            raise ValueError(f"文件数据为空: {os.path.basename(self.asc_path)},请检查文件内容")
        
        self.log_message.emit(f"  点数: {len(points):,}")
        self.v3_results['total_points'] = len(points)
        self._raw_points = points
        self.visualization_ready.emit(points, "原始点云")

    def _execute_segment(self):
        from hrg_special_analyzer import HRGSpecialAnalyzer
        analyzer = HRGSpecialAnalyzer()
        hrg_points, assembly_points, bottom_plane = analyzer.segment_hrg_and_assembly(self._raw_points)
        self.log_message.emit(f"  谐振陀螺: {len(hrg_points):,} 点")
        self.log_message.emit(f"  装配结构: {len(assembly_points):,} 点")
        self.log_message.emit(f"  底部平面: {len(bottom_plane):,} 点")
        self.v3_results['segmentation'] = {
            'hrg_points': len(hrg_points),
            'assembly_points': len(assembly_points),
            'bottom_plane_points': len(bottom_plane)
        }
        self._hrg_points = hrg_points
        self._assembly_points = assembly_points
        self._bottom_plane = bottom_plane
        self._analyzer = analyzer
        self.visualization_ready.emit(hrg_points, "谐振陀螺(分割后)")

    def _execute_assembly(self):
        assembly_error = self._analyzer.analyze_assembly_error(self._hrg_points, self._bottom_plane)
        self.log_message.emit(f"  平均距离: {assembly_error['mean_distance']*1000:.2f} μm")
        self.log_message.emit(f"  标准差: {assembly_error['std_distance']*1000:.2f} μm")
        self.v3_results['assembly_error'] = assembly_error

    def _execute_clean(self):
        """
        数据清理流程
        
        根据数据类型执行不同的清理策略:
        - 齿结构数据: 跳过清理,保留所有数据点
        - 表面结构数据: 跳过清理,保留所有数据点
        - 平面度数据: 跳过清理,保留所有数据点
        - HRG数据: 执行z <= -0.1的过滤清理
        """
        # 识别数据类型(首次识别时缓存)
        if self._data_type is None:
            self._data_type = self.identify_data_type(self.asc_path)
        
        if self._data_type == 'tooth':
            # 齿结构数据清理策略: 保留所有数据
            self.log_message.emit("  检测到齿结构数据,跳过HRG清理流程")
            self._hrg_clean = self._hrg_points.copy()
            self.v3_results['hrg_cleaned_points'] = len(self._hrg_clean)
            self.hrg_points_data = self._hrg_clean.copy()
            self.log_message.emit(f"  数据点数: {len(self._hrg_clean):,}")
            self.visualization_ready.emit(self._hrg_clean, "齿结构数据")
            
        elif self._data_type == 'surface':
            # 表面结构数据清理策略: 保留所有数据
            self.log_message.emit("  检测到表面结构数据,跳过HRG清理流程")
            self._hrg_clean = self._hrg_points.copy()
            self.v3_results['hrg_cleaned_points'] = len(self._hrg_clean)
            self.hrg_points_data = self._hrg_clean.copy()
            self.log_message.emit(f"  数据点数: {len(self._hrg_clean):,}")
            self.visualization_ready.emit(self._hrg_clean, "表面结构数据")
            
        elif self._data_type == 'flatness':
            # 平面度数据清理策略: 保留所有数据
            self.log_message.emit("  检测到平面度数据,跳过HRG清理流程")
            self._hrg_clean = self._hrg_points.copy()
            self.v3_results['hrg_cleaned_points'] = len(self._hrg_clean)
            self.hrg_points_data = self._hrg_clean.copy()
            self.log_message.emit(f"  数据点数: {len(self._hrg_clean):,}")
            self.visualization_ready.emit(self._hrg_clean, "平面度数据")
            
        else:
            # HRG数据清理策略: 过滤z <= -0.1的点
            self.log_message.emit("  检测到HRG数据,执行清理流程")
            z = self._hrg_points[:, 2]
            z_threshold = -0.1
            clean_mask = z <= z_threshold
            hrg_clean = self._hrg_points[clean_mask]
            
            # 空数据检测
            if len(hrg_clean) == 0:
                raise ValueError("数据清理后为空: 所有数据点z值均大于-0.1,请检查数据有效性")
            
            self.log_message.emit(f"  清理后: {len(hrg_clean):,} 点")
            self.v3_results['hrg_cleaned_points'] = len(hrg_clean)
            self._hrg_clean = hrg_clean
            self.hrg_points_data = hrg_clean.copy()
            self.visualization_ready.emit(hrg_clean, "谐振陀螺(清理后)")

    def _execute_geometry(self):
        roundness_result = self._analyzer.analyze_roundness(self._hrg_clean)
        roundness = {
            'max_error': roundness_result.get('max_roundness_error', roundness_result.get('max_error', 0)) * 1000,
            'mean_error': roundness_result.get('mean_roundness_error', roundness_result.get('mean_error', 0)) * 1000
        }
        self.log_message.emit(f"  圆度最大: {roundness['max_error']:.2f} μm")
        self.log_message.emit(f"  圆度平均: {roundness['mean_error']:.2f} μm")

        sphericity_result = self._analyzer.analyze_sphericity_hrg_only(self._hrg_clean)
        sphericity = {
            'center': sphericity_result.get('center', [0, 0, 0]),
            'radius': sphericity_result.get('radius', 0),
            'error': sphericity_result.get('sphericity_error', sphericity_result.get('error', 0)) * 1000
        }
        self.log_message.emit(f"  球度半径: {sphericity['radius']:.3f} mm")
        self.log_message.emit(f"  球度误差: {sphericity['error']:.2f} μm")

        self.v3_results['roundness'] = roundness
        self.v3_results['sphericity'] = sphericity

        output_dir = os.path.join(package_dir, 'output')
        os.makedirs(output_dir, exist_ok=True)
        report_path = os.path.join(output_dir, 'gui_analysis_report_v3.txt')
        try:
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(str(self.v3_results))
            self.log_message.emit(f"  报告已保存: {report_path}")
        except Exception:
            pass

    def _execute_stl_compare(self):
        import trimesh
        from advanced_alignment import try_multiple_alignments

        self.log_message.emit(f"  加载STL: {os.path.basename(self.stl_path)}")
        mesh = trimesh.load(self.stl_path)
        stl_points = mesh.sample(10000)
        self.log_message.emit(f"  STL点数: {len(stl_points):,}")

        stl_aligned, align_error, strategy = try_multiple_alignments(self._hrg_clean, stl_points)
        self.log_message.emit(f"  对齐策略: {strategy}")
        self.log_message.emit(f"  对齐误差: {align_error*1000:.2f} μm")

        self.visualization_ready.emit(stl_aligned, "STL模型点云(对齐后)")
        self.comparison_ready.emit(self._hrg_clean, stl_aligned, "ASC谐振陀螺", "STL模型(对齐后)")

        stl_roundness_result = self._analyzer.analyze_roundness(stl_aligned)
        stl_roundness = {
            'max_error': stl_roundness_result.get('max_roundness_error', stl_roundness_result.get('max_error', 0)),
            'mean_error': stl_roundness_result.get('mean_roundness_error', stl_roundness_result.get('mean_error', 0))
        }
        stl_sphericity_result = self._analyzer.analyze_sphericity_hrg_only(stl_aligned)
        stl_sphericity = {
            'center': stl_sphericity_result.get('center', [0, 0, 0]),
            'radius': stl_sphericity_result.get('radius', 0),
            'error': stl_sphericity_result.get('sphericity_error', stl_sphericity_result.get('error', 0)) * 1000
        }
        roundness = self.v3_results.get('roundness', {})
        sphericity = self.v3_results.get('sphericity', {})
        self.log_message.emit(f"  圆度误差差异: {abs(roundness.get('mean_error', 0) - stl_roundness['mean_error']):.2f} μm")
        self.log_message.emit(f"  球度误差差异: {abs(sphericity.get('error', 0) - stl_sphericity['error']):.2f} μm")
        self.log_message.emit(f"  半径差异: {abs(sphericity.get('radius', 0) - stl_sphericity['radius']):.3f} mm")

        self.v3_results['stl_comparison'] = {
            'stl_roundness': stl_roundness,
            'stl_sphericity': stl_sphericity,
            'roundness_diff': abs(roundness.get('mean_error', 0) - stl_roundness['mean_error']),
            'sphericity_diff': abs(sphericity.get('error', 0) - stl_sphericity['error']),
            'radius_diff': abs(sphericity.get('radius', 0) - stl_sphericity['radius']),
            'alignment_error': align_error,
            'alignment_strategy': strategy
        }

    def _execute_roughness(self):
        # 齿结构/表面结构/平面度数据使用原始点云, HRG数据使用处理后点云
        if self._data_type in ('surface', 'flatness', 'tooth'):
            points_to_analyze = self._raw_points
        else:
            points_to_analyze = self.hrg_points_data
        r = self.precision_analyzer.roughness_analyzer.analyze(points_to_analyze)
        if self.precision_result is None:
            self.precision_result = PrecisionAnalysisResult()
        self.precision_result.roughness_result = r
        self.log_message.emit(f"  Ra: {r.ra:.3f} um")
        self.log_message.emit(f"  Rq: {r.rq:.3f} um")
        self.log_message.emit(f"  Rz: {r.rz:.3f} um")
        self.log_message.emit(f"  RSm: {r.rsm:.3f} mm")

    def _execute_waviness(self):
        # 齿结构/表面结构/平面度数据使用原始点云, HRG数据使用处理后点云
        if self._data_type in ('surface', 'flatness', 'tooth'):
            points_to_analyze = self._raw_points
        else:
            points_to_analyze = self.hrg_points_data
        r = self.precision_analyzer.waviness_analyzer.analyze(points_to_analyze)
        if self.precision_result is None:
            self.precision_result = PrecisionAnalysisResult()
        self.precision_result.waviness_result = r
        self.log_message.emit(f"  波纹度幅值: {r.waviness_amplitude:.3f} um")

    def _execute_symmetry(self):
        r = self.precision_analyzer.symmetry_analyzer.analyze(self.hrg_points_data)
        if self.precision_result is None:
            self.precision_result = PrecisionAnalysisResult()
        self.precision_result.symmetry_result = r
        for order, error in r.symmetry_errors.items():
            self.log_message.emit(f"  {order}阶: {error:.4f}")

    def _execute_thickness(self):
        r = self.precision_analyzer.thickness_analyzer.analyze(self.hrg_points_data)
        if self.precision_result is None:
            self.precision_result = PrecisionAnalysisResult()
        self.precision_result.thickness_result = r
        self.log_message.emit(f"  平均壁厚: {r.mean_thickness:.3f} mm")
        self.log_message.emit(f"  不均匀度: {r.uniformity:.4f}")

    def _execute_resonance(self):
        r = self.precision_analyzer.resonance_analyzer.analyze(self.hrg_points_data)
        if self.precision_result is None:
            self.precision_result = PrecisionAnalysisResult()
        self.precision_result.resonance_result = r
        self.log_message.emit(f"  质量分布均匀性: {r.mass_uniformity:.4f}")
        if r.frequency_shift_estimate:
            self.log_message.emit(f"  频率偏移估计: {r.frequency_shift_estimate:.6f}")

    def _execute_flatness(self):
        from flatness_analyzer import FlatnessAnalyzer
        fa = FlatnessAnalyzer(self.precision_analyzer.config.get('flatness', {}))
        
        data_type = self.identify_data_type(self.asc_path)
        if data_type in ('flatness', 'tooth'):
            points_to_analyze = self._raw_points
        else:
            points_to_analyze = self.hrg_points_data
        
        r = fa.analyze(points_to_analyze)
        if self.precision_result is None:
            self.precision_result = PrecisionAnalysisResult()
        self.precision_result.flatness_result = r
        self.log_message.emit(f"  FLTt(MZPL): {r.flt_t_mz:.3f} um")
        self.log_message.emit(f"  FLTt(LSPL): {r.flt_t_ls:.3f} um")
        self.log_message.emit(f"  FLTp(LSPL): {r.flt_p:.3f} um")
        self.log_message.emit(f"  FLTv(LSPL): {r.flt_v:.3f} um")
        self.log_message.emit(f"  FLTq(LSPL): {r.flt_q:.3f} um")

    def _execute_roundness_full(self):
        from roundness_full_analyzer import RoundnessFullAnalyzer
        ra = RoundnessFullAnalyzer(self.precision_analyzer.config.get('roundness_full', {}))
        r = ra.analyze(self.hrg_points_data)
        if self.precision_result is None:
            self.precision_result = PrecisionAnalysisResult()
        self.precision_result.roundness_full_result = r
        self.log_message.emit(f"  MZC: {r.mzc_error:.3f} um")
        self.log_message.emit(f"  LSC: {r.lsc_error:.3f} um")
        self.log_message.emit(f"  MCC: {r.mcc_error:.3f} um")
        self.log_message.emit(f"  MLC: {r.mlc_error:.3f} um")

    def _execute_profile_filter(self):
        from profile_filter_analyzer import ProfileFilterAnalyzer
        pa = ProfileFilterAnalyzer(self.precision_analyzer.config.get('profile_filter', {}))
        r = pa.analyze(self.hrg_points_data)
        if self.precision_result is None:
            self.precision_result = PrecisionAnalysisResult()
        self.precision_result.profile_filter_result = r
        self.log_message.emit(f"  lambda_c: {r.lambda_c} mm")
        self.log_message.emit(f"  lambda_s: {r.lambda_s} mm")
        d = r.to_dict()
        if 'roughness_rms' in d:
            self.log_message.emit(f"  粗糙度轮廓RMS: {d['roughness_rms']:.6f} mm")
        if 'waviness_rms' in d:
            self.log_message.emit(f"  波纹度轮廓RMS: {d['waviness_rms']:.6f} mm")

    def _execute_tooth_analysis(self):
        data_type = self.identify_data_type(self.asc_path)
        if data_type in ('flatness', 'surface', 'tooth'):
            points_to_analyze = self._raw_points
        else:
            points_to_analyze = self.hrg_points_data

        if points_to_analyze is None:
            self.log_message.emit("  跳过（无点云数据）")
            return
        
        try:
            from tooth_analysis_simple import analyze_tooth_structure
            
            tooth_result = analyze_tooth_structure(points_to_analyze, theoretical_tooth_count=48)
            
            if self.precision_result is None:
                from precision_analyzer import PrecisionAnalysisResult
                self.precision_result = PrecisionAnalysisResult()
            
            self.precision_result.tooth_analysis_result = tooth_result
            
            self.log_message.emit(f"  齿数: {tooth_result.tooth_count}")
            if tooth_result.tooth_count > 0:
                self.log_message.emit(f"  齿高: {tooth_result.tooth_height_mean:.3f} ± {tooth_result.tooth_height_std:.3f} mm")
                self.log_message.emit(f"  齿宽: {tooth_result.tooth_width_mean:.3f} ± {tooth_result.tooth_width_std:.3f} mm")
                self.log_message.emit(f"  齿厚: {tooth_result.tooth_thickness_mean:.3f} ± {tooth_result.tooth_thickness_std:.3f} mm")
                self.log_message.emit(f"  平面度: {tooth_result.flatness_mean:.6f} mm")
                self.log_message.emit(f"  齿间距: {tooth_result.tooth_spacing_mean:.3f} ± {tooth_result.tooth_spacing_std:.3f} mm")
                self.log_message.emit(f"  齿距偏差: {tooth_result.pitch_deviation_mean:.4f} ± {tooth_result.pitch_deviation_std:.4f} mm")
                self.log_message.emit(f"  周向倾角: {tooth_result.circumferential_tilt_mean:.3f} ± {tooth_result.circumferential_tilt_std:.3f} deg")
                self.log_message.emit(f"  径向倾角: {tooth_result.radial_tilt_mean:.3f} ± {tooth_result.radial_tilt_std:.3f} deg")
                self.log_message.emit(f"  质量评分: {tooth_result.quality_score:.1f} 分")
                self.log_message.emit(f"  质量等级: {tooth_result.quality_grade}")
        except Exception as e:
            import traceback
            self.log_message.emit(f"  失败: {str(e)}")
            self.failed_steps['tooth_analysis'] = str(e)

    def _execute_quality(self):
        pr = self.precision_result
        has_any = any([
            pr.roughness_result, pr.waviness_result, pr.symmetry_result,
            pr.thickness_result, pr.resonance_result, pr.flatness_result,
            pr.roundness_full_result, pr.profile_filter_result
        ])
        if not has_any:
            self.log_message.emit("  跳过（无有效指标数据）")
            return

        q = self.precision_analyzer.quality_evaluator.analyze(
            roughness_result=pr.roughness_result,
            symmetry_result=pr.symmetry_result,
            thickness_result=pr.thickness_result,
            waviness_result=pr.waviness_result,
            resonance_result=pr.resonance_result
        )
        pr.quality_result = q

        self.log_message.emit(f"  综合评分: {q.total_score:.1f} 分")
        self.log_message.emit(f"  质量等级: {q.grade}")
        if q.individual_scores:
            self.log_message.emit("  各项得分:")
            for k, s in q.individual_scores.items():
                self.log_message.emit(f"    {k}: {s:.1f}")
        if q.improvement_suggestions:
            self.log_message.emit("  改进建议:")
            for i, s in enumerate(q.improvement_suggestions, 1):
                self.log_message.emit(f"    {i}. {s}")

        v4_output = os.path.join(package_dir, 'output')
        os.makedirs(v4_output, exist_ok=True)

        pf = os.path.join(v4_output, 'v4_precision_analysis.json')
        pr.to_json(pf)
        self.log_message.emit(f"  精度分析结果已保存: {pf}")

        combined = self.v3_results.copy()
        combined['v4_precision_analysis'] = pr.to_dict()
        cf = os.path.join(v4_output, 'v4_combined_results.json')
        with open(cf, 'w', encoding='utf-8') as f:
            json.dump(combined, f, indent=2, ensure_ascii=False, default=str)
        self.log_message.emit(f"  综合结果已保存: {cf}")

        rf = os.path.join(v4_output, 'v4_analysis_report.txt')
        with open(rf, 'w', encoding='utf-8') as f:
            f.write("HRG谐振陀螺分析结果\n")
            f.write("=" * 70 + "\n\n")
            f.write("v3.0 分析结果:\n")
            for k, v in self.v3_results.items():
                f.write(f"  {k}: {v}\n")
            f.write("\nv4.0 精度分析结果:\n")
            f.write(json.dumps(pr.to_dict(), indent=2, ensure_ascii=False, default=str))
        self.log_message.emit(f"  文本报告已保存: {rf}")


class HRGPrecisionAnalyzerGUIV4(HRGCompleteAnalyzerGUIV3WithExport):

    def __init__(self):
        super().__init__()

        if PRECISION_ANALYZER_AVAILABLE:
            config_path = os.path.join(package_dir, 'config', 'default_config.yaml')
            self.precision_analyzer = PrecisionAnalyzer(config_path)
        else:
            self.precision_analyzer = None

        self.hrg_points_data = None
        self._unified_worker = None

        self.setWindowTitle("HRG谐振陀螺分析系统 v4.0")

    def init_ui(self):
        self.setGeometry(100, 100, 1400, 900)

        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)

        file_group = QGroupBox("文件选择")
        file_layout = QGridLayout()
        file_layout.addWidget(QLabel("ASC文件:"), 0, 0)
        self.asc_edit = QLineEdit()
        self.asc_edit.setPlaceholderText("选择ASC点云文件")
        file_layout.addWidget(self.asc_edit, 0, 1)
        asc_btn = QPushButton("浏览")
        asc_btn.clicked.connect(self.select_asc)
        file_layout.addWidget(asc_btn, 0, 2)
        file_layout.addWidget(QLabel("STL文件:"), 1, 0)
        self.stl_edit = QLineEdit()
        self.stl_edit.setPlaceholderText("选择STL模型文件(可选)")
        file_layout.addWidget(self.stl_edit, 1, 1)
        stl_btn = QPushButton("浏览")
        stl_btn.clicked.connect(self.select_stl)
        file_layout.addWidget(stl_btn, 1, 2)
        file_layout.addWidget(QLabel("采样率:"), 2, 0)
        self.sample_spin = QSpinBox()
        self.sample_spin.setRange(1, 1000)
        self.sample_spin.setValue(100)
        file_layout.addWidget(self.sample_spin, 2, 1)
        file_layout.addWidget(QLabel("(1/N采样,100表示1/100)"), 2, 2)
        file_group.setLayout(file_layout)
        layout.addWidget(file_group)

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

        precision_group = QGroupBox("精度分析选项")
        precision_layout = QGridLayout()
        precision_layout.setSpacing(4)
        self.roughness_check = QCheckBox("表面粗糙度 (Ra,Rq,Rz,RSm)")
        self.roughness_check.setChecked(True)
        self.roughness_check.setToolTip("GB/T 3505")
        self.waviness_check = QCheckBox("波纹度分析")
        self.waviness_check.setChecked(True)
        self.symmetry_check = QCheckBox("对称性 (2,4,6,8阶)")
        self.symmetry_check.setChecked(True)
        self.thickness_check = QCheckBox("壁厚均匀性")
        self.thickness_check.setChecked(True)
        self.resonance_check = QCheckBox("谐振参数")
        self.resonance_check.setChecked(True)
        self.quality_check = QCheckBox("质量评价")
        self.quality_check.setChecked(True)
        self.flatness_check = QCheckBox("平面度 (FLTt,FLTp,FLTv,FLTq)")
        self.flatness_check.setChecked(True)
        self.flatness_check.setToolTip("GB/T 24630")
        self.roundness_full_check = QCheckBox("圆度完整评定 (MZC,LSC,MCC,MLC)")
        self.roundness_full_check.setChecked(True)
        self.roundness_full_check.setToolTip("GB/T 7235")
        self.profile_filter_check = QCheckBox("轮廓滤波 (λs/λc)")
        self.profile_filter_check.setChecked(True)
        self.profile_filter_check.setToolTip("GB/T 6062")
        self.tooth_analysis_check = QCheckBox("齿状结构分析")
        self.tooth_analysis_check.setChecked(True)
        self.tooth_analysis_check.setToolTip("齿识别、几何测量、平整度分析")
        all_checks = [self.roughness_check, self.waviness_check, self.symmetry_check,
                      self.thickness_check, self.resonance_check, self.quality_check,
                      self.flatness_check, self.roundness_full_check, self.profile_filter_check,
                      self.tooth_analysis_check]
        cols = 3
        for i, cb in enumerate(all_checks):
            precision_layout.addWidget(cb, i // cols, i % cols)
        precision_group.setLayout(precision_layout)
        layout.addWidget(precision_group)

        splitter = QSplitter(Qt.Horizontal)
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
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        vis_group = QGroupBox("点云可视化")
        vis_layout = QVBoxLayout()
        if VTK_AVAILABLE:
            self.vis_widget = VTKVisualizationWidget()
            self._using_vtk = True
        else:
            from hrg_complete_analyzer_gui_v3 import VisualizationWidget
            self.vis_widget = VisualizationWidget()
            self._using_vtk = False
            self.add_log("提示: VTK未安装，3D对比将使用matplotlib渲染")
        vis_layout.addWidget(self.vis_widget)
        vis_group.setLayout(vis_layout)
        right_layout.addWidget(vis_group, 1)
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setSizes([380, 1020])
        layout.addWidget(splitter)

        export_progress_group = QGroupBox("导出 / 进度")
        ep_layout = QHBoxLayout()
        ep_layout.setSpacing(6)

        self.export_detailed_btn = QPushButton("导出报告")
        self.export_detailed_btn.setStyleSheet("""
            QPushButton {
                background-color: #0173B2; color: white; border: none;
                padding: 8px; font-size: 12px; border-radius: 4px;
            }
            QPushButton:hover { background-color: #015a8f; }
            QPushButton:disabled { background-color: #cccccc; }
        """)
        self.export_detailed_btn.clicked.connect(self._export_detailed_report)
        self.export_detailed_btn.setEnabled(False)
        self.export_detailed_btn.setToolTip("导出详细分析报告 (支持Word/PDF/批量)")
        ep_layout.addWidget(self.export_detailed_btn, 1)

        self.export_viz_btn = QPushButton("导出图片")
        self.export_viz_btn.setStyleSheet("""
            QPushButton {
                background-color: #2ECC71; color: white; border: none;
                padding: 8px; font-size: 12px; border-radius: 4px;
            }
            QPushButton:hover { background-color: #27ae60; }
        """)
        self.export_viz_btn.clicked.connect(self.export_visualization_image)
        self.export_viz_btn.setToolTip("将当前可视化导出为PNG (300 DPI)")
        ep_layout.addWidget(self.export_viz_btn, 1)

        self.progress_bar = QProgressBar()
        ep_layout.addWidget(self.progress_bar, 1)

        self.status_label = QLabel("就绪")
        self.status_label.setMinimumWidth(80)
        ep_layout.addWidget(self.status_label)

        export_progress_group.setLayout(ep_layout)
        layout.addWidget(export_progress_group)

        self.statusBar().showMessage("就绪")

    def update_visualization(self, points, title):
        self.vis_widget.plot_point_cloud(points, title)

    def update_comparison(self, points1, points2, title1, title2):
        self.vis_widget.plot_comparison(points1, points2, title1, title2)

    def _build_step_config(self):
        config = {}
        check_map = {
            'enable_roughness': 'roughness_check',
            'enable_waviness': 'waviness_check',
            'enable_symmetry': 'symmetry_check',
            'enable_thickness': 'thickness_check',
            'enable_resonance': 'resonance_check',
            'enable_quality': 'quality_check',
            'enable_flatness': 'flatness_check',
            'enable_roundness_full': 'roundness_full_check',
            'enable_profile_filter': 'profile_filter_check',
            'enable_tooth_analysis': 'tooth_analysis_check',
        }
        for key, cb_name in check_map.items():
            try:
                if hasattr(self, cb_name) and getattr(self, cb_name) is not None:
                    config[key] = getattr(self, cb_name).isChecked()
                else:
                    config[key] = True
            except RuntimeError:
                config[key] = True
        return config

    def start_analysis(self):
        asc_path = self.asc_edit.text()
        if not asc_path or not os.path.exists(asc_path):
            QMessageBox.warning(self, "警告", "请选择有效的ASC文件")
            return

        stl_path = self.stl_edit.text() if self.stl_edit.text() else None
        sample_rate = self.sample_spin.value()

        if self.precision_analyzer is None and not PRECISION_ANALYZER_AVAILABLE:
            QMessageBox.warning(self, "警告", "精度分析模块不可用")
            return

        self.log_text.clear()
        self.result_text.clear()

        step_config = self._build_step_config()

        self._unified_worker = UnifiedAnalysisWorker(
            asc_path=asc_path,
            stl_path=stl_path,
            sample_rate=sample_rate,
            precision_analyzer=self.precision_analyzer,
            step_config=step_config
        )

        self._unified_worker.progress_updated.connect(self.update_progress)
        self._unified_worker.log_message.connect(self.add_log)
        self._unified_worker.visualization_ready.connect(self.update_visualization)
        self._unified_worker.comparison_ready.connect(self.update_comparison)
        self._unified_worker.analysis_finished.connect(self._on_unified_analysis_complete)
        self._unified_worker.error_occurred.connect(self.show_error)

        self._unified_worker.start()
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.statusBar().showMessage("分析中...")

    def stop_analysis(self):
        if self._unified_worker and self._unified_worker.isRunning():
            self._unified_worker.terminate()
            self._unified_worker.wait()
        if hasattr(super(), 'stop_analysis'):
            super().stop_analysis()
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.statusBar().showMessage("已停止")

    def _on_unified_analysis_complete(self, results):
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.statusBar().showMessage("分析完成")

        self.worker = self._unified_worker
        if hasattr(self._unified_worker, 'v3_results'):
            self.worker.results = self._unified_worker.v3_results

        self.analysis_results_data = self._prepare_export_data(
            self._unified_worker.v3_results
        ) if hasattr(self, '_prepare_export_data') else None

        self.export_detailed_btn.setEnabled(True)

        if self._unified_worker.precision_result is not None:
            self._last_precision_result = self._unified_worker.precision_result
            self._display_precision_results(self._unified_worker.precision_result)

        self._display_v3_results(self._unified_worker.v3_results)

    def _export_detailed_report(self):
        menu = QMenu(self)
        word_action = menu.addAction("Word格式")
        pdf_action = menu.addAction("PDF格式")
        both_action = menu.addAction("批量导出(Word+PDF)")
        menu.addSeparator()
        txt_action = menu.addAction("TXT格式")

        btn_pos = self.export_detailed_btn.mapToGlobal(
            self.export_detailed_btn.rect().bottomLeft()
        )
        action = menu.exec_(btn_pos)

        if action == pdf_action:
            self._do_export_pdf()
        elif action == word_action:
            self._do_export_word()
        elif action == both_action:
            self._do_export_both()
        elif action == txt_action:
            self._do_export_txt()

    def _get_unified_report_content(self):
        v3_results = {}
        if self._unified_worker and hasattr(self._unified_worker, 'v3_results'):
            v3_results = self._unified_worker.v3_results
        elif self.worker and hasattr(self.worker, 'results'):
            v3_results = self.worker.results

        v3_content = ""
        if hasattr(self, '_generate_detailed_report_content'):
            try:
                v3_content = self._generate_detailed_report_content(v3_results)
            except Exception:
                v3_content = str(v3_results)

        v4_content = ""
        if hasattr(self, '_last_precision_result') and self._last_precision_result:
            pr = self._last_precision_result
            v4_lines = []
            v4_lines.append("=" * 80)
            v4_lines.append("加工精度分析结果")
            v4_lines.append("=" * 80)
            v4_lines.append("")
            if pr.roughness_result:
                r = pr.roughness_result
                v4_lines.append("九、表面粗糙度 (GB/T 3505)")
                v4_lines.append("-" * 80)
                v4_lines.append(f"  Ra: {r.ra:.3f} um")
                v4_lines.append(f"  Rq: {r.rq:.3f} um")
                v4_lines.append(f"  Rz: {r.rz:.3f} um")
                v4_lines.append(f"  RSm: {r.rsm:.3f} mm")
                v4_lines.append("")
            if pr.waviness_result:
                v4_lines.append("十、波纹度分析")
                v4_lines.append("-" * 80)
                v4_lines.append(f"  波纹度幅值: {pr.waviness_result.waviness_amplitude:.3f} um")
                v4_lines.append("")
            if pr.symmetry_result:
                v4_lines.append("十一、对称性分析")
                v4_lines.append("-" * 80)
                for order, error in pr.symmetry_result.symmetry_errors.items():
                    v4_lines.append(f"  {order}阶对称性误差: {error:.4f}")
                v4_lines.append("")
            if pr.thickness_result:
                th = pr.thickness_result
                v4_lines.append("十二、壁厚分析")
                v4_lines.append("-" * 80)
                v4_lines.append(f"  平均壁厚: {th.mean_thickness:.3f} mm")
                v4_lines.append(f"  标准差: {th.std_thickness:.3f} mm")
                v4_lines.append(f"  不均匀度: {th.uniformity:.4f}")
                v4_lines.append("")
            if pr.resonance_result:
                rs = pr.resonance_result
                v4_lines.append("十三、谐振参数分析")
                v4_lines.append("-" * 80)
                v4_lines.append(f"  质量分布均匀性: {rs.mass_uniformity:.4f}")
                if rs.frequency_shift_estimate:
                    v4_lines.append(f"  频率偏移估计: {rs.frequency_shift_estimate:.6f}")
                v4_lines.append("")
            if pr.flatness_result:
                fl = pr.flatness_result
                v4_lines.append("十四、平面度分析 (GB/T 24630.1-2024)")
                v4_lines.append("-" * 80)
                v4_lines.append(f"  FLTt(MZPL): {fl.flt_t_mz:.3f} um")
                v4_lines.append(f"  FLTt(LSPL): {fl.flt_t_ls:.3f} um")
                v4_lines.append(f"  FLTp(LSPL): {fl.flt_p:.3f} um")
                v4_lines.append(f"  FLTv(LSPL): {fl.flt_v:.3f} um")
                v4_lines.append(f"  FLTq(LSPL): {fl.flt_q:.3f} um")
                v4_lines.append("")
            if pr.roundness_full_result:
                rn = pr.roundness_full_result
                v4_lines.append("十五、圆度完整评定 (GB/T 7235-2004)")
                v4_lines.append("-" * 80)
                v4_lines.append(f"  MZC(最小区域圆): {rn.mzc_error:.3f} um")
                v4_lines.append(f"  LSC(最小二乘圆): {rn.lsc_error:.3f} um")
                v4_lines.append(f"  MCC(最小外接圆): {rn.mcc_error:.3f} um")
                v4_lines.append(f"  MLC(最大内接圆): {rn.mlc_error:.3f} um")
                v4_lines.append("")
            if pr.profile_filter_result:
                pf = pr.profile_filter_result
                v4_lines.append("十六、轮廓滤波分析 (GB/T 6062-2009)")
                v4_lines.append("-" * 80)
                v4_lines.append(f"  lambda_c: {pf.lambda_c} mm")
                v4_lines.append(f"  lambda_s: {pf.lambda_s} mm")
                d = pf.to_dict()
                if 'roughness_rms' in d:
                    v4_lines.append(f"  粗糙度轮廓RMS: {d['roughness_rms']:.6f} mm")
                if 'waviness_rms' in d:
                    v4_lines.append(f"  波纹度轮廓RMS: {d['waviness_rms']:.6f} mm")
                v4_lines.append("")
            if pr.quality_result:
                q = pr.quality_result
                v4_lines.append("十七、质量评价")
                v4_lines.append("-" * 80)
                v4_lines.append(f"  综合评分: {q.total_score:.1f} 分")
                v4_lines.append(f"  质量等级: {q.grade}")
                v4_lines.append("")
                v4_lines.append("  各项得分:")
                for k, s in q.individual_scores.items():
                    v4_lines.append(f"    {k}: {s:.1f}")
                if q.improvement_suggestions:
                    v4_lines.append("")
                    v4_lines.append("  改进建议:")
                    for i, s in enumerate(q.improvement_suggestions, 1):
                        v4_lines.append(f"    {i}. {s}")
                v4_lines.append("")
            if pr.tooth_analysis_result:
                ta = pr.tooth_analysis_result
                v4_lines.append("十八、齿状结构分析")
                v4_lines.append("-" * 80)
                v4_lines.append(f"  齿数: {ta.tooth_count}")
                if ta.tooth_count > 0:
                    v4_lines.append(f"  齿高: {ta.tooth_height_mean:.3f} ± {ta.tooth_height_std:.3f} mm")
                    v4_lines.append(f"  齿宽: {ta.tooth_width_mean:.3f} ± {ta.tooth_width_std:.3f} mm")
                    v4_lines.append(f"  齿厚: {ta.tooth_thickness_mean:.3f} ± {ta.tooth_thickness_std:.3f} mm")
                    v4_lines.append(f"  平面度: {ta.flatness_mean:.6f} mm")
                    v4_lines.append(f"  质量评分: {ta.quality_score:.1f} 分")
                    v4_lines.append(f"  质量等级: {ta.quality_grade}")
                v4_lines.append("")
            v4_content = "\n".join(v4_lines)

        return v3_content + "\n\n" + v4_content if v4_content else v3_content

    def _do_export_pdf(self):
        try:
            file_path, _ = QFileDialog.getSaveFileName(
                self, '保存PDF报告', 'output/HRG详细分析报告.pdf', 'PDF Files (*.pdf)'
            )
            if not file_path:
                return
            self.add_log("正在生成PDF报告...")
            report_content = self._get_unified_report_content()

            from reportlab.lib.pagesizes import A4
            from reportlab.lib.units import mm
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont

            chinese_font = 'Helvetica'
            try:
                import platform
                if platform.system() == 'Windows':
                    for fp, name in [('C:/Windows/Fonts/simsun.ttc', 'SimSun'),
                                     ('C:/Windows/Fonts/simhei.ttf', 'SimHei')]:
                        if os.path.exists(fp):
                            pdfmetrics.registerFont(TTFont(name, fp))
                            chinese_font = name
                            break
            except Exception:
                pass

            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            doc = SimpleDocTemplate(file_path, pagesize=A4,
                                    rightMargin=20*mm, leftMargin=20*mm,
                                    topMargin=20*mm, bottomMargin=20*mm)
            styles = getSampleStyleSheet()
            title_style = ParagraphStyle('CT', parent=styles['Heading1'], fontName=chinese_font, fontSize=16, spaceAfter=12, alignment=1)
            heading_style = ParagraphStyle('CH', parent=styles['Heading2'], fontName=chinese_font, fontSize=14, spaceAfter=6, spaceBefore=12)
            normal_style = ParagraphStyle('CN', parent=styles['Normal'], fontName=chinese_font, fontSize=10, spaceAfter=3)

            story = []
            for line in report_content.split('\n'):
                if line.startswith('=' * 80):
                    story.append(Spacer(1, 6))
                elif line.startswith('-' * 80):
                    story.append(Spacer(1, 3))
                elif line.startswith('HRG谐振陀螺详细分析报告'):
                    story.append(Paragraph(line, title_style))
                elif any(line.startswith(p) for p in ['一、', '二、', '三、', '四、', '五、', '六、', '七、', '八、', '九、', '十、', '十一', '十二', '十三', '十四', '十五', '十六', '十七']):
                    story.append(Paragraph(line, heading_style))
                elif line.strip():
                    line = line.replace('μm', 'μm').replace('✅', '√')
                    story.append(Paragraph(line, normal_style))
            doc.build(story)
            QMessageBox.information(self, '导出成功', f'PDF报告已生成!\n{file_path}')
            self.add_log(f"PDF报告已导出: {file_path}")
        except Exception as e:
            import traceback
            QMessageBox.critical(self, '错误', f'导出失败: {str(e)}\n\n{traceback.format_exc()}')

    def _do_export_word(self):
        try:
            file_path, _ = QFileDialog.getSaveFileName(
                self, '保存Word报告', 'output/HRG详细分析报告.docx', 'Word Files (*.docx)'
            )
            if not file_path:
                return
            self.add_log("正在生成Word报告...")
            report_content = self._get_unified_report_content()

            from docx import Document
            from docx.shared import Pt
            from docx.enum.text import WD_ALIGN_PARAGRAPH

            doc = Document()
            style = doc.styles['Normal']
            style.font.name = '宋体'
            style.font.size = Pt(10)

            for line in report_content.split('\n'):
                if line.startswith('=' * 80):
                    p = doc.add_paragraph()
                    p.add_run('─' * 60)
                elif line.startswith('-' * 80):
                    p = doc.add_paragraph()
                    p.add_run('─' * 40)
                elif line.startswith('HRG谐振陀螺详细分析报告'):
                    p = doc.add_paragraph()
                    run = p.add_run(line)
                    run.bold = True
                    run.font.size = Pt(16)
                    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                elif any(line.startswith(p) for p in ['一、', '二、', '三、', '四、', '五、', '六、', '七、', '八、', '九、', '十、', '十一', '十二', '十三', '十四', '十五', '十六', '十七']):
                    p = doc.add_paragraph()
                    run = p.add_run(line)
                    run.bold = True
                    run.font.size = Pt(14)
                elif line.strip():
                    line = line.replace('μm', 'μm').replace('✅', '√')
                    doc.add_paragraph(line)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            doc.save(file_path)
            QMessageBox.information(self, '导出成功', f'Word报告已生成!\n{file_path}')
            self.add_log(f"Word报告已导出: {file_path}")
        except Exception as e:
            import traceback
            QMessageBox.critical(self, '错误', f'导出失败: {str(e)}\n\n{traceback.format_exc()}')

    def _do_export_both(self):
        dir_path = QFileDialog.getExistingDirectory(self, '选择保存目录', 'output')
        if not dir_path:
            return
        try:
            self.add_log("正在批量导出报告...")
            pdf_path = os.path.join(dir_path, 'HRG详细分析报告.pdf')
            word_path = os.path.join(dir_path, 'HRG详细分析报告.docx')
            self._do_export_pdf_to(pdf_path)
            self._do_export_word_to(word_path)
            pdf_size = os.path.getsize(pdf_path) / 1024
            word_size = os.path.getsize(word_path) / 1024
            msg = f'批量导出成功!\n\nPDF: {pdf_size:.2f} KB\nWord: {word_size:.2f} KB'
            QMessageBox.information(self, '导出成功', msg)
            self.add_log(f"批量导出完成: PDF + Word")
        except Exception as e:
            import traceback
            QMessageBox.critical(self, '错误', f'导出失败: {str(e)}\n\n{traceback.format_exc()}')

    def _do_export_pdf_to(self, file_path):
        report_content = self._get_unified_report_content()
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import mm
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont

        chinese_font = 'Helvetica'
        try:
            import platform
            if platform.system() == 'Windows':
                for fp, name in [('C:/Windows/Fonts/simsun.ttc', 'SimSun'),
                                 ('C:/Windows/Fonts/simhei.ttf', 'SimHei')]:
                    if os.path.exists(fp):
                        pdfmetrics.registerFont(TTFont(name, fp))
                        chinese_font = name
                        break
        except Exception:
            pass

        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        doc = SimpleDocTemplate(file_path, pagesize=A4,
                                rightMargin=20*mm, leftMargin=20*mm,
                                topMargin=20*mm, bottomMargin=20*mm)
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle('CT', parent=styles['Heading1'], fontName=chinese_font, fontSize=16, spaceAfter=12, alignment=1)
        heading_style = ParagraphStyle('CH', parent=styles['Heading2'], fontName=chinese_font, fontSize=14, spaceAfter=6, spaceBefore=12)
        normal_style = ParagraphStyle('CN', parent=styles['Normal'], fontName=chinese_font, fontSize=10, spaceAfter=3)

        story = []
        for line in report_content.split('\n'):
            if line.startswith('=' * 80):
                story.append(Spacer(1, 6))
            elif line.startswith('-' * 80):
                story.append(Spacer(1, 3))
            elif line.startswith('HRG谐振陀螺详细分析报告'):
                story.append(Paragraph(line, title_style))
            elif any(line.startswith(p) for p in ['一、', '二、', '三、', '四、', '五、', '六、', '七、', '八、', '九、', '十、', '十一', '十二', '十三', '十四', '十五', '十六', '十七']):
                story.append(Paragraph(line, heading_style))
            elif line.strip():
                line = line.replace('μm', 'μm').replace('✅', '√')
                story.append(Paragraph(line, normal_style))
        doc.build(story)

    def _do_export_word_to(self, file_path):
        report_content = self._get_unified_report_content()
        from docx import Document
        from docx.shared import Pt
        from docx.enum.text import WD_ALIGN_PARAGRAPH

        doc = Document()
        style = doc.styles['Normal']
        style.font.name = '宋体'
        style.font.size = Pt(10)

        for line in report_content.split('\n'):
            if line.startswith('=' * 80):
                p = doc.add_paragraph()
                p.add_run('─' * 60)
            elif line.startswith('-' * 80):
                p = doc.add_paragraph()
                p.add_run('─' * 40)
            elif line.startswith('HRG谐振陀螺详细分析报告'):
                p = doc.add_paragraph()
                run = p.add_run(line)
                run.bold = True
                run.font.size = Pt(16)
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            elif any(line.startswith(p) for p in ['一、', '二、', '三、', '四、', '五、', '六、', '七、', '八、', '九、', '十、', '十一', '十二', '十三', '十四', '十五', '十六', '十七']):
                p = doc.add_paragraph()
                run = p.add_run(line)
                run.bold = True
                run.font.size = Pt(14)
            elif line.strip():
                line = line.replace('μm', 'μm').replace('✅', '√')
                doc.add_paragraph(line)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        doc.save(file_path)

    def _do_export_txt(self):
        try:
            file_path, _ = QFileDialog.getSaveFileName(
                self, '保存详细报告', 'output/HRG详细分析报告.txt', 'Text Files (*.txt)'
            )
            if not file_path:
                return
            self.add_log("正在生成TXT报告...")
            report_content = self._get_unified_report_content()
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(report_content)
            QMessageBox.information(self, '导出成功', f'报告已生成!\n{file_path}')
            self.add_log(f"TXT报告已导出: {file_path}")
        except Exception as e:
            import traceback
            QMessageBox.critical(self, '错误', f'导出失败: {str(e)}\n\n{traceback.format_exc()}')

    def _display_v3_results(self, results):
        if not results:
            return
        t = "=" * 70 + "\n"
        t += "HRG完整分析结果\n"
        t += "=" * 70 + "\n\n"
        t += f"分析时间: {results.get('timestamp', 'N/A')}\n"
        t += f"总点数: {results.get('total_points', 0):,}\n\n"

        seg = results.get('segmentation', {})
        t += "-" * 70 + "\n1. 点云分割\n" + "-" * 70 + "\n"
        t += f"  谐振陀螺: {seg.get('hrg_points', 0):,} 点\n"
        t += f"  装配结构: {seg.get('assembly_points', 0):,} 点\n"
        t += f"  底部平面: {seg.get('bottom_plane_points', 0):,} 点\n"
        t += f"  清理后谐振陀螺: {results.get('hrg_cleaned_points', 0):,} 点\n\n"

        asm = results.get('assembly_error', {})
        t += "-" * 70 + "\n2. 装配误差\n" + "-" * 70 + "\n"
        t += f"  平均距离: {asm.get('mean_distance', 0)*1000:.2f} μm\n"
        t += f"  标准差: {asm.get('std_distance', 0)*1000:.2f} μm\n\n"

        rn = results.get('roundness', {})
        t += "-" * 70 + "\n3. 圆度误差\n" + "-" * 70 + "\n"
        t += f"  最大: {rn.get('max_error', 0):.2f} μm\n"
        t += f"  平均: {rn.get('mean_error', 0):.2f} μm\n\n"

        sp = results.get('sphericity', {})
        t += "-" * 70 + "\n4. 球度误差\n" + "-" * 70 + "\n"
        t += f"  半径: {sp.get('radius', 0):.3f} mm\n"
        t += f"  误差: {sp.get('error', 0):.2f} μm\n\n"

        stl = results.get('stl_comparison', {})
        if stl:
            t += "-" * 70 + "\n5. STL对比\n" + "-" * 70 + "\n"
            t += f"  圆度误差差异: {stl.get('roundness_diff', 0):.2f} μm\n"
            t += f"  球度误差差异: {stl.get('sphericity_diff', 0):.2f} μm\n"
            t += f"  半径差异: {stl.get('radius_diff', 0):.3f} mm\n\n"

        cur = self.result_text.toPlainText()
        self.result_text.setText(t + cur)

    def _display_precision_results(self, pr):
        t = "\n" + "=" * 70 + "\n"
        t += "加工精度分析结果\n"
        t += "=" * 70 + "\n\n"

        if pr.roughness_result:
            r = pr.roughness_result
            t += "-" * 70 + "\n【表面粗糙度】\n" + "-" * 70 + "\n"
            t += f"  Ra: {r.ra:.3f} um\n  Rq: {r.rq:.3f} um\n"
            t += f"  Rz: {r.rz:.3f} um\n  RSm: {r.rsm:.3f} mm\n\n"

        if pr.waviness_result:
            t += "-" * 70 + "\n【波纹度】\n" + "-" * 70 + "\n"
            t += f"  波纹度幅值: {pr.waviness_result.waviness_amplitude:.3f} um\n\n"

        if pr.symmetry_result:
            t += "-" * 70 + "\n【对称性】\n" + "-" * 70 + "\n"
            for order, error in pr.symmetry_result.symmetry_errors.items():
                t += f"  {order}阶: {error:.4f}\n"
            t += "\n"

        if pr.thickness_result:
            th = pr.thickness_result
            t += "-" * 70 + "\n【壁厚】\n" + "-" * 70 + "\n"
            t += f"  平均壁厚: {th.mean_thickness:.3f} mm\n"
            t += f"  标准差: {th.std_thickness:.3f} mm\n"
            t += f"  不均匀度: {th.uniformity:.4f}\n\n"

        if pr.resonance_result:
            rs = pr.resonance_result
            t += "-" * 70 + "\n【谐振参数】\n" + "-" * 70 + "\n"
            t += f"  质量分布均匀性: {rs.mass_uniformity:.4f}\n"
            if rs.frequency_shift_estimate:
                t += f"  频率偏移估计: {rs.frequency_shift_estimate:.6f}\n"
            t += "\n"

        if pr.flatness_result:
            fl = pr.flatness_result
            t += "-" * 70 + "\n【平面度 GB/T 24630.1-2024】\n" + "-" * 70 + "\n"
            t += f"  FLTt(MZPL): {fl.flt_t_mz:.3f} um\n"
            t += f"  FLTt(LSPL): {fl.flt_t_ls:.3f} um\n"
            t += f"  FLTp(LSPL): {fl.flt_p:.3f} um\n"
            t += f"  FLTv(LSPL): {fl.flt_v:.3f} um\n"
            t += f"  FLTq(LSPL): {fl.flt_q:.3f} um\n\n"

        if pr.roundness_full_result:
            rn = pr.roundness_full_result
            t += "-" * 70 + "\n【圆度完整评定 GB/T 7235-2004】\n" + "-" * 70 + "\n"
            t += f"  MZC(最小区域圆): {rn.mzc_error:.3f} um\n"
            t += f"  LSC(最小二乘圆): {rn.lsc_error:.3f} um\n"
            t += f"  MCC(最小外接圆): {rn.mcc_error:.3f} um\n"
            t += f"  MLC(最大内接圆): {rn.mlc_error:.3f} um\n\n"

        if pr.profile_filter_result:
            pf = pr.profile_filter_result
            t += "-" * 70 + "\n【轮廓滤波 GB/T 6062-2009】\n" + "-" * 70 + "\n"
            t += f"  lambda_c: {pf.lambda_c} mm\n"
            t += f"  lambda_s: {pf.lambda_s} mm\n"
            d = pf.to_dict()
            if 'roughness_rms' in d:
                t += f"  粗糙度轮廓RMS: {d['roughness_rms']:.6f} mm\n"
            if 'waviness_rms' in d:
                t += f"  波纹度轮廓RMS: {d['waviness_rms']:.6f} mm\n"
            t += "\n"

        if pr.quality_result:
            q = pr.quality_result
            t += "-" * 70 + "\n【质量评价】\n" + "-" * 70 + "\n"
            t += f"  综合评分: {q.total_score:.1f} 分\n  质量等级: {q.grade}\n\n"
            t += "  各项得分:\n"
            for k, s in q.individual_scores.items():
                t += f"    {k}: {s:.1f}\n"
            if q.improvement_suggestions:
                t += "\n  改进建议:\n"
                for i, s in enumerate(q.improvement_suggestions, 1):
                    t += f"    {i}. {s}\n"
            t += "\n"

        t += f"精度分析耗时: {pr.analysis_time:.2f} 秒\n"
        t += "=" * 70 + "\n"

        cur = self.result_text.toPlainText()
        self.result_text.setText(cur + t)

    def export_visualization_image(self):
        try:
            if not hasattr(self, 'vis_widget') or self.vis_widget is None:
                QMessageBox.warning(self, "提示", "无可视化窗口")
                return

            default_fn = f"visualization_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            v4_output = os.path.join(package_dir, 'output')
            os.makedirs(v4_output, exist_ok=True)

            file_path, _ = QFileDialog.getSaveFileName(
                self, "保存可视化图片",
                os.path.join(v4_output, default_fn),
                "PNG (*.png);;JPEG (*.jpg);;All (*)"
            )
            if not file_path:
                return

            if self._using_vtk and hasattr(self.vis_widget, 'get_vtk_screenshot'):
                import matplotlib.pyplot as plt
                vtk_arr = self.vis_widget.get_vtk_screenshot()
                if vtk_arr is not None:
                    fig, axes = plt.subplots(1, 2, figsize=(16, 8))
                    self.vis_widget.figure.tight_layout()
                    self.vis_widget.canvas.draw()
                    axes[0].imshow(self.vis_widget.figure.canvas.buffer_rgba())
                    axes[0].set_title("2D 剖面图")
                    axes[0].axis('off')
                    axes[1].imshow(vtk_arr)
                    axes[1].set_title("3D 点云 (VTK)")
                    axes[1].axis('off')
                    fig.tight_layout()
                    fig.savefig(file_path, dpi=300, bbox_inches='tight',
                                facecolor='white', edgecolor='none')
                    plt.close(fig)
                else:
                    self.vis_widget.figure.savefig(
                        file_path, dpi=300, bbox_inches='tight',
                        facecolor='white', edgecolor='none'
                    )
            else:
                if not hasattr(self.vis_widget, 'figure'):
                    QMessageBox.warning(self, "提示", "可视化窗口无图形数据")
                    return
                self.vis_widget.figure.savefig(
                    file_path, dpi=300, bbox_inches='tight',
                    facecolor='white', edgecolor='none'
                )

            self.add_log(f"\n可视化图片已导出: {file_path}")
            QMessageBox.information(self, "成功", f"已导出:\n{file_path}")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"导出失败:\n{str(e)}")




if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    window = HRGPrecisionAnalyzerGUIV4()
    window.show()
    sys.exit(app.exec_())
