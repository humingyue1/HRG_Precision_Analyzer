"""生成HRG技术点说明Word文档"""
from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT

doc = Document()

style = doc.styles['Normal']
style.font.name = '宋体'
style.font.size = Pt(11)
style.paragraph_format.line_spacing = 1.5

def add_title(text, level=1):
    h = doc.add_heading(text, level=level)
    for run in h.runs:
        run.font.color.rgb = RGBColor(0, 51, 102)

def add_para(text, bold=False):
    p = doc.add_paragraph()
    run = p.add_run(text)
    run.bold = bold
    return p

def add_table(headers, rows):
    table = doc.add_table(rows=1+len(rows), cols=len(headers), style='Light Grid Accent 1')
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, h in enumerate(headers):
        cell = table.rows[0].cells[i]
        cell.text = h
        for p in cell.paragraphs:
            for r in p.runs:
                r.bold = True
                r.font.size = Pt(10)
    for ri, row in enumerate(rows):
        for ci, val in enumerate(row):
            cell = table.rows[ri+1].cells[ci]
            cell.text = str(val)
            for p in cell.paragraphs:
                for r in p.runs:
                    r.font.size = Pt(10)
    return table

# ===== 封面 =====
doc.add_paragraph('\n\n\n')
t = doc.add_paragraph()
t.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = t.add_run('HRG半球谐振陀螺加工精度分析系统\n技术点全面说明文档')
r.bold = True
r.font.size = Pt(22)
r.font.color.rgb = RGBColor(0, 51, 102)

doc.add_paragraph('\n')
t2 = doc.add_paragraph()
t2.alignment = WD_ALIGN_PARAGRAPH.CENTER
r2 = t2.add_run('版本: v4.0 | 文档日期: 2026-05-14')
r2.font.size = Pt(12)
r2.font.color.rgb = RGBColor(100, 100, 100)

doc.add_page_break()

# ===== 目录概览 =====
add_title('一、文档概述')
add_para('本文档全面提取HRG半球谐振陀螺加工精度分析系统中所有可用于论文的技术点、算法、数学模型、国家标准引用及实现方法。涵盖9大分析模块、4项国标体系、20+核心算法。')

add_title('二、国家标准体系总览')
add_table(
    ['标准编号', '标准名称', '应用模块', '关键参数'],
    [
        ['GB/T 3505-2009', '产品几何量技术规范(GPS) 表面结构 轮廓法', '表面粗糙度、波纹度', 'Ra, Rq, Rz, RSm, λc, λf'],
        ['GB/T 6062-2009', '产品几何量技术规范(GPS) 表面结构 轮廓法 接触(触针)式仪器的标称特性', '轮廓滤波、粗糙度', 'λs, λc, 针尖半径, 采样间距'],
        ['GB/T 18777-2002', '产品几何量技术规范(GPS) 表面结构 轮廓法 相位修正滤波器的计量特性', '高斯滤波器', '截止波长传输率50%, 高斯核函数'],
        ['GB/T 24630.1-2024', '产品几何量技术规范(GPS) 平面度 第1部分: 词汇和参数', '平面度分析', 'FLTt, FLTp, FLTv, FLTq'],
        ['GB/T 24630.2-2024', '产品几何量技术规范(GPS) 平面度 第2部分: 规范操作集', '平面度分析', 'LSPL, MZPL参考平面'],
        ['GB/T 7235-2004', '产品几何量技术规范(GPS) 圆度测量 术语定义及参数', '圆度完整评定', 'MZC, LSC, MCC, MLC, upr'],
    ]
)

doc.add_page_break()

# ===== 表面粗糙度 =====
add_title('三、表面粗糙度分析 (GB/T 3505-2009)')

add_title('3.1 轮廓算术平均偏差 Ra', level=2)
add_para('标准条款: GB/T 3505-2009 第4.2.1条')
add_para('数学公式: Ra = (1/l) × ∫₀ˡ|Z(x)|dx')
add_para('实现方法: 对粗糙度轮廓沿取样长度进行数值积分(np.trapz)，单位转换mm→μm(×1000)')
add_para('关键参数: 取样长度lr = λc = 0.8mm, 评定长度ln = 5×lr = 4.0mm')

add_title('3.2 轮廓均方根偏差 Rq', level=2)
add_para('标准条款: GB/T 3505-2009 第4.2.2条')
add_para('数学公式: Rq = √[(1/l) × ∫₀ˡZ²(x)dx]')
add_para('实现方法: 对Z²(x)进行数值积分后开方')

