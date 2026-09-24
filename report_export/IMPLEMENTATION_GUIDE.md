# 报告导出功能完整实现指南

## 已完成的工作 ✅

### 阶段一：基础框架搭建

1. **目录结构** ✅
   - 创建了完整的模块目录结构
   - 所有`__init__.py`文件已创建

2. **数据模型** ✅
   - `models/export_request.py` - 导出请求封装
   - `models/export_result.py` - 导出结果封装
   - `models/analysis_data.py` - 分析数据模型
   - `models/export_config.py` - 导出配置

3. **工具函数** ✅
   - `utils/file_utils.py` - 文件操作工具
   - `utils/validation_utils.py` - 数据验证工具
   - `utils/chart_utils.py` - 图表转换工具

4. **文档** ✅
   - `README.md` - 使用说明文档

## 待实现的核心模块

由于代码量较大，以下是关键模块的实现要点和代码框架：

### 1. 可视化图表生成（visualization/）

#### chart_style_manager.py
```python
"""图表样式管理"""
from dataclasses import dataclass

@dataclass
class ChartStyleConfig:
    """图表样式配置"""
    font_family: str = 'SimHei'
    font_size_title: int = 14
    font_size_label: int = 12
    font_size_tick: int = 10
    color_primary: str = '#0173B2'
    color_secondary: str = '#DE8F05'
    colormap: str = 'RdYlGn_r'
    fig_width: float = 8
    fig_height: float = 6
    dpi: int = 300

def apply_style(figure, config: ChartStyleConfig):
    """应用样式到图表"""
    import matplotlib
    matplotlib.rcParams['font.family'] = config.font_family
    # ... 应用其他样式
```

#### point_cloud_charts.py
```python
"""点云分布图生成"""
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import numpy as np

class PointCloudChartGenerator:
    def generate_3d_scatter(self, points: np.ndarray):
        """生成3D散点图"""
        fig = plt.figure(figsize=(8, 6))
        ax = fig.add_subplot(111, projection='3d')

        ax.scatter(points[:, 0], points[:, 1], points[:, 2],
                   s=1, alpha=0.6, c='blue')

        ax.set_xlabel('X (mm)')
        ax.set_ylabel('Y (mm)')
        ax.set_zlabel('Z (mm)')
        ax.set_title('HRG点云三维分布')

        return fig

    def generate_analysis(self, points: np.ndarray, stats: dict) -> str:
        """生成分析说明"""
        # 返回包含四部分的分析说明文本
        analysis = f"""
【图表说明】
本图展示了HRG谐振陀螺点云的三维空间分布，共包含{len(points):,}个测量点。

【数据特征】
点云整体呈现球形形状，空间跨度为X={stats['x_span']:.2f}mm，Y={stats['y_span']:.2f}mm，Z={stats['z_span']:.2f}mm。
点云分布均匀，无明显缺失区域。

【问题诊断】
点云数据完整，无明显异常点或缺失区域。

【结论建议】
点云数据质量良好，可用于后续分析。
        """
        return analysis
```

### 2. PDF报告生成（generators/pdf_generator.py）

```python
"""PDF报告生成器"""
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

class PDFReportGenerator:
    def __init__(self):
        # 注册中文字体
        try:
            pdfmetrics.registerFont(TTFont('SimHei', 'SimHei.ttf'))
        except:
            print("警告: 未找到SimHei字体，使用默认字体")

    def generate(self, analysis_data: dict, output_path: str) -> bool:
        """生成PDF报告"""
        doc = SimpleDocTemplate(output_path, pagesize=A4)

        # 构建文档内容
        story = []

        # 添加标题
        story.append(Paragraph("HRG谐振陀螺分析报告", self.styles['Title']))
        story.append(Spacer(1, 12))

        # 添加章节
        story.append(Paragraph("一、基本信息", self.styles['Heading1']))
        # ... 添加内容

        # 添加图表
        # chart_image = Image(chart_path, width=400, height=300)
        # story.append(chart_image)

        # 生成PDF
        doc.build(story)
        return True
```

### 3. Word报告生成（generators/word_generator.py）

```python
"""Word报告生成器"""
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

class WordReportGenerator:
    def generate(self, analysis_data: dict, output_path: str) -> bool:
        """生成Word报告"""
        doc = Document()

        # 添加标题
        title = doc.add_heading('HRG谐振陀螺分析报告', 0)
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER

        # 添加章节
        doc.add_heading('一、基本信息', level=1)
        doc.add_paragraph('报告生成时间: ...')

        # 添加表格
        table = doc.add_table(rows=3, cols=2)
        table.cell(0, 0).text = '项目'
        table.cell(0, 1).text = '数值'

        # 添加图表
        # doc.add_picture(chart_path, width=Inches(6))

        # 保存文档
        doc.save(output_path)
        return True
```

