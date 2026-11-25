"""从已核验的实验文件生成课程报告，不重新调参。

依赖 python-docx 与 Pillow；建议使用 Codex bundled document runtime。
"""
import csv
import json
from pathlib import Path
from docx import Document
from docx.shared import Cm, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

ROOT = Path(__file__).resolve().parent
RESULT = ROOT / 'outputs' / 'complete'
DEST = ROOT / 'reports'
NAMES = {'light_rule': '光照规则', 'lr_light': '光照 LR', 'lr_co2': 'CO₂ LR',
         'lr_light_co2': '光照＋CO₂ LR', 'logistic': '全特征 LR', 'random_forest': '随机森林'}
ORDER = list(NAMES)


def load_csv(name):
    with (RESULT / name).open(encoding='utf-8-sig', newline='') as handle:
        return list(csv.DictReader(handle))


def main():
    DEST.mkdir(exist_ok=True)
    records = load_csv('metrics.csv')
    results = {(r['dataset'], r['method']): r for r in records}
    experiment = json.loads((RESULT / 'experiment.json').read_text(encoding='utf-8'))
    checks = json.loads((RESULT / 'validation.json').read_text(encoding='utf-8'))
    assert checks['passed'] and checks['total_rows'] == 74502
    quality = json.loads((ROOT / 'outputs/step01/data_check.json').read_text(encoding='utf-8'))
    doc = Document()
    # 清除默认模板可能附带的标题装饰线，保持课程报告为纯黑标题。
    for style in doc.styles:
        for border in list(style.element.iter(qn('w:pBdr'))):
            border.getparent().remove(border)
    section = doc.sections[0]
    section.page_width, section.page_height = Cm(21), Cm(29.7)
    section.top_margin, section.bottom_margin = Cm(1.8), Cm(1.8)
    section.left_margin = section.right_margin = Cm(2)
    for name in ['Normal', 'Title', 'Subtitle', 'Heading 1', 'Heading 2', 'Caption']:
        style = doc.styles[name]
        style.font.name = 'Calibri'
        style.element.get_or_add_rPr().rFonts.set(qn('w:eastAsia'), '宋体')
        style.font.color.rgb = RGBColor(0, 0, 0)
        style.font.italic = False
        style.font.underline = False
    normal = doc.styles['Normal']
    normal.font.size = Pt(10.5)
    normal.paragraph_format.line_spacing = 1.25
    normal.paragraph_format.space_after = Pt(6)
    for name, size in [('Title', 20), ('Heading 1', 15), ('Heading 2', 11.5)]:
        doc.styles[name].font.size = Pt(size)
        doc.styles[name].font.bold = True
    doc.styles['Heading 1'].paragraph_format.space_after = Pt(10)
    doc.styles['Caption'].font.size = Pt(9)
    doc.styles['Caption'].font.italic = False
    header = section.header.paragraphs[0]
    header.text = '大数据分析期末课程项目  ·  第14题'
    header.runs[0].font.size = Pt(8)
    footer = section.footer.paragraphs[0]
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    footer.add_run('第 ')
    field = OxmlElement('w:fldSimple'); field.set(qn('w:instr'), 'PAGE')
    footer._p.append(field)
    footer.add_run(' 页')
    for r in footer.runs:
        r.font.size = Pt(8)
    doc.core_properties.title = '基于环境传感器的室内占用检测实验报告'
    doc.core_properties.author = ''
    doc.core_properties.subject = '数据质量、规则与模型比较、特征分析、误判与环境响应'

    def p(text, style=None):
        obj = doc.add_paragraph(text, style)
        obj.paragraph_format.widow_control = True
        return obj

    def h(text, level=1):
        doc.add_heading(text, level)

    def page(text):
        doc.add_page_break(); h(text)

    def table(headers, rows, widths=None, size=9):
        t = doc.add_table(rows=1, cols=len(headers))
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        t.autofit = False
        widths = widths or [17 / len(headers)] * len(headers)
        for i, width in enumerate(widths):
            t.columns[i].width = Cm(width)
        for i, value in enumerate(headers):
            t.rows[0].cells[i].text = str(value)
        for row in rows:
            cells = t.add_row().cells
            for i, value in enumerate(row):
                cells[i].text = str(value)
        for j, row in enumerate(t.rows):
            trpr = row._tr.get_or_add_trPr()
            no_split = OxmlElement('w:cantSplit'); trpr.append(no_split)
            if j == 0:
                repeat = OxmlElement('w:tblHeader'); trpr.append(repeat)
            for i, cell in enumerate(row.cells):
                cell.width = Cm(widths[i])
                cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
                prop = cell._tc.get_or_add_tcPr()
                shade = OxmlElement('w:shd')
                shade.set(qn('w:fill'), 'E8EDF1' if j == 0 else ('F5F7F8' if j % 2 == 0 else 'FFFFFF'))
                prop.append(shade)
                margins = OxmlElement('w:tcMar')
                for side in ['top', 'left', 'bottom', 'right']:
                    item = OxmlElement('w:' + side); item.set(qn('w:w'), '70'); item.set(qn('w:type'), 'dxa'); margins.append(item)
                prop.append(margins)
                borders = OxmlElement('w:tcBorders')
                for side in ['top', 'left', 'bottom', 'right']:
                    item = OxmlElement('w:' + side)
                    for key, val in [('val', 'single'), ('sz', '4'), ('color', 'D9D9D9')]:
                        item.set(qn('w:' + key), val)
                    borders.append(item)
                prop.append(borders)
                for para in cell.paragraphs:
                    para.alignment = WD_ALIGN_PARAGRAPH.LEFT if i == 0 else WD_ALIGN_PARAGRAPH.CENTER
                    para.paragraph_format.space_after = Pt(0)
                    para.paragraph_format.line_spacing = 1.1
                    for run in para.runs:
                        run.font.size = Pt(size); run.bold = j == 0
        p('')
        return t

    def image(name, caption, width=16.5):
        para = doc.add_paragraph()
        para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        para.add_run().add_picture(str(RESULT / name), width=Cm(width))
        para.paragraph_format.keep_with_next = True
        cap = p(caption, 'Caption'); cap.alignment = WD_ALIGN_PARAGRAPH.CENTER

    p('基于环境传感器的室内占用检测', 'Title')
    p('大数据分析期末课程项目实验报告', 'Subtitle')
    h('摘要', 2)
    p('本项目利用温度、湿度、光照、CO₂和含湿量判断房间当前是否有人，在固定时间划分下比较光照阈值规则、逻辑回归与随机森林，并进行传感器特征对比、误判分组和状态切换事件分析。数据共20,560条，两个官方测试集共12,417条。光照与CO₂组合模型在两个测试集的F1分别为0.9709和0.9838，合并F1为0.9796；仅光照模型的合并F1为0.9771，仅CO₂模型为0.6219。结果显示，光照具有较强识别作用，全部特征与复杂模型未必更优。状态切换附近误判更集中，但严格筛选后仅有1次进入与11次离开事件，无法估计普适的固定响应滞后。')
    p('关键词：室内占用检测；环境传感器；逻辑回归；时间划分；误报与漏报。')
    h('1 研究问题与数据说明')
    p('研究目标为当前状态检测，而非提前预测。比较规则与机器学习的表现，检验光照、CO₂及其他环境量的信息增量，并讨论单一房间的适用范围。标签Occupancy中1表示有人、0表示无人。')
    table(['文件', '记录数', '有人数', '有人比例', '时间位置'], [
        ['datatraining.txt', '8,143', '1,729', '21.23%', '训练期'],
        ['datatest.txt', '2,665', '972', '36.47%', '训练期之前'],
        ['datatest2.txt', '9,752', '2,049', '21.01%', '训练期之后']], [4.6, 2, 2, 2.4, 6], 9)
    p('训练期为2015年2月4日17:51至2月10日09:33。测试1覆盖2月2日14:19至2月4日10:43，测试2覆盖2月11日14:48至2月18日09:19。因此两个测试分别反映更早与更晚时段的检测表现，不能都称为未来预测。')
    p('五个环境特征均无空缺，三个文件的时间戳无重复；记录间隔为59、60或61秒，近似分钟级。原始文件每行额外包含记录编号，读取时与七个具名字段分开。预测输出source_row为文件内1起始数据行号，不含表头。')

    page('2 数据分布与实验设计')
    h('2 1 环境变量分布', 2)
    distributions = load_csv('feature_distributions.csv')
    aliases = {'Temperature': '温度 ℃', 'Humidity': '相对湿度 %', 'Light': '光照 Lux', 'CO2': 'CO₂ ppm', 'HumidityRatio': '含湿量 kg/kg'}
    rows = []
    for f, label in aliases.items():
        no = next(r for r in distributions if r['source_file'] == 'datatraining.txt' and r['feature'] == f and r['occupancy'] == '0')
        yes = next(r for r in distributions if r['source_file'] == 'datatraining.txt' and r['feature'] == f and r['occupancy'] == '1')
        fmt = '.5f' if f == 'HumidityRatio' else '.2f'
        rows.append([label, format(float(no['median']), fmt), format(float(yes['median']), fmt), format(float(no['mean']), fmt), format(float(yes['mean']), fmt)])
    table(['环境量', '无人中位数', '有人中位数', '无人均值', '有人均值'], rows, [4.2,3.2,3.2,3.2,3.2])
    p('表中统计基于完整训练文件，仅用于数据描述。光照和CO₂的两类分布存在重叠，不能视为完全可分。测试2无人记录的CO₂中位数为587.5 ppm，高于训练文件的446 ppm，提示绝对浓度与占用的关系随时段变化。其余分位数、标准差和极值保存在特征分布明细。')
    p('仅用训练部分计算的湿度与含湿量相关系数约0.918，光照与CO₂约0.808，说明特征存在信息重叠；相关性不能单独解释模型性能差异。')
    h('2 2 数据划分与参数选择', 2)
    p('训练文件按时间排序，前6,514条训练、后1,629条验证。验证集仅用于阈值和参数选择，固定配置后使用完整8,143条训练数据重训，再分别评价两个官方测试集。标准化在相应拟合阶段的训练数据上完成，日期、编号与标签不作为输入。')
    table(['方法', '候选配置与选择方式'], [
        ['光照规则', '训练部分的201个分位点去重作候选；验证F1最高，并列取较低阈值。最终Light > 177.038 Lux判有人。'],
        ['逻辑回归 LR', '标准化；C∈{0.1,1,10}；max_iter=2000；按验证F1选C，概率阈值固定0.5。'],
        ['随机森林', '200棵树；max_depth∈{5,无限}；min_samples_leaf∈{1,5}；验证选择深度5、最小叶样本1。']], [3.2,13.8])
    p('逻辑回归预定比较光照、CO₂、光照与CO₂、全部5特征四组输入，所选C分别为0.1、1、10、1。随机种子固定42。第一轮测试成绩已被查看；后续按课程规定的固定特征组完成比较，没有追加测试驱动的搜索，也不将其表述为新的盲测。')

    page('3 两个测试集的分类结果')
    p('以有人为正类。Precision=TP/(TP+FP)，Recall=TP/(TP+FN)，F1=2TP/(2TP+FP+FN)，FPR=FP/(FP+TN)。FP为无人判有人，FN为有人判无人；Precision、Recall零分母按0处理，分组无负类时FPR留空。')
    for dataset, title in [('datatest.txt','测试1  共2665条'), ('datatest2.txt','测试2  共9752条')]:
        h(title, 2)
        table(['方法', 'Precision', 'Recall', 'F1', 'FPR', 'FP', 'FN'],
              [[NAMES[m]] + [f"{float(results[dataset,m][v]):.4f}" for v in ['precision','recall','f1','fpr']] +
               [results[dataset,m]['fp'], results[dataset,m]['fn']] for m in ORDER], [4,2.5,2.3,2.3,2.3,1.3,1.3], 8.5)
    p('测试1各方法的光照相关表现较好；测试2中CO₂单独使用下降明显，光照规则也出现451次误报。全特征逻辑回归在测试2只误报52次，但漏报93次，显示不同决策边界对应不同错误取舍。')
    p('光照与CO₂组合在测试1的F1略低于仅光照模型，在测试2略高。所有方法以同一批观测和相同指标比较；不只报告最有利的单个文件。完整混淆矩阵计数见第8节。')

    page('4 特征对比与合并结果')
    image('feature_comparison.png', '图1  各方法在两个官方测试集上的有人类F1。LR表示逻辑回归。')
    table(['方法', '合并Precision', '合并Recall', '合并F1', '合并FPR'],
          [[NAMES[m]] + [f"{float(results['pooled',m][v]):.4f}" for v in ['precision','recall','f1','fpr']] for m in ORDER], [4,3.25,3.25,3.25,3.25], 8.5)
    p('合并指标由12,417条预测重新计算，未对两个测试F1取平均。组合模型合并误报111条、漏报14条，在本轮合并测试上F1最高。全部特征和随机森林未超过简单组合，说明增加输入或模型复杂度并不保证增益。')
    p('仅光照逻辑回归重训后的0.5概率边界约341.36 Lux，高于规则阈值177.04 Lux；两者差异部分来自决策边界，不能把组合模型的全部改善都归因于CO₂。')
    p('组合模型验证F1为0.9583，低于规则0.9941、仅光照LR的0.9924和随机森林0.9941。组合在测试上的领先是描述性发现，不能称为验证选出的冠军，也不能证明跨房间最优。')

    page('5 连续状态与误差分析')
    image('timeline_datatest2_second_day.png', '图2  测试2第二个日历日的环境与状态变化。状态对照为真实值、光照规则、全特征LR。', 16)
    p('图示日期按各文件第二个日历日固定选取，同时保留两个文件全时段图。测试2中，光照规则在2月12日10:38:59至12:42:00连续误报124条，光照中位数274.5 Lux，超过规则阈值。数据没有灯具开关或日照标签，不能确认具体光源。')
    h('状态切换后的误差分组', 2)
    slices = load_csv('error_slices.csv')
    slice_rows = []
    for filename, label in [('datatest.txt','测试1'), ('datatest2.txt','测试2')]:
        for period, period_label in [('within_10min_after_change','切换后10分钟内'),('over_10min_after_change','距切换超过10分钟')]:
            r = next(r for r in slices if r['source_file'] == filename and r['method'] == 'lr_light_co2' and r['period'] == period)
            slice_rows.append([label,period_label,r['n'],r['fp'],r['fn'],f"{float(r['f1']):.4f}"])
    table(['集合', '时段', '样本数', 'FP', 'FN', 'F1'], slice_rows, [2,5.5,2.5,2,2,3], 8.5)
    p('组合模型在切换附近误判更集中。文件开头到第一次切换前的状态持续时间未知，单列而非当作稳定时段。各组类别比例也不同，因此差异不能完全归因于响应滞后；此分组仅作事后解释。')

    page('6 环境响应与滞后分析')
    image('transition_profiles.png', '图3  独立切换事件的环境变化。实线为事件中位数，阴影为四分位范围，并非置信区间。', 16)
    p('三个文件共有57次进入和57次离开切换。要求切换前后各30个采样点完整、间隔不超过61秒且窗口内无其他切换后，只剩1次进入和11次离开事件。未通过重标记或平滑标签增加事件数。')
    table(['事件', '合格数量', '约5分钟后', '约15分钟后', '约30分钟后'], [
        ['进入',1,'+8.83 ppm','+24.00 ppm','+72.50 ppm'],
        ['离开',11,'−20.50 ppm','−31.67 ppm','−92.00 ppm']], [3,2.5,3.8,3.8,3.9], 9)
    p('表中为CO₂相对切换前5个观测中位数的差值；离开行再取事件间中位数。横轴为相对采样点，近似分钟，不能解读为精确的固定响应时间。光照可能较快变化，而CO₂呈逐步变化；离开前CO₂已有下降，不能将整段下降都归因于离开。')
    p('通风、人数、环境背景未控制，进入事件仅1个，更不支持一般化的滞后结论。未来观测仅用于事后曲线，分类器没有使用。')

    page('7 结论局限与复现说明')
    h('7 1 结论与适用范围', 2)
    p('本数据集上，光照具有较强的当前占用识别能力；CO₂单独使用对跨时段分布变化较敏感。光照与CO₂组合的合并F1约0.980，全部特征与随机森林没有进一步改善。结果说明特征选择和决策边界的重要性，也显示状态切换附近的识别难度。')
    p('本研究限于单一房间与有限日期。照明习惯、自然光、通风变化和背景CO₂均可能影响结果。分钟级观测存在依赖，不能把12,417条记录当成同样数量的独立实验；本报告不进行独立同分布假设下的显著性宣称。实际应用前应使用新日期或新房间独立验证，并根据误报、漏报代价选方案。')
    h('7 2 运行环境与复现', 2)
    p('实验环境：Python 3.14.9，NumPy 2.5.5，SciPy 1.18.1，scikit-learn 1.9.1，Matplotlib 3.11.2。依赖固定在requirements.txt。实验为小规模本地CPU计算，不要求GPU、Spark或大模型服务。')
    p('首轮模型比较记录耗时约' + f"{json.loads((ROOT/'outputs/step02/experiment.json').read_text(encoding='utf-8'))['elapsed_seconds']:.2f}" + '秒；完整实验记录耗时约' + f"{experiment['elapsed_seconds']:.2f}" + '秒。分别包含对应脚本内的数据处理与结果生成，且范围不同，不能视为单模型训练耗时或直接相减。耗时会随设备与系统负载变化。')
    for line in ['python -m venv .venv', '.venv/Scripts/python.exe -m pip install -r requirements.txt',
                 '.venv/Scripts/python.exe step01_check_data.py', '.venv/Scripts/python.exe run_complete_experiment.py',
                 '.venv/Scripts/python.exe validate_submission.py']:
        obj = p(line); obj.paragraph_format.space_after = Pt(2)
        for r in obj.runs: r.font.name = 'Consolas'; r.font.size = Pt(8.5)
    h('7 3 结果文件与核验', 2)
    p('occupancy_predictions.csv包含source_file、source_row、date、occupancy_true、occupancy_pred、score、method七列，六种方法各覆盖12,417条测试记录，总计74,502条。规则score为0或1，其他方法为估计概率。文件逐条通过覆盖、唯一标识、真实标签、时间、分数范围和指标重算核验。')
    p('提交包同时保留完整源码、运行说明、数据划分、参数记录、指标、误差明细与图表。原始输入、处理结果和报告分目录保存。')
    h('数据来源与引用', 2)
    p('Candanedo, L. (2016). Occupancy Detection. UCI Machine Learning Repository. DOI: 10.24432/C5X01N。https://archive.ics.uci.edu/dataset/357/occupancy+detection。原始数据采用CC BY 4.0；原始TXT未修改，代码与实验结果为本项目新增。')

    page('8 混淆矩阵与要求对应')
    p('下表用TN、FP、FN、TP完整表示每个方法的2×2混淆矩阵。矩阵行是真实类别0、1，列是预测类别0、1，即第一行为TN、FP，第二行为FN、TP。合并行由两个测试计数求和。')
    table(['集合', '方法', 'TN', 'FP', 'FN', 'TP'],
          [[{'datatest.txt':'测试1','datatest2.txt':'测试2','pooled':'合并'}[d],NAMES[m]] + [results[d,m][k] for k in ['tn','fp','fn','tp']]
           for d in ['datatest.txt','datatest2.txt','pooled'] for m in ORDER], [2,5,2.5,2.5,2.5,2.5], 8.5)
    h('课程要求对应', 2)
    table(['任务', '本报告及配套文件'], [
        ['数据质量与分布','第1至2节；data_check.json、feature_distributions.csv'],
        ['规则与模型比较','第2至4节；experiment.json、metrics.csv'],
        ['特征对比','第4节及图1；四组输入的逻辑回归比较'],
        ['误判与连续状态','第5节；连续图、error_slices.csv、error_episodes.csv'],
        ['滞后与适用范围','第6至7节；transition_events.csv及图3'],
        ['源码划分与预测','第7节；源码、split_manifest.json、预测CSV与validation.json']], [4,13], 8.5)
    path = DEST / '室内占用检测课程项目实验报告.docx'
    doc.save(path)
    print(path)


if __name__ == '__main__':
    main()