add_title('3.3 轮廓最大高度 Rz', level=2)
add_para('标准条款: GB/T 3505-2009 第4.1.3条')
add_para('数学公式: Rz = Rp + Rv，其中Rp为最大轮廓峰高，Rv为最大轮廓谷深')
add_para('重要说明: GB/T 3505-1983中Rz曾表示"十点高度"，2009版已修正为"轮廓最大高度"')
add_para('聚合规则: 多取样长度时Rz = max(Rz₁, Rz₂, ..., Rzₙ)')

add_title('3.4 轮廓单元平均宽度 RSm', level=2)
add_para('标准条款: GB/T 3505-2009 第4.3.1条')
add_para('数学公式: RSm = (1/m) × ∑Xsᵢ，Xsᵢ为轮廓单元宽度(峰+谷组合)')
add_para('分辨力判据(GB/T 3505-2009 第4.3.1注):')
add_para('  - 高度分辨力: 默认10%×Rz')
add_para('  - 水平间距分辨力: 默认1%×lr')
add_para('实现方法: 检测轮廓与中线的零交叉点，按分辨力判据筛选有效轮廓单元')

add_title('3.5 λs/λc双级高斯滤波器', level=2)
add_para('标准条款: GB/T 6062-2009 第3.1.4条/3.1.6条, GB/T 18777-2002')
add_para('滤波流程: 原始信号 → λs滤波器(抑制短波噪声) → λc滤波器(抑制长波成分) → 粗糙度轮廓 = λs输出 - λc长波成分')
add_para('传输频带: λs ~ λc，截止波长处传输率50% (GB/T 18777-2002)')
add_para('高斯核函数: G(x) = exp(-x²/(2σ²))，其中σ = λ/(2π)')
add_para('实现方法: FFT频域卷积，O(N log N)复杂度')
add_para('参数约束: λc/λs比例应在{100, 300}附近，默认λs=0.0025mm, λc=0.8mm')

add_title('3.6 3D点云到2D轮廓提取', level=2)
add_para('方法: 径向轮廓提取——r = √(x²+y²), z保留，按r排序后重采样至均匀间隔(10000点)')
add_para('重采样: 线性插值 np.interp，等间距化')

doc.add_page_break()

# ===== 波纹度 =====
add_title('四、波纹度分析 (GB/T 3505-2009 第3.1.7条)')

add_title('4.1 标称形状去除', level=2)
add_para('标准条款: GB/T 3505-2009 第3.1.7注1')
add_para('方法: 在用λf滤波器分离波纹度轮廓以前，应首先用最小二乘法的最佳拟合从总轮廓中提取标称形状，并将形状成分从总轮廓中去除')
add_para('实现: A = [x, 1]，y_nominal = A×coeffs (lstsq求解)，残差 = y - y_nominal')

add_title('4.2 λf/λc两级滤波分离波纹度', level=2)
add_para('滤波流程: 去除标称形状 → λf低通(抑制长波) → λc低通(抑制短波) → 波纹度 = λf输出 - λc输出')
add_para('传输频带: λc ~ λf，默认λc=2.5mm, λf=8.0mm')
add_para('波纹度幅值: W = (max(y) - min(y)) / 2，单位μm')

doc.add_page_break()

# ===== 平面度 =====
add_title('五、平面度分析 (GB/T 24630.1-2024 / GB/T 24630.2-2024)')

add_title('5.1 最小二乘参考平面 (LSPL)', level=2)
add_para('方法: 基于SVD的平面拟合法')
add_para('算法: 质心化点云 → SVD分解 → 最小奇异值对应的右奇异向量为法向量')
add_para('SVD: centered = U×S×Vᵀ (full_matrices=False)，normal = Vt[2]')
add_para('偏差计算: dᵢ = (pᵢ - center) · normal')

add_title('5.2 最小区域参考平面 (MZPL)', level=2)
add_para('标准: GB/T 24630.2-2024 规范操作集')
add_para('方法: 旋转搜索法 + Nelder-Mead单纯形优化')
add_para('参数化法向量: n = (sinφ·cosθ, sinφ·sinθ, cosφ)')
add_para('目标函数: min[max(d) - min(d)]，使峰-谷值最小')
add_para('初始值: 由LSPL法向量转换得到(θ₀, φ₀)')

