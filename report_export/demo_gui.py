"""
GUI集成示例
展示如何在现有GUI中添加报告导出功能
"""

import sys
import os

# 添加路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QPushButton, QMessageBox, QFileDialog)
from PyQt5.QtCore import Qt

# 导入报告导出模块
from report_export.export_controller import ExportController
from report_export.models.export_request import ExportRequest
from report_export.models.export_result import ExportResult


class SimpleExportDemo(QMainWindow):
    """简单的导出演示窗口"""

    def __init__(self):
        super().__init__()
        self.initUI()

        # 模拟分析结果数据
        self.analysis_results = {
            'assembly_error': {
                'mean_distance': 0.523,
                'std_distance': 0.087,
                'min_distance': 0.356,
                'max_distance': 0.712
            },
            'roundness': {
                'max_error': 125.3,
                'mean_error': 68.7
            },
            'sphericity': {
                'center': [0.001, -0.002, 0.003],
                'radius': 15.234,
                'error': 187.5
            }
        }

    def initUI(self):
        """初始化UI"""
        self.setWindowTitle('HRG报告导出演示')
        self.setGeometry(100, 100, 400, 300)

        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 创建布局
        layout = QVBoxLayout()
        central_widget.setLayout(layout)

        # 添加标题
        from PyQt5.QtWidgets import QLabel
        title = QLabel('HRG报告导出功能演示')
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet('font-size: 16px; font-weight: bold; margin: 20px;')
        layout.addWidget(title)

        # 添加说明
        info = QLabel('点击下方按钮导出分析报告')
        info.setAlignment(Qt.AlignCenter)
        info.setStyleSheet('margin: 10px;')
        layout.addWidget(info)

        # 添加间距
        layout.addSpacing(20)

        # 添加导出PDF按钮
        self.export_pdf_btn = QPushButton('📄 导出PDF报告')
        self.export_pdf_btn.setStyleSheet('''
            QPushButton {
                background-color: #0173B2;
                color: white;
                border: none;
                padding: 10px;
                font-size: 14px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #015a8f;
            }
        ''')
        self.export_pdf_btn.clicked.connect(self.export_pdf)
        layout.addWidget(self.export_pdf_btn)

        # 添加导出Word按钮
        self.export_word_btn = QPushButton('📝 导出Word报告')
        self.export_word_btn.setStyleSheet('''
            QPushButton {
                background-color: #DE8F05;
                color: white;
                border: none;
                padding: 10px;
                font-size: 14px;
                border-radius: 5px;
                margin-top: 10px;
            }
            QPushButton:hover {
                background-color: #b87404;
            }
        ''')
        self.export_word_btn.clicked.connect(self.export_word)
        layout.addWidget(self.export_word_btn)

        # 添加批量导出按钮
        self.export_both_btn = QPushButton('📦 批量导出(PDF+Word)')
        self.export_both_btn.setStyleSheet('''
            QPushButton {
                background-color: #009988;
                color: white;
                border: none;
                padding: 10px;
                font-size: 14px;
                border-radius: 5px;
                margin-top: 10px;
            }
            QPushButton:hover {
                background-color: #007a6e;
            }
        ''')
        self.export_both_btn.clicked.connect(self.export_both)
        layout.addWidget(self.export_both_btn)

        # 添加状态标签
        layout.addSpacing(20)
        self.status_label = QLabel('准备就绪')
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet('color: gray;')
        layout.addWidget(self.status_label)

    def export_pdf(self):
        """导出PDF报告"""
        self.status_label.setText('正在导出PDF...')
        QApplication.processEvents()

        try:
            # 选择保存路径
            file_path, _ = QFileDialog.getSaveFileName(
                self, '保存PDF报告', 
                'output/reports/HRG分析报告.pdf',
                'PDF Files (*.pdf)'
            )

            if not file_path:
                self.status_label.setText('已取消')
                return

            # 创建导出请求
            request = ExportRequest(
                format_type='pdf',
                output_dir=os.path.dirname(file_path),
                analysis_data=self.analysis_results,
                filename_prefix=os.path.splitext(os.path.basename(file_path))[0],
                include_charts=True,
                language='zh'
            )

            # 创建导出控制器并执行导出
            controller = ExportController()
            result = controller.export_report(request)

            if result.success:
                QMessageBox.information(
                    self, '导出成功',
                    f'PDF报告已成功生成！\n\n'
                    f'文件路径:\n{result.file_paths[0]}\n\n'
                    f'文件大小: {result.file_sizes[0]/1024:.2f} KB\n'
                    f'导出耗时: {result.export_time:.2f} 秒'
                )
                self.status_label.setText('PDF导出成功')
            else:
                QMessageBox.warning(self, '导出失败', f'导出失败: {result.error_message}')
                self.status_label.setText('导出失败')

        except Exception as e:
            QMessageBox.critical(self, '错误', f'导出失败: {str(e)}')
            self.status_label.setText('导出失败')

    def export_word(self):
        """导出Word报告"""
        self.status_label.setText('正在导出Word...')
        QApplication.processEvents()

        try:
            # 选择保存路径
            file_path, _ = QFileDialog.getSaveFileName(
                self, '保存Word报告',
                'output/reports/HRG分析报告.docx',
                'Word Files (*.docx)'
            )

            if not file_path:
                self.status_label.setText('已取消')
                return

            # 创建导出请求
            request = ExportRequest(
                format_type='word',
                output_dir=os.path.dirname(file_path),
                analysis_data=self.analysis_results,
                filename_prefix=os.path.splitext(os.path.basename(file_path))[0],
                include_charts=True,
                language='zh'
            )

            # 创建导出控制器并执行导出
            controller = ExportController()
            result = controller.export_report(request)

            if result.success:
                QMessageBox.information(
                    self, '导出成功',
                    f'Word报告已成功生成！\n\n'
                    f'文件路径:\n{result.file_paths[0]}\n\n'
                    f'文件大小: {result.file_sizes[0]/1024:.2f} KB\n'
                    f'导出耗时: {result.export_time:.2f} 秒'
                )
                self.status_label.setText('Word导出成功')
            else:
                QMessageBox.warning(self, '导出失败', f'导出失败: {result.error_message}')
                self.status_label.setText('导出失败')

        except Exception as e:
            QMessageBox.critical(self, '错误', f'导出失败: {str(e)}')
            self.status_label.setText('导出失败')

    def export_both(self):
        """批量导出PDF和Word"""
        self.status_label.setText('正在批量导出...')
        QApplication.processEvents()

        try:
            # 选择保存目录
            dir_path = QFileDialog.getExistingDirectory(
                self, '选择保存目录',
                'output/reports'
            )

            if not dir_path:
                self.status_label.setText('已取消')
                return

            # 创建导出请求
            request = ExportRequest(
                format_type='both',
                output_dir=dir_path,
                analysis_data=self.analysis_results,
                filename_prefix='HRG分析报告',
                include_charts=True,
                language='zh'
            )

            # 创建导出控制器并执行导出
            controller = ExportController()
            result = controller.export_report(request)

            if result.success:
                msg = f'批量导出成功！\n\n生成文件:\n'
                for path, size in zip(result.file_paths, result.file_sizes):
                    msg += f'\n{os.path.basename(path)} ({size/1024:.2f} KB)'
                msg += f'\n\n总大小: {result.get_total_size_mb():.2f} MB'
                msg += f'\n导出耗时: {result.export_time:.2f} 秒'

                QMessageBox.information(self, '导出成功', msg)
                self.status_label.setText('批量导出成功')
            else:
                QMessageBox.warning(self, '导出失败', f'导出失败: {result.error_message}')
                self.status_label.setText('导出失败')

        except Exception as e:
            QMessageBox.critical(self, '错误', f'导出失败: {str(e)}')
            self.status_label.setText('导出失败')


def main():
    """主函数"""
    app = QApplication(sys.argv)
    
    # 设置应用样式
    app.setStyle('Fusion')
    
    # 创建并显示窗口
    window = SimpleExportDemo()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
