"""
HRG完整分析GUI v3.0 - 集成报告导出功能
在原有GUI基础上添加PDF和Word报告导出按钮
"""

import sys
import os

# 设置路径
script_dir = os.path.dirname(os.path.abspath(__file__))
package_dir = os.path.dirname(script_dir)
core_dir = os.path.join(package_dir, 'core')
v1_core_dir = os.path.join(package_dir, 'v1.0_Special_Analyzer', 'core')
report_export_dir = os.path.join(package_dir, 'report_export')

# 添加所有需要的路径
paths_to_add = [
    script_dir,   # 添加script_dir以找到同目录下的GUI模块
    package_dir,  # 添加package_dir以找到advanced_alignment.py
    core_dir,
    v1_core_dir,
    report_export_dir
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
except ImportError as e:
    print(f"导入错误: {e}")
    sys.exit(1)

# 导入报告导出模块
try:
    from report_export.export_controller import ExportController
    from report_export.models.export_request import ExportRequest
    REPORT_EXPORT_AVAILABLE = True
except ImportError as e:
    print(f"警告: 报告导出功能不可用: {e}")
    print("请安装依赖: pip install reportlab python-docx Pillow")
    REPORT_EXPORT_AVAILABLE = False


# 导入原始GUI的所有内容
from hrg_complete_analyzer_gui_v3 import *


class HRGCompleteAnalyzerGUIV3WithExport(HRGCompleteAnalyzerGUIV3):
    """HRG完整分析GUI v3 - 带报告导出功能"""

    def init_ui(self):
        """初始化UI - 在原有基础上添加导出按钮"""
        # 调用父类的初始化
        super().init_ui()

        # 添加报告导出按钮组
        self._add_export_buttons()

    def _add_export_buttons(self):
        """添加报告导出按钮"""
        # 找到控制按钮的布局
        # 在原有GUI中，按钮布局在第417-430行
        # 我们需要在停止按钮后添加导出按钮

        # 获取主窗口的布局
        main_widget = self.centralWidget()
        main_layout = main_widget.layout()

        # 创建导出按钮组
        export_group = QGroupBox("报告导出")
        export_layout = QHBoxLayout()

        # 详细报告导出按钮（始终可用）
        self.export_detailed_btn = QPushButton("📋 导出详细报告")
        self.export_detailed_btn.setStyleSheet("""
            QPushButton {
                background-color: #9467BD;
                color: white;
                border: none;
                padding: 8px;
                font-size: 12px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #7d5a9e;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.export_detailed_btn.clicked.connect(self.export_detailed_report)
        self.export_detailed_btn.setEnabled(False)  # 初始禁用，分析完成后启用
        export_layout.addWidget(self.export_detailed_btn)

        if REPORT_EXPORT_AVAILABLE:
            # PDF导出按钮
            self.export_pdf_btn = QPushButton("📄 导出PDF报告")
            self.export_pdf_btn.setStyleSheet("""
                QPushButton {
                    background-color: #0173B2;
                    color: white;
                    border: none;
                    padding: 8px;
                    font-size: 12px;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #015a8f;
                }
                QPushButton:disabled {
                    background-color: #cccccc;
                }
            """)
            self.export_pdf_btn.clicked.connect(self.export_pdf_report)
            self.export_pdf_btn.setEnabled(False)  # 初始禁用，分析完成后启用
            export_layout.addWidget(self.export_pdf_btn)

            # Word导出按钮
            self.export_word_btn = QPushButton("📝 导出Word报告")
            self.export_word_btn.setStyleSheet("""
                QPushButton {
                    background-color: #DE8F05;
                    color: white;
                    border: none;
                    padding: 8px;
                    font-size: 12px;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #b87404;
                }
                QPushButton:disabled {
                    background-color: #cccccc;
                }
            """)
            self.export_word_btn.clicked.connect(self.export_word_report)
            self.export_word_btn.setEnabled(False)
            export_layout.addWidget(self.export_word_btn)

            # 批量导出按钮
            self.export_both_btn = QPushButton("📦 批量导出")
            self.export_both_btn.setStyleSheet("""
                QPushButton {
                    background-color: #009988;
                    color: white;
                    border: none;
                    padding: 8px;
                    font-size: 12px;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #007a6e;
                }
                QPushButton:disabled {
                    background-color: #cccccc;
                }
            """)
            self.export_both_btn.clicked.connect(self.export_both_reports)
            self.export_both_btn.setEnabled(False)
            export_layout.addWidget(self.export_both_btn)

        else:
            # 显示不可用提示
            unavailable_label = QLabel("⚠️ 报告导出功能不可用 - 请安装依赖: pip install reportlab python-docx Pillow")
            unavailable_label.setStyleSheet("color: #CC3311; padding: 10px;")
            export_layout.addWidget(unavailable_label)

        export_group.setLayout(export_layout)

        # 将导出按钮组插入到进度条之前
        # 找到进度条的位置
        for i in range(main_layout.count()):
            item = main_layout.itemAt(i)
            if item and item.widget() and isinstance(item.widget(), QGroupBox):
                if item.widget().title() == "进度":
                    main_layout.insertWidget(i, export_group)
                    break

        # 保存分析结果数据
        self.analysis_results_data = None

    def analysis_complete(self, results):
        """分析完成处理 - 重写以保存结果并启用导出按钮"""
        # 调用父类的方法
        super().analysis_complete(results)

        # 保存分析结果数据
        self.analysis_results_data = self._prepare_export_data(results)

        # 启用导出按钮
        self.export_detailed_btn.setEnabled(True)  # 详细报告按钮始终可用
        
        if REPORT_EXPORT_AVAILABLE:
            self.export_pdf_btn.setEnabled(True)
            self.export_word_btn.setEnabled(True)
            self.export_both_btn.setEnabled(True)

            self.add_log("✅ 报告导出功能已启用，可以导出PDF或Word格式报告")
        
        self.add_log("✅ 详细报告导出功能已启用")

    def _prepare_export_data(self, results):
        """准备导出数据"""
        if not results:
            return None

        export_data = {}

        # 装配误差
        if 'assembly_error' in results:
            ae = results['assembly_error']
            export_data['assembly_error'] = {
                'mean_distance': ae.get('mean_distance', 0),
                'std_distance': ae.get('std_distance', 0),
                'min_distance': ae.get('min_distance', 0),
                'max_distance': ae.get('max_distance', 0),
            }

        # 圆度误差
        if 'roundness' in results:
            rd = results['roundness']
            export_data['roundness'] = {
                'max_error': rd.get('max_error', rd.get('max_roundness_error', 0)),
                'mean_error': rd.get('mean_error', rd.get('mean_roundness_error', 0)),
            }

        # 球度误差
        if 'sphericity' in results:
            sp = results['sphericity']
            center = sp.get('center', [0, 0, 0])
            export_data['sphericity'] = {
                'center': center.tolist() if hasattr(center, 'tolist') else center,
                'radius': sp.get('radius', 0),
                'error': sp.get('error', sp.get('sphericity_error', 0)),
            }

        return export_data

    def export_pdf_report(self):
        """导出PDF报告"""
        if not hasattr(self, 'worker') or not self.worker:
            QMessageBox.warning(self, "警告", "没有可导出的分析结果！")
            return
        
        # 选择保存路径
        file_path, _ = QFileDialog.getSaveFileName(
            self, '保存PDF报告',
            'output/HRG详细分析报告.pdf',
            'PDF Files (*.pdf)'
        )
        
        if not file_path:
            return
        
        try:
            self.add_log("正在生成PDF报告...")
            
            # 获取分析结果
            results = self.worker.results if hasattr(self.worker, 'results') else {}
            
            # 生成详细报告内容
            report_content = self._generate_detailed_report_content(results)
            
            # 使用reportlab生成PDF
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.units import mm
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont
            
            # 注册中文字体
            try:
                # 尝试使用系统中的中文字体
                import platform
                if platform.system() == 'Windows':
                    # Windows系统，使用宋体
                    font_path = 'C:/Windows/Fonts/simsun.ttc'
                    if os.path.exists(font_path):
                        pdfmetrics.registerFont(TTFont('SimSun', font_path))
                        chinese_font = 'SimSun'
                    else:
                        # 如果宋体不存在，尝试黑体
                        font_path = 'C:/Windows/Fonts/simhei.ttf'
                        if os.path.exists(font_path):
                            pdfmetrics.registerFont(TTFont('SimHei', font_path))
                            chinese_font = 'SimHei'
                        else:
                            chinese_font = 'Helvetica'
                else:
                    # 非Windows系统，尝试使用Noto Sans CJK
                    chinese_font = 'Helvetica'
            except:
                chinese_font = 'Helvetica'
            
            # 创建PDF文档
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            doc = SimpleDocTemplate(file_path, pagesize=A4,
                                  rightMargin=20*mm, leftMargin=20*mm,
                                  topMargin=20*mm, bottomMargin=20*mm)
            
            # 获取样式
            styles = getSampleStyleSheet()
            
            # 创建自定义样式（使用中文字体）
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontName=chinese_font,
                fontSize=16,
                spaceAfter=12,
                alignment=1  # 居中
            )
            
            heading_style = ParagraphStyle(
                'CustomHeading',
                parent=styles['Heading2'],
                fontName=chinese_font,
                fontSize=14,
                spaceAfter=6,
                spaceBefore=12
            )
            
            normal_style = ParagraphStyle(
                'CustomNormal',
                parent=styles['Normal'],
                fontName=chinese_font,
                fontSize=10,
                spaceAfter=3
            )
            
            # 构建PDF内容
            story = []
            
            # 将报告内容按行处理
            lines = report_content.split('\n')
            for line in lines:
                if line.startswith('=' * 80):
                    story.append(Spacer(1, 6))
                elif line.startswith('-' * 80):
                    story.append(Spacer(1, 3))
                elif line.startswith('HRG谐振陀螺详细分析报告'):
                    story.append(Paragraph(line, title_style))
                elif line.startswith('一、') or line.startswith('二、') or \
                     line.startswith('三、') or line.startswith('四、') or \
                     line.startswith('五、') or line.startswith('六、') or \
                     line.startswith('七、') or line.startswith('八、') or \
                     line.startswith('九、'):
                    story.append(Paragraph(line, heading_style))
                elif line.strip():
                    # 处理特殊字符
                    line = line.replace('μm', 'μm').replace('✅', '√')
                    story.append(Paragraph(line, normal_style))
            
            # 生成PDF
            doc.build(story)
            
            QMessageBox.information(
                self, '导出成功',
                f'PDF报告已成功生成！\n\n'
                f'文件路径:\n{file_path}\n\n'
                f'文件大小: {os.path.getsize(file_path)/1024:.2f} KB'
            )
            self.add_log(f"✅ PDF报告已导出: {file_path}")
            
        except Exception as e:
            import traceback
            QMessageBox.critical(self, '错误', f'导出失败: {str(e)}\n\n{traceback.format_exc()}')

    def export_word_report(self):
        """导出Word报告"""
        if not hasattr(self, 'worker') or not self.worker:
            QMessageBox.warning(self, "警告", "没有可导出的分析结果！")
            return
        
        # 选择保存路径
        file_path, _ = QFileDialog.getSaveFileName(
            self, '保存Word报告',
            'output/HRG详细分析报告.docx',
            'Word Files (*.docx)'
        )
        
        if not file_path:
            return
        
        try:
            self.add_log("正在生成Word报告...")
            
            # 获取分析结果
            results = self.worker.results if hasattr(self.worker, 'results') else {}
            
            # 生成详细报告内容
            report_content = self._generate_detailed_report_content(results)
            
            # 使用python-docx生成Word文档
            from docx import Document
            from docx.shared import Pt, Inches
            from docx.enum.text import WD_ALIGN_PARAGRAPH
            
            # 创建Word文档
            doc = Document()
            
            # 设置默认字体
            style = doc.styles['Normal']
            font = style.font
            font.name = '宋体'
            font.size = Pt(10)
            
            # 将报告内容按行处理
            lines = report_content.split('\n')
            for line in lines:
                if line.startswith('=' * 80):
                    # 添加分隔线
                    p = doc.add_paragraph()
                    p.add_run('─' * 60)
                elif line.startswith('-' * 80):
                    # 添加短分隔线
                    p = doc.add_paragraph()
                    p.add_run('─' * 40)
                elif line.startswith('HRG谐振陀螺详细分析报告'):
                    # 标题
                    p = doc.add_paragraph()
                    run = p.add_run(line)
                    run.bold = True
                    run.font.size = Pt(16)
                    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                elif line.startswith('一、') or line.startswith('二、') or \
                     line.startswith('三、') or line.startswith('四、') or \
                     line.startswith('五、') or line.startswith('六、') or \
                     line.startswith('七、') or line.startswith('八、') or \
                     line.startswith('九、'):
                    # 章节标题
                    p = doc.add_paragraph()
                    run = p.add_run(line)
                    run.bold = True
                    run.font.size = Pt(14)
                elif line.strip():
                    # 普通文本
                    # 处理特殊字符
                    line = line.replace('μm', 'μm').replace('✅', '√')
                    doc.add_paragraph(line)
            
            # 保存文档
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            doc.save(file_path)
            
            QMessageBox.information(
                self, '导出成功',
                f'Word报告已成功生成！\n\n'
                f'文件路径:\n{file_path}\n\n'
                f'文件大小: {os.path.getsize(file_path)/1024:.2f} KB'
            )
            self.add_log(f"✅ Word报告已导出: {file_path}")
            
        except Exception as e:
            import traceback
            QMessageBox.critical(self, '错误', f'导出失败: {str(e)}\n\n{traceback.format_exc()}')

    def export_both_reports(self):
        """批量导出PDF和Word报告"""
        if not hasattr(self, 'worker') or not self.worker:
            QMessageBox.warning(self, "警告", "没有可导出的分析结果！")
            return
        
        # 选择保存目录
        dir_path = QFileDialog.getExistingDirectory(
            self, '选择保存目录',
            'output'
        )
        
        if not dir_path:
            return
        
        try:
            self.add_log("正在批量导出报告...")
            
            # 导出PDF
            pdf_path = os.path.join(dir_path, 'HRG详细分析报告.pdf')
            self.export_pdf_report_internal(pdf_path)
            
            # 导出Word
            word_path = os.path.join(dir_path, 'HRG详细分析报告.docx')
            self.export_word_report_internal(word_path)
            
            # 显示结果
            pdf_size = os.path.getsize(pdf_path) / 1024
            word_size = os.path.getsize(word_path) / 1024
            
            msg = f'批量导出成功！\n\n生成文件:\n'
            msg += f'\nHRG详细分析报告.pdf ({pdf_size:.2f} KB)'
            msg += f'\nHRG详细分析报告.docx ({word_size:.2f} KB)'
            msg += f'\n\n总大小: {(pdf_size + word_size)/1024:.2f} MB'
            
            QMessageBox.information(self, '导出成功', msg)
            self.add_log(f"✅ 批量导出完成: 2个文件")
            
        except Exception as e:
            import traceback
            QMessageBox.critical(self, '错误', f'导出失败: {str(e)}\n\n{traceback.format_exc()}')
    
    def export_pdf_report_internal(self, file_path):
        """内部方法：导出PDF报告"""
        # 获取分析结果
        results = self.worker.results if hasattr(self.worker, 'results') else {}
        
        # 生成详细报告内容
        report_content = self._generate_detailed_report_content(results)
        
        # 使用reportlab生成PDF
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import mm
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        
        # 注册中文字体
        try:
            import platform
            if platform.system() == 'Windows':
                font_path = 'C:/Windows/Fonts/simsun.ttc'
                if os.path.exists(font_path):
                    pdfmetrics.registerFont(TTFont('SimSun', font_path))
                    chinese_font = 'SimSun'
                else:
                    font_path = 'C:/Windows/Fonts/simhei.ttf'
                    if os.path.exists(font_path):
                        pdfmetrics.registerFont(TTFont('SimHei', font_path))
                        chinese_font = 'SimHei'
                    else:
                        chinese_font = 'Helvetica'
            else:
                chinese_font = 'Helvetica'
        except:
            chinese_font = 'Helvetica'
        
        # 创建PDF文档
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        doc = SimpleDocTemplate(file_path, pagesize=A4,
                              rightMargin=20*mm, leftMargin=20*mm,
                              topMargin=20*mm, bottomMargin=20*mm)
        
        # 获取样式
        styles = getSampleStyleSheet()
        
        # 创建自定义样式（使用中文字体）
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontName=chinese_font,
            fontSize=16,
            spaceAfter=12,
            alignment=1
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontName=chinese_font,
            fontSize=14,
            spaceAfter=6,
            spaceBefore=12
        )
        
        normal_style = ParagraphStyle(
            'CustomNormal',
            parent=styles['Normal'],
            fontName=chinese_font,
            fontSize=10,
            spaceAfter=3
        )
        
        # 构建PDF内容
        story = []
        
        lines = report_content.split('\n')
        for line in lines:
            if line.startswith('=' * 80):
                story.append(Spacer(1, 6))
            elif line.startswith('-' * 80):
                story.append(Spacer(1, 3))
            elif line.startswith('HRG谐振陀螺详细分析报告'):
                story.append(Paragraph(line, title_style))
            elif line.startswith('一、') or line.startswith('二、') or \
                 line.startswith('三、') or line.startswith('四、') or \
                 line.startswith('五、') or line.startswith('六、') or \
                 line.startswith('七、') or line.startswith('八、') or \
                 line.startswith('九、'):
                story.append(Paragraph(line, heading_style))
            elif line.strip():
                line = line.replace('μm', 'μm').replace('✅', '√')
                story.append(Paragraph(line, normal_style))
        
        doc.build(story)
    
    def export_word_report_internal(self, file_path):
        """内部方法：导出Word报告"""
        # 获取分析结果
        results = self.worker.results if hasattr(self.worker, 'results') else {}
        
        # 生成详细报告内容
        report_content = self._generate_detailed_report_content(results)
        
        # 使用python-docx生成Word文档
        from docx import Document
        from docx.shared import Pt
        from docx.enum.text import WD_ALIGN_PARAGRAPH
        
        # 创建Word文档
        doc = Document()
        
        # 设置默认字体
        style = doc.styles['Normal']
        font = style.font
        font.name = '宋体'
        font.size = Pt(10)
        
        # 将报告内容按行处理
        lines = report_content.split('\n')
        for line in lines:
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
            elif line.startswith('一、') or line.startswith('二、') or \
                 line.startswith('三、') or line.startswith('四、') or \
                 line.startswith('五、') or line.startswith('六、') or \
                 line.startswith('七、') or line.startswith('八、') or \
                 line.startswith('九、'):
                p = doc.add_paragraph()
                run = p.add_run(line)
                run.bold = True
                run.font.size = Pt(14)
            elif line.strip():
                line = line.replace('μm', 'μm').replace('✅', '√')
                doc.add_paragraph(line)
        
        # 保存文档
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        doc.save(file_path)
    
    def export_detailed_report(self):
        """导出详细报告（TXT格式）"""
        if not hasattr(self, 'worker') or not self.worker:
            QMessageBox.warning(self, "警告", "没有可导出的分析结果！")
            return
        
        # 选择保存路径
        file_path, _ = QFileDialog.getSaveFileName(
            self, '保存详细报告',
            'output/HRG详细分析报告.txt',
            'Text Files (*.txt)'
        )
        
        if not file_path:
            return
        
        try:
            self.add_log("正在生成详细报告...")
            
            # 获取分析结果
            results = self.worker.results if hasattr(self.worker, 'results') else {}
            
            # 生成报告内容
            report_content = self._generate_detailed_report_content(results)
            
            # 保存报告
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(report_content)
            
            QMessageBox.information(
                self, '导出成功',
                f'详细报告已成功生成！\n\n'
                f'文件路径:\n{file_path}\n\n'
                f'文件大小: {os.path.getsize(file_path)/1024:.2f} KB'
            )
            self.add_log(f"✅ 详细报告已导出: {file_path}")
            
        except Exception as e:
            import traceback
            QMessageBox.critical(self, '错误', f'导出失败: {str(e)}\n\n{traceback.format_exc()}')
    
    def _generate_detailed_report_content(self, results):
        """生成详细报告内容"""
        from datetime import datetime
        import numpy as np
        
        # 获取基本信息
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        asc_file = os.path.basename(self.asc_edit.text()) if hasattr(self, 'asc_edit') else 'N/A'
        stl_file = os.path.basename(self.stl_edit.text()) if hasattr(self, 'stl_edit') and self.stl_edit.text() else None
        
        # 构建报告
        report = []
        report.append("=" * 80)
        report.append("HRG谐振陀螺详细分析报告")
        report.append("=" * 80)
        report.append("")
        
        # 一、基本信息
        report.append("一、基本信息")
        report.append("-" * 80)
        report.append(f"报告生成时间: {timestamp}")
        report.append(f"ASC数据文件: {asc_file}")
        if stl_file:
            report.append(f"STL模型文件: {stl_file}")
        report.append(f"分析软件版本: v3.0")
        report.append(f"执行标准: GB/T 24630-2009 (球度), GB/T 7235-2004 (圆度)")
        report.append("")
        
        # 二、原始数据统计
        if 'total_points' in results:
            report.append("二、原始数据统计")
            report.append("-" * 80)
            report.append(f"总点数: {results['total_points']:,}")
            report.append("")
        
        # 三、点云分割结果
        if 'segmentation' in results:
            seg = results['segmentation']
            total = results.get('total_points', 1)
            report.append("三、点云分割结果")
            report.append("-" * 80)
            report.append(f"分割算法: Z坐标直方图 + XY距离聚类")
            report.append(f"谐振陀螺点数: {seg.get('hrg_points', 0):,} ({seg.get('hrg_points', 0)/total*100:.2f}%)")
            report.append(f"装配结构点数: {seg.get('assembly_points', 0):,} ({seg.get('assembly_points', 0)/total*100:.2f}%)")
            report.append(f"底部平面点数: {seg.get('bottom_plane_points', 0):,} ({seg.get('bottom_plane_points', 0)/total*100:.2f}%)")
            report.append(f"清理后谐振陀螺: {results.get('hrg_cleaned_points', 0):,} 点 (去除虚影)")
            report.append("")
        
        # 四、装配误差分析
        if 'assembly_error' in results:
            ae = results['assembly_error']
            report.append("四、装配误差分析")
            report.append("-" * 80)
            report.append("分析对象: 谐振陀螺齿状底部到装配平面的距离")
            report.append("")
            report.append("统计结果:")
            report.append(f"  平均距离: {ae.get('mean_distance', 0):.6f} mm ({ae.get('mean_distance', 0)*1000:.2f} μm)")
            report.append(f"  标准差: {ae.get('std_distance', 0):.6f} mm ({ae.get('std_distance', 0)*1000:.2f} μm)")
            report.append(f"  最小距离: {ae.get('min_distance', 0):.6f} mm ({ae.get('min_distance', 0)*1000:.2f} μm)")
            report.append(f"  最大距离: {ae.get('max_distance', 0):.6f} mm ({ae.get('max_distance', 0)*1000:.2f} μm)")
            
            mean_dist_um = ae.get('mean_distance', 0) * 1000
            if mean_dist_um < 500:
                quality = "优秀"
                comment = "装配精度很高,满足高精度要求"
            elif mean_dist_um < 1000:
                quality = "良好"
                comment = "装配精度较好,满足一般精度要求"
            elif mean_dist_um < 2000:
                quality = "一般"
                comment = "装配精度一般,可能需要改进"
            else:
                quality = "较差"
                comment = "装配精度较低,需要改进工艺"
            
            report.append(f"  距离范围: {(ae.get('max_distance', 0)-ae.get('min_distance', 0))*1000:.2f} μm")
            report.append("")
            report.append(f"质量评价: {quality}")
            report.append(f"评价说明: {comment}")
            report.append("")
        
        # 五、圆度误差分析
        if 'roundness' in results:
            rnd = results['roundness']
            report.append("五、圆度误差分析")
            report.append("-" * 80)
            report.append("分析对象: 谐振陀螺的圆度误差")
            report.append("分析方法: 分层圆拟合,计算每层的圆度误差")
            report.append("执行标准: GB/T 7235-2004 产品几何量技术规范(GPS) 圆度测量")
            report.append("")
            report.append("统计结果:")
            report.append(f"  最大圆度误差: {rnd.get('max_error', 0):.2f} μm")
            report.append(f"  平均圆度误差: {rnd.get('mean_error', 0):.2f} μm")
            report.append("")
            
            mean_rnd = rnd.get('mean_error', 0)
            if mean_rnd < 500:
                rnd_quality = "优秀"
                rnd_comment = "圆度精度很高"
            elif mean_rnd < 1000:
                rnd_quality = "良好"
                rnd_comment = "圆度精度较好"
            elif mean_rnd < 2000:
                rnd_quality = "一般"
                rnd_comment = "圆度精度一般"
            else:
                rnd_quality = "较差"
                rnd_comment = "圆度精度较低"
            
            report.append(f"质量评价: {rnd_quality}")
            report.append(f"评价说明: {rnd_comment}")
            report.append("")
        
        # 六、球度误差分析
        if 'sphericity' in results:
            sph = results['sphericity']
            report.append("六、球度误差分析")
            report.append("-" * 80)
            report.append("分析对象: 谐振陀螺的球度误差")
            report.append("分析方法: 最小二乘球拟合,计算球度误差")
            report.append("执行标准: GB/T 24630-2009 产品几何量技术规范(GPS) 球度测量")
            report.append("")
            report.append("拟合结果:")
            center = sph.get('center', [0, 0, 0])
            report.append(f"  拟合球心坐标: [{center[0]:.6f}, {center[1]:.6f}, {center[2]:.6f}] mm")
            report.append(f"  拟合球半径: {sph.get('radius', 0):.6f} mm")
            report.append(f"  球度误差: {sph.get('error', 0):.2f} μm")
            report.append("")
            
            sph_err = sph.get('error', 0)
            if sph_err < 500:
                sph_quality = "优秀"
                sph_comment = "球度精度很高"
            elif sph_err < 1500:
                sph_quality = "良好"
                sph_comment = "球度精度较好"
            elif sph_err < 3000:
                sph_quality = "一般"
                sph_comment = "球度精度一般"
            else:
                sph_quality = "较差"
                sph_comment = "球度精度较低"
            
            report.append(f"质量评价: {sph_quality}")
            report.append(f"评价说明: {sph_comment}")
            report.append("")
        
        # 七、STL模型对比分析
        if 'stl_comparison' in results:
            stl = results['stl_comparison']
            report.append("七、STL模型对比分析")
            report.append("-" * 80)
            report.append(f"STL模型文件: {stl_file}")
            report.append(f"对齐策略: {stl.get('alignment_strategy', 'N/A')}")
            report.append(f"对齐误差: {stl.get('alignment_error', 0):.6f} mm")
            report.append("")
            
            stl_rnd = stl.get('stl_roundness', {})
            stl_sph = stl.get('stl_sphericity', {})
            
            report.append("STL模型几何误差:")
            report.append(f"  圆度误差: {stl_rnd.get('mean_error', 0):.2f} μm")
            report.append(f"  球度误差: {stl_sph.get('error', 0):.2f} μm")
            report.append(f"  拟合半径: {stl_sph.get('radius', 0):.6f} mm")
            report.append("")
            
            report.append("对比结果:")
            report.append(f"  圆度误差差异: {stl.get('roundness_diff', 0):.2f} μm")
            report.append(f"  球度误差差异: {stl.get('sphericity_diff', 0):.2f} μm")
            report.append(f"  半径差异: {stl.get('radius_diff', 0):.6f} mm")
            report.append("")
            
            sph_diff = stl.get('sphericity_diff', 0)
            if sph_diff < 100:
                cmp_quality = "优秀"
                cmp_comment = "实际加工与设计模型高度一致"
            elif sph_diff < 500:
                cmp_quality = "良好"
                cmp_comment = "实际加工与设计模型基本一致"
            else:
                cmp_quality = "需关注"
                cmp_comment = "实际加工与设计模型存在差异"
            
            report.append(f"对比评价: {cmp_quality}")
            report.append(f"评价说明: {cmp_comment}")
            report.append("")
        
        # 八、综合评价
        report.append("八、综合评价")
        report.append("-" * 80)
        report.append("")
        
        # 计算综合得分
        scores = []
        if 'assembly_error' in results:
            mean_dist_um = results['assembly_error'].get('mean_distance', 0) * 1000
            if mean_dist_um < 500:
                scores.append(100)
            elif mean_dist_um < 1000:
                scores.append(80)
            elif mean_dist_um < 2000:
                scores.append(60)
            else:
                scores.append(40)
        
        if 'roundness' in results:
            mean_rnd = results['roundness'].get('mean_error', 0)
            if mean_rnd < 500:
                scores.append(100)
            elif mean_rnd < 1000:
                scores.append(80)
            elif mean_rnd < 2000:
                scores.append(60)
            else:
                scores.append(40)
        
        if 'sphericity' in results:
            sph_err = results['sphericity'].get('error', 0)
            if sph_err < 500:
                scores.append(100)
            elif sph_err < 1500:
                scores.append(80)
            elif sph_err < 3000:
                scores.append(60)
            else:
                scores.append(40)
        
        if scores:
            overall_score = np.mean(scores)
            report.append(f"综合得分: {overall_score:.1f}/100")
            report.append("")
            
            if overall_score >= 90:
                overall_quality = "优秀"
                overall_comment = "各项指标均达到高精度要求,加工质量优秀"
            elif overall_score >= 70:
                overall_quality = "良好"
                overall_comment = "各项指标达到一般精度要求,加工质量良好"
            elif overall_score >= 50:
                overall_quality = "一般"
                overall_comment = "部分指标需要改进,加工质量一般"
            else:
                overall_quality = "较差"
                overall_comment = "多项指标不达标,需要改进加工工艺"
            
            report.append(f"综合评价: {overall_quality}")
            report.append(f"评价说明: {overall_comment}")
            report.append("")
            
            report.append("各项指标得分:")
            for i, score in enumerate(scores):
                if i == 0:
                    report.append(f"  装配误差: {score}/100")
                elif i == 1:
                    report.append(f"  圆度误差: {score}/100")
                elif i == 2:
                    report.append(f"  球度误差: {score}/100")
            report.append("")
        
        # 九、改进建议
        report.append("九、改进建议")
        report.append("-" * 80)
        report.append("")
        
        suggestions = []
        
        if 'assembly_error' in results:
            mean_dist_um = results['assembly_error'].get('mean_distance', 0) * 1000
            if mean_dist_um >= 1000:
                suggestions.append("1. 装配误差较大,建议:")
                suggestions.append("   - 检查装配工艺流程")
                suggestions.append("   - 提高装配定位精度")
                suggestions.append("   - 优化装配夹具设计")
                suggestions.append("")
        
        if 'roundness' in results:
            mean_rnd = results['roundness'].get('mean_error', 0)
            if mean_rnd >= 1000:
                suggestions.append("2. 圆度误差较大,建议:")
                suggestions.append("   - 检查加工设备精度")
                suggestions.append("   - 优化切削参数")
                suggestions.append("   - 提高刀具质量")
                suggestions.append("")
        
        if 'sphericity' in results:
            sph_err = results['sphericity'].get('error', 0)
            if sph_err >= 1500:
                suggestions.append("3. 球度误差较大,建议:")
                suggestions.append("   - 检查球面加工工艺")
                suggestions.append("   - 优化刀具路径")
                suggestions.append("   - 提高机床刚性")
                suggestions.append("")
        
        if not suggestions:
            suggestions.append("各项指标良好,建议:")
            suggestions.append("   - 保持当前加工工艺")
            suggestions.append("   - 定期检测设备精度")
            suggestions.append("   - 持续质量监控")
            suggestions.append("")
        
        report.extend(suggestions)
        
        # 结尾
        report.append("")
        report.append("=" * 80)
        report.append("报告结束")
        report.append("=" * 80)
        
        return '\n'.join(report)


# 主程序入口
if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    window = HRGCompleteAnalyzerGUIV3WithExport()
    window.show()

    sys.exit(app.exec_())