add_title('5.3 平面度参数', level=2)
add_table(
    ['参数符号', '参数名称', '计算方法', '参考平面'],
    [
        ['FLTt', '峰-谷平面度偏差', 'max(d) - min(d)', 'LSPL / MZPL'],
        ['FLTp', '峰值平面度偏差', 'max(d)', 'LSPL'],
        ['FLTv', '谷值平面度偏差', '-min(d)', 'LSPL'],
        ['FLTq', '均方根平面度偏差', '√(mean(d²))', 'LSPL'],
    ]
)

doc.add_page_break()

# ===== 圆度 =====
add_title('六、圆度完整评定 (GB/T 7235-2004)')

add_title('6.1 最小二乘圆 (LSC)', level=2)
add_para('方法: 代数拟合——展开(x-a)²+(y-b)²=R² → x²+y²-2ax-2by+(a²+b²-R²)=0')
add_para('求解: A=[x, y, 1], b=-(x²+y²), lstsq求解 → 圆心(a/2, b/2), 半径R=√(a²+b²-c)')
add_para('圆度误差: Δ = max(devs) - min(devs)')

add_title('6.2 最小区域圆 (MZC)', level=2)
add_para('方法: Nelder-Mead优化，最小化max(dists)-min(dists)')
add_para('半径: R = (max(dists) + min(dists)) / 2')

add_title('6.3 最小外接圆 (MCC)', level=2)
add_para('方法: 优化使外接半径R最小，同时内接半径r最大')
add_para('目标: min(R - r)，其中R = max(dists), r = min(dists)')

add_title('6.4 最大内接圆 (MLC)', level=2)
add_para('方法: 优化使内接半径r最大，同时外接半径R最小')
add_para('目标: min(R - r)')

add_title('6.5 upr滤波器', level=2)
add_para('标准: GB/T 7235-2004 波数/转(undulations per revolution)')
add_para('方法: FFT频域滤波，保留[upr_min, upr_max]范围内的频率分量')
add_para('默认范围: 1-50 upr，可选: 1-15, 1-150, 1-500, 1-1500')

doc.add_page_break()

# ===== 轮廓滤波 =====
add_title('七、轮廓滤波分析 (GB/T 6062-2009)')

add_title('7.1 高斯相位修正滤波器', level=2)
add_para('标准: GB/T 18777-2002 / ISO 11562')
add_para('核函数: G(x) = exp(-x²/(2σ²)) / ∫G(x)dx，σ = λ/(2π)')
add_para('实现: FFT频域卷积')

add_title('7.2 截止波长标称值系列 (GB/T 6062-2009 表1)', level=2)
add_table(
    ['λc (mm)', 'λs (mm)', 'λc/λs比', '最大针尖半径rtp (μm)', '最大采样间距 (mm)'],
    [
        ['0.08', '0.0025', '30', '2', '0.0005'],
        ['0.25', '0.0025', '100', '2', '0.0005'],
        ['0.8', '0.0025', '300', '2', '0.0005'],
        ['2.5', '0.008', '300', '5', '0.0015'],
        ['8.0', '0.025', '300', '10', '0.005'],
    ]
)

add_title('7.3 三级轮廓分离', level=2)
add_para('流程: 原始轮廓 → λs滤波(短波抑制) → λc滤波(粗糙度/波纹度分离)')
add_para('结果: 粗糙度轮廓 = λs输出 - λc输出；波纹度轮廓 = λc输出')

doc.add_page_break()

# ===== 对称性 =====
add_title('八、对称性分析')

add_title('8.1 n阶旋转对称性误差', level=2)
add_para('方法: 将点云转换到极坐标(r, θ, z)，对每个点旋转2π/n角度后查找最近邻')
add_para('对称轴查找: PCA主成分分析——最小特征值对应的特征向量为旋转对称轴')
add_para('旋转实现: Rodrigues旋转公式——R = I + sin(θ)·K + (1-cos(θ))·K²')
add_para('误差计算: 最近邻Z值差异的均值，归一化到[0,1]范围')
add_para('默认阶数: 2, 4, 6, 8阶')

add_title('8.2 极坐标变换', level=2)
add_para('步骤: 1) PCA找对称轴 2) Rodrigues旋转对齐Z轴 3) 转极坐标 r=√(x²+y²), θ=atan2(y,x)')

doc.add_page_break()

# ===== 壁厚 =====
add_title('九、壁厚分析')

