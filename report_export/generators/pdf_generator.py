"""
PDF报告生成器
生成符合国标的PDF格式分析报告
"""

import os
import time
from datetime import datetime
from typing import Dict, Any, Optional

from reportlab.lib.pagesizes import A4
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, 
                                 Table, TableStyle, Image, PageBreak)
from reportlab.lib.units import mm
from reportlab.lib import colors

from templates.pdf_template import PDFTemplate
from utils.chart_utils import figure_to_image


class PDFReportGenerator:
    """PDF报告生成器"""

    def __init__(self):
        """初始化PDF生成器"""
        self.template = PDFTemplate()

    def generate(self, analysis_data: Dict[str, Any], output_path: str) -> bool:
        """
        生成PDF报告

        Args:
            analysis_data: 分析结果数据
            output_path: 输出文件路径

        Returns:
            bool: 是否成功
        """
        try:
            # 创建PDF文档
            doc = SimpleDocTemplate(
                output_path,
                **self.template.get_page_settings()
            )

            # 构建文档内容
            story = []

            # 1. 添加标题
            story.extend(self._add_title())

            # 2. 添加基本信息
            story.extend(self._add_basic_info(analysis_data))

            # 3. 添加分析结果
            story.extend(self._add_analysis_results(analysis_data))

            # 4. 添加综合评价
            story.extend(self._add_evaluation(analysis_data))

            # 生成PDF
            doc.build(story)

            return True

        except Exception as e:
            print(f"PDF生成失败: {e}")
            return False

    def _add_title(self):
        """添加标题"""
        story = []

        # 主标题
        title = Paragraph(
            "HRG谐振陀螺分析报告",
            self.template.styles['ChineseTitle']
        )
        story.append(title)
        story.append(Spacer(1, 10 * mm))

        return story

    def _add_basic_info(self, data: Dict[str, Any]):
        """添加基本信息"""
        story = []

        # 章节标题
        story.append(Paragraph(
            "一、基本信息",
            self.template.styles['ChineseHeading1']
        ))

        # 信息表格
        info_data = [
            ['项目', '内容'],
            ['报告生成时间', datetime.now().strftime('%Y-%m-%d %H:%M:%S')],
            ['分析软件版本', 'v3.0'],
            ['执行标准', 'GB/T 24630.1-2024, GB/T 7235-2004, GB/T 3505-2009, GB/T 6062-2009'],
        ]

        table = Table(info_data, colWidths=[60 * mm, 100 * mm])
        table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), self.template.chinese_font),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BACKGROUND', (0, 0), (-1, 0), self.template.colors['primary']),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, self.template.colors['light_gray']]),
        ]))

        story.append(table)
        story.append(Spacer(1, 10 * mm))

        return story

    def _add_analysis_results(self, data: Dict[str, Any]):
        """添加分析结果"""
        story = []

        # 装配误差分析
        if 'assembly_error' in data:
            story.extend(self._add_assembly_error(data['assembly_error']))

        # 圆度误差分析
        if 'roundness' in data:
            story.extend(self._add_roundness(data['roundness']))

        # 球度误差分析
        if 'sphericity' in data:
            story.extend(self._add_sphericity(data['sphericity']))

        return story

    def _add_assembly_error(self, data: Dict[str, Any]):
        """添加装配误差分析"""
        story = []

        story.append(Paragraph(
            "二、装配误差分析",
            self.template.styles['ChineseHeading1']
        ))

        # 数据表格
        table_data = [
            ['指标', '数值'],
            ['平均距离', f"{data.get('mean_distance', 0):.6f} mm ({data.get('mean_distance', 0)*1000:.2f} μm)"],
            ['标准差', f"{data.get('std_distance', 0):.6f} mm ({data.get('std_distance', 0)*1000:.2f} μm)"],
            ['最小距离', f"{data.get('min_distance', 0):.6f} mm ({data.get('min_distance', 0)*1000:.2f} μm)"],
            ['最大距离', f"{data.get('max_distance', 0):.6f} mm ({data.get('max_distance', 0)*1000:.2f} μm)"],
        ]

        table = Table(table_data, colWidths=[60 * mm, 100 * mm])
        table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), self.template.chinese_font),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BACKGROUND', (0, 0), (-1, 0), self.template.colors['primary']),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ]))

        story.append(table)
        story.append(Spacer(1, 10 * mm))

        return story

    def _add_roundness(self, data: Dict[str, Any]):
        """添加圆度误差分析"""
        story = []

        story.append(Paragraph(
            "三、圆度误差分析",
            self.template.styles['ChineseHeading1']
        ))

        table_data = [
            ['指标', '数值'],
            ['最大圆度误差', f"{data.get('max_error', 0):.2f} μm"],
            ['平均圆度误差', f"{data.get('mean_error', 0):.2f} μm"],
        ]

        table = Table(table_data, colWidths=[60 * mm, 100 * mm])
        table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), self.template.chinese_font),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BACKGROUND', (0, 0), (-1, 0), self.template.colors['primary']),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ]))

        story.append(table)
        story.append(Spacer(1, 10 * mm))

        return story

    def _add_sphericity(self, data: Dict[str, Any]):
        """添加球度误差分析"""
        story = []

        story.append(Paragraph(
            "四、球度误差分析",
            self.template.styles['ChineseHeading1']
        ))

        center = data.get('center', [0, 0, 0])
        table_data = [
            ['指标', '数值'],
            ['拟合球心', f"({center[0]:.6f}, {center[1]:.6f}, {center[2]:.6f}) mm"],
            ['拟合半径', f"{data.get('radius', 0):.6f} mm"],
            ['球度误差', f"{data.get('error', 0):.2f} μm"],
        ]

        table = Table(table_data, colWidths=[60 * mm, 100 * mm])
        table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), self.template.chinese_font),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BACKGROUND', (0, 0), (-1, 0), self.template.colors['primary']),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ]))

        story.append(table)
        story.append(Spacer(1, 10 * mm))

        return story

    def _add_evaluation(self, data: Dict[str, Any]):
        """添加综合评价"""
        story = []

        story.append(Paragraph(
            "五、综合评价",
            self.template.styles['ChineseHeading1']
        ))

        # 简单的评价文本
        eval_text = """
        本报告基于HRG点云分析结果生成，包含装配误差、圆度误差、球度误差等关键指标。
        分析过程符合国家标准GB/T 24630.1-2024、GB/T 7235-2004、GB/T 3505-2009和GB/T 6062-2009的要求。
        """

        story.append(Paragraph(eval_text, self.template.styles['ChineseBody']))
        story.append(Spacer(1, 10 * mm))

        return story