### 4. 导出控制器（export_controller.py）

```python
"""导出控制器 - 主入口"""
import time
from typing import Optional
from .models.export_request import ExportRequest
from .models.export_result import ExportResult
from .utils.file_utils import ensure_dir, get_unique_filename, safe_write_file
from .utils.validation_utils import validate_analysis_data, check_dependencies

class ExportController:
    """报告导出控制器"""

    def __init__(self):
        # 检查依赖
        self.deps_ok, self.missing_deps = check_dependencies()

    def export_report(self, request: ExportRequest) -> ExportResult:
        """执行报告导出"""
        start_time = time.time()

        try:
            # 1. 验证请求
            is_valid, error = request.validate()
            if not is_valid:
                return ExportResult.create_failure(error)

            # 2. 验证数据
            is_valid, error = validate_analysis_data(request.analysis_data)
            if not is_valid:
                return ExportResult.create_failure(error)

            # 3. 确保输出目录存在
            if not ensure_dir(request.output_dir):
                return ExportResult.create_failure("无法创建输出目录")

            # 4. 生成报告
            file_paths = []
            file_sizes = []

            for ext in request.get_file_extensions():
                # 生成文件名
                filename = f"{request.filename_prefix}_{request.get_timestamp_str()}"
                filepath = get_unique_filename(request.output_dir, filename, ext)

                # 根据扩展名选择生成器
                if ext == '.pdf':
                    success = self._generate_pdf(request.analysis_data, filepath)
                elif ext == '.docx':
                    success = self._generate_word(request.analysis_data, filepath)

                if success:
                    file_paths.append(filepath)
                    file_sizes.append(os.path.getsize(filepath))

            # 5. 返回结果
            export_time = time.time() - start_time
            return ExportResult.create_success(file_paths, file_sizes, export_time)

        except Exception as e:
            export_time = time.time() - start_time
            return ExportResult.create_failure(str(e), export_time)

    def _generate_pdf(self, data: dict, filepath: str) -> bool:
        """生成PDF报告"""
        from .generators.pdf_generator import PDFReportGenerator
        generator = PDFReportGenerator()
        return generator.generate(data, filepath)

    def _generate_word(self, data: dict, filepath: str) -> bool:
        """生成Word报告"""
        from .generators.word_generator import WordReportGenerator
        generator = WordReportGenerator()
        return generator.generate(data, filepath)

    def get_supported_formats(self) -> list:
        """获取支持的格式"""
        return ['pdf', 'word', 'both']
```

## 实现步骤建议

### 步骤1：实现可视化模块
1. 实现`chart_style_manager.py` - 样式配置
2. 实现`point_cloud_charts.py` - 点云图
3. 实现`error_distribution_charts.py` - 误差图
4. 实现`radar_chart.py` - 雷达图
5. 实现`chart_analyzer.py` - 分析说明生成

### 步骤2：实现报告生成器
1. 实现`pdf_generator.py` - PDF生成
2. 实现`word_generator.py` - Word生成
3. 实现内容构建器

### 步骤3：实现导出控制器
1. 实现`export_controller.py` - 主控制器
2. 实现模板管理器

### 步骤4：GUI集成
1. 在GUI中添加导出按钮
2. 实现导出事件处理
3. 实现进度显示

### 步骤5：测试验证
1. 单元测试
2. 集成测试
3. 回归测试（确保不影响现有功能）

## 关键注意事项

1. **不影响现有功能**
   - 所有代码在独立目录
   - 不修改现有代码
   - 独立输出目录

2. **依赖管理**
   - 优雅降级：依赖未安装时提示用户
   - 不影响现有依赖版本

3. **错误处理**
   - 完善的异常捕获
   - 友好的错误提示
   - 资源清理

4. **性能优化**
   - 图表生成优化
   - 文件写入优化
   - 内存管理

## 测试清单

- [ ] 数据模型测试
- [ ] 工具函数测试
- [ ] 图表生成测试
- [ ] PDF生成测试
- [ ] Word生成测试
- [ ] 导出控制器测试
- [ ] GUI集成测试
- [ ] 回归测试（现有功能）

## 估计工作量

- 可视化模块：2-3天
- PDF生成：1-2天
- Word生成：1-2天
- 导出控制器：1天
- GUI集成：1天
- 测试优化：1-2天

**总计：7-11天**

## 下一步行动

建议按以下顺序实现：

1. 先实现可视化图表生成（核心功能）
2. 实现PDF生成器（主要输出格式）
3. 实现Word生成器（次要输出格式）
4. 实现导出控制器（统一入口）
5. GUI集成（用户界面）
6. 测试验证（质量保证）

每个模块实现后立即进行单元测试，确保功能正确。