add_title('9.1 内外表面分离', level=2)
add_para('方法: 按半径中位数分界——r < median(r)为内表面, r ≥ median(r)为外表面')

add_title('9.2 局部壁厚计算', level=2)
add_para('方法: KDTree最近邻搜索——对外表面每个点在内表面KDTree中查找最近点，距离即为局部壁厚')
add_para('数据结构: scipy.spatial.cKDTree (C实现，高性能)')

add_title('9.3 壁厚均匀性', level=2)
add_para('公式: uniformity = σ(厚度) / μ(厚度)')
add_para('统计量: mean, std, min, max, 壁厚分布彩色云图(jet色图)')

doc.add_page_break()

# ===== 谐振参数 =====
add_title('十、谐振参数分析')

add_title('10.1 质量分布均匀性', level=2)
add_para('方法: 将空间划分为36个扇形区域(每10°)，统计各扇形点数(质量估计)')
add_para('公式: uniformity = 1 - σ(扇形质量) / μ(扇形质量)，范围[0,1]')

add_title('10.2 惯性张量计算', level=2)
add_para('公式: Ixx = Σmᵢ(yᵢ²+zᵢ²), Iyy = Σmᵢ(xᵢ²+zᵢ²), Izz = Σmᵢ(xᵢ²+yᵢ²)')
add_para('惯量积: Ixy = -Σmᵢ·xᵢ·yᵢ, Ixz = -Σmᵢ·xᵢ·zᵢ, Iyz = -Σmᵢ·yᵢ·zᵢ')
add_para('质量估计: 包围盒体积×10%×密度(7850 kg/m³)')

add_title('10.3 谐振频率偏移估计', level=2)
add_para('方法: 对惯性张量进行特征值分解，频率偏移 ∝ 惯性主轴差异 × (1-质量均匀性)')
add_para('公式: Δf = σ(λ_normalized) × (1 - mass_uniformity)')

doc.add_page_break()

# ===== 质量评价 =====
add_title('十一、质量评价')

add_title('11.1 多指标加权评分', level=2)
add_table(
    ['指标', '默认权重', '评分依据', '阈值(优/良/中)'],
    [
        ['表面粗糙度', '0.25', 'Ra值', 'Ra≤0.4 / 0.8 / 1.6 μm'],
        ['对称性', '0.25', '最小对称性误差', '≤0.01 / 0.02 / 0.05'],
        ['壁厚均匀性', '0.20', '不均匀度', '≤0.02 / 0.05 / 0.10'],
        ['波纹度', '0.15', '波纹度幅值', '≤1.0 / 2.0 / 5.0 μm'],
        ['谐振参数', '0.15', '质量分布均匀性', '直接映射×100'],
    ]
)

add_title('11.2 分段线性插值评分', level=2)
add_para('方法: 在优/良/中阈值之间进行线性插值，超出中等阈值后线性衰减')
add_para('综合评分: S = Σ(wᵢ × sᵢ) / Σwᵢ (归一化加权平均)')

add_title('11.3 质量等级', level=2)
add_para('优: ≥90分, 良: ≥75分, 中: ≥60分, 差: <60分')

add_title('11.4 改进建议生成', level=2)
add_para('方法: 找出最低得分指标(低于60分)，根据指标类型给出针对性建议')

doc.add_page_break()

# ===== 高级算法 =====
add_title('十二、高级几何评定算法')

add_title('12.1 改进Kasa代数球拟合', level=2)
add_para('标准: GB/T 7235-2004 圆度测量, GB/T 24630-2009 球度测量')
add_para('改进: 坐标平移到质心提高数值稳定性，SVD求解代替最小二乘')
add_para('设计矩阵: A = [x, y, z, 1], b = x²+y²+z²')
add_para('SVD求解: params = Vᵀ·diag(1/S)·Uᵀ·b')

add_title('12.2 圆心搜索算法(变步长策略)', level=2)
add_para('方法: 在LSC圆心附近以变步长搜索MZC/MCC/MLC圆心')

add_title('12.3 Gauss-Newton迭代优化', level=2)
add_para('应用: 圆度和球度的高精度迭代优化')

add_title('12.4 最小区域法评定', level=2)
add_para('标准: GB/T 7235-2004 最小区域圆/球评定')

doc.add_page_break()

# ===== 点云对齐 =====
add_title('十三、点云对齐与配准')

add_title('13.1 最佳刚体变换(SVD)', level=2)
add_para('算法: 计算两组点云的质心 → 中心化 → 协方差矩阵H = Aᵀ·B → SVD分解H = UΣVᵀ → R = V·Uᵀ → t = centroid_B - R·centroid_A')
add_para('反射处理: 若det(R)<0，修正Vᵀ最后一行取反')

add_title('13.2 ICP算法(迭代最近点)', level=2)
add_para('算法: 构建KDTree → 迭代: 查找最近点对 → 计算最佳刚体变换 → 应用变换 → 判断收敛')
add_para('参数: max_iterations=50, tolerance=1e-6')
add_para('数据结构: scipy.spatial.cKDTree 加速最近邻查询')

add_title('13.3 多策略对齐', level=2)
add_para('方法: 尝试多种对齐策略(PCA初始对齐 + ICP精配准)，选择误差最小的策略')

doc.add_page_break()

# ===== VTK 3D可视化 =====
add_title('十四、VTK三维点云可视化')

add_title('14.1 VTK渲染管线', level=2)
add_para('完整管线: numpy N×3 → vtkPoints + vtkCellArray → vtkPolyData → vtkGlyph3D(球体化) → vtkPolyDataMapper → vtkActor → vtkRenderer → QVTKRenderWindowInteractor')
add_para('球体化: vtkSphereSource(低分辨率6×6) + vtkGlyph3D，每个点渲染为小球')
add_para('交互: vtkInteractorStyleTrackballCamera(左键旋转、右键缩放、中键平移)')

add_title('14.2 坐标轴指示器', level=2)
add_para('实现: vtkAxesActor + vtkOrientationMarkerWidget(右下角显示XYZ方向)')

add_title('14.3 降采样与NaN过滤', level=2)
add_para('NaN/Inf过滤: mask = np.isfinite(points).all(axis=1)')
add_para('降采样: 超过10000点时随机采样(np.random.choice)')

add_title('14.4 截图导出', level=2)
add_para('方法: vtkWindowToImageFilter → vtk_to_numpy → reshape(H,W,3) → np.flipud(翻转)')

doc.add_page_break()

# ===== 基础算法 =====
add_title('十五、基础算法与数据结构')

add_title('15.1 主成分分析 (PCA)', level=2)
add_para('方法: 点云归一化(平移到质心) → 协方差矩阵 → 特征值分解(np.linalg.eigh) → 按特征值降序排列')
add_para('应用: 对称轴查找、法向量估计、点云主方向确定')

add_title('15.2 KDTree空间索引', level=2)
add_para('实现: scipy.spatial.cKDTree (Cython加速)')
add_para('应用: 最近邻查询(壁厚计算、对称性误差、ICP配准)')

add_title('15.3 Rodrigues旋转公式', level=2)
add_para('公式: R = I + sin(θ)·K + (1-cos(θ))·K²')
add_para('K为旋转轴的反对称矩阵: K = [[0,-kz,ky],[kz,0,-kx],[-ky,kx,0]]')

add_title('15.4 FFT频域卷积', level=2)
add_para('方法: y_filtered = IFFT(FFT(y) × FFT(kernel))')
add_para('优势: O(N log N)复杂度，比直接卷积O(N²)快数量级')
add_para('应用: 高斯滤波器(粗糙度/波纹度/轮廓滤波)')

add_title('15.5 SVD奇异值分解', level=2)
add_para('应用: 平面拟合(LSPL法向量)、最佳刚体变换(ICP)、改进Kasa球拟合')
add_para('优化: 使用full_matrices=False避免巨大矩阵(如229099×229099)')

doc.add_page_break()

# ===== 系统架构 =====
add_title('十六、系统架构与软件工程')

add_title('16.1 统一分析流程', level=2)
add_table(
    ['步骤编号', '分析步骤', '模块', '可选/必选'],
    [
        ['1', '加载ASC文件', 'complete_pipeline', '必选'],
        ['2', '分割点云', 'hrg_special_analyzer', '必选'],
        ['3', '分析装配误差', 'hrg_special_analyzer', '必选'],
        ['4', '清理谐振陀螺点云', '阈值过滤', '必选'],
        ['5', '分析几何误差(圆度+球度)', 'hrg_special_analyzer', '必选'],
        ['6', '与STL模型对比', 'advanced_alignment+ICP', '可选(需STL)'],
        ['7', '表面粗糙度分析', 'roughness_analyzer', '可选(复选框)'],
        ['8', '波纹度分析', 'waviness_analyzer', '可选(复选框)'],
        ['9', '对称性分析', 'symmetry_analyzer', '可选(复选框)'],
        ['10', '壁厚分析', 'thickness_analyzer', '可选(复选框)'],
        ['11', '谐振参数分析', 'resonance_analyzer', '可选(复选框)'],
        ['12', '平面度分析', 'flatness_analyzer', '可选(复选框)'],
        ['13', '圆度完整评定', 'roundness_full_analyzer', '可选(复选框)'],
        ['14', '轮廓滤波分析', 'profile_filter_analyzer', '可选(复选框)'],
        ['15', '质量评价', 'quality_evaluator', '可选(复选框)'],
    ]
)

add_title('16.2 声明式步骤注册表', level=2)
add_para('实现: StepDef数据类——step_id, step_name, is_v3, optional, enabled_check, execute_fn')
add_para('动态计算: 根据复选框状态和STL文件存在性自动计算实际步骤数和编号')

add_title('16.3 多线程分析', level=2)
add_para('实现: QThread + pyqtSignal信号槽机制')
add_para('信号: progress_updated(int, str), log_message(str), visualization_ready(ndarray, str), comparison_ready(ndarray, ndarray, str, str), analysis_finished(dict), error_occurred(str)')

add_title('16.4 降级容错机制', level=2)
add_para('VTK降级: try/except import vtk → VTK_AVAILABLE标志 → 不可用时使用matplotlib 3D scatter')
add_para('步骤容错: v3核心步骤失败终止流程，v4精度步骤失败记录并继续')

add_title('16.5 导出报告格式', level=2)
add_para('Word: python-docx生成.docx，支持中文字体(SimSun/SimHei)')
add_para('PDF: reportlab生成.pdf，支持中文字体注册')
add_para('TXT: 纯文本写入')
add_para('JSON: 精度分析结果序列化')

doc.add_page_break()

# ===== 论文写作建议 =====
add_title('十七、论文写作建议')

add_title('17.1 方法论章节建议结构', level=2)
add_para('1) 点云数据采集与预处理(ASC文件解析、采样、去虚影)')
add_para('2) 表面形貌评定体系(Ra/Rq/Rz/RSm参数 + λs/λc双级高斯滤波 + GB/T 3505)')
add_para('3) 几何误差评定方法(平面度LSPL/MZPL + 圆度MZC/LSC/MCC/MLC + GB/T 24630 + GB/T 7235)')
add_para('4) HRG专用分析(旋转对称性误差 + 壁厚均匀性 + 谐振参数)')
add_para('5) STL模型对比与ICP配准')
add_para('6) 多指标加权质量评价体系')

add_title('17.2 核心创新点提炼', level=2)
add_para('1) 基于GB/T标准族的HRG陀螺综合精度评定体系(5项国标融合)')
add_para('2) 声明式步骤注册表实现分析流程动态编排')
add_para('3) v3.0几何分析+v4.0精度评定的统一分析框架')
add_para('4) 基于PCA+Rodrigues的旋转对称性定量评定')
add_para('5) 惯性张量→谐振频率偏移的简化估计模型')
add_para('6) 多策略ICP对齐(PCA初始+ICP精配准)')

add_title('17.3 关键数学公式汇总', level=2)
add_para('Ra = (1/l)∫|Z(x)|dx  (GB/T 3505 4.2.1)')
add_para('Rq = √[(1/l)∫Z²(x)dx]  (GB/T 3505 4.2.2)')
add_para('Rz = Rp + Rv  (GB/T 3505 4.1.3)')
add_para('G(x) = exp(-x²/(2σ²)), σ=λ/(2π)  (GB/T 18777)')
add_para('R_rodrigues = I + sinθ·K + (1-cosθ)·K²')
add_para('H = AᵀB, R = VUᵀ  (SVD刚体变换)')
add_para('I_tensor = [[Ixx,Ixy,Ixz],[Ixy,Iyy,Iyz],[Ixz,Iyz,Izz]]  (惯性张量)')
add_para('Δf = σ(λ_norm) × (1-mass_uniformity)  (频率偏移估计)')

output_path = r'D:\school\0shuo\gyroscopes\M_mHRG_Metric_analysis\M_mHRG_Metric\v3.0_Complete_Analyzer_Release\v4.0_Precision_Analyzer_Release\output\HRG技术点说明文档.docx'
doc.save(output_path)
print(f'文档已保存: {output_path}')
