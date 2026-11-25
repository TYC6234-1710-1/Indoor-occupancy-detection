# 基于环境传感器的室内占用检测

大数据分析课程项目。根据温度、湿度、光照、CO₂及含湿量，判断房间当前是否有人，比较阈值规则、逻辑回归与随机森林。

## 当前进度

- [x] 原始数据读取与质量检查。
- [x] 训练文件按时间划分训练集与验证集，并保存划分清单。
- [x] 光照阈值、逻辑回归、随机森林的首轮比较。
- [x] 保存验证配置、两个测试集及合并评价、逐条预测和比较图。
- [x] 光照、CO₂、组合与全部特征的对比实验。
- [x] 连续时段图、误报漏报及环境变化的事后事件分析。
- [x] 生成课程要求的 `occupancy_predictions.csv` 并独立核验。
- [x] 完成课程报告、提交文件核对与打包。

## 数据与实验约定

`data/datatraining.txt` 有8,143条观测；按时间排序，前6,514条训练，后1,629条验证。两个官方测试文件分别有2,665条和9,752条观测，独立评价。

原始文件的表头有7列，数据行额外包含一个记录编号。代码单独保留该编号，`source_row` 使用文件内从1开始的数据行号，不含表头。日期与编号不作为模型输入。`Occupancy=1` 为正类。

候选光照阈值来自训练部分，通过验证集F1选取。逻辑回归和随机森林也只通过验证集选择参数；概率分类阈值固定为0.5。配置确定后，机器学习模型使用完整训练文件重训，标准化也重新在完整训练文件拟合。测试结果用于评价，不用于回头选择参数。汇总指标通过合并预测重新计算。

## 运行

本次实验使用 Python 3.14.9。建议使用独立虚拟环境，依赖版本见 `requirements.txt`。

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe step01_check_data.py
.\.venv\Scripts\python.exe step02_compare_models.py
.\.venv\Scripts\python.exe run_complete_experiment.py
.\.venv\Scripts\python.exe validate_submission.py
```

若默认 `python` 不可用，请使用正常安装的 Python 可执行文件的完整路径创建环境。本项目虚拟环境不上传仓库。

`run_complete_experiment.py` 会重新执行第一轮模型比较，再补齐特征对比和分析，因此完整重跑时可以省略单独运行 `step02_compare_models.py`。

## 文件说明

- `step01_check_data.py`：标准库实现的数据检查，生成 `outputs/step01/data_check.json` 和 `split_manifest.json`。
- `step02_compare_models.py`：模型比较，生成 `outputs/step02/` 下的实验记录、选定配置、预测明细及图表。
- `outputs/step02/experiment.json`：含全部候选参数的验证成绩、最终测试指标、软件版本、随机种子和运行耗时。
- `outputs/step02/predictions.json`：三个方法的37,251条预测记录。规则的 `score` 为0/1输出，其余方法为估计概率；该文件暂未转换为最终提交CSV。
- `数据来源与说明.md`：题目要求与数据字段。
- `run_complete_experiment.py`：完整实验入口，结果保存至 `outputs/complete/`。
- `validate_submission.py`：使用原始数据独立检查预测覆盖、唯一性、标签、概率与指标计算。
- `outputs/complete/occupancy_predictions.csv`：最终格式预测文件，共6种方法，每方法12,417条，共74,502条记录。
- `docs/实验结果与分析.md`：实验方法、结果解释及局限，可作为最终报告的内容基础。

## 第一轮结果

逻辑回归在两个测试集的F1分别约为0.969和0.964。本轮两个测试集合并后的F1约为0.966。光照规则在第二个测试集产生451次误报，逻辑回归为52次，但后者漏报更多。上述结果为首轮实验，尚未完成特征对比与误差归因。

![两个测试集的模型F1比较](outputs/step02/model_comparison.png)

## 完整实验结果

本轮按预先确定的光照、CO₂、两者组合、全部特征进行比较，各组逻辑回归均在相同验证集上从 `C=0.1,1,10` 中选参数。概率阈值保持0.5，没有根据测试结果增加调参。

光照与CO₂组合的两个测试F1约为0.971、0.984，合并F1约为0.980；仅光照合并F1约为0.977，仅CO₂约为0.622。组合在合并测试上表现最高，但验证集并未将其排为第一，因此不能将其表述为通过验证选出的最终冠军，也不能据此断言跨房间最优。所有方法均保留在预测文件中。

切换后10分钟内的误判更集中。严格筛选的独立事件只有1次进入和11次离开，因此只给出描述性环境变化曲线，不估计固定的生理或通风响应滞后。误报成因也不能仅凭光照值确定。

![特征与方法对比](outputs/complete/feature_comparison.png)

完整分析见 [实验结果与分析](docs/实验结果与分析.md)。预测文件通过独立核验，记录见 `outputs/complete/validation.json`，课程提交版报告见下节。

## 课程报告与提交包

可编辑报告为 [室内占用检测课程项目实验报告](reports/室内占用检测课程项目实验报告.docx)，覆盖研究问题、数据说明、方法与实验设置、结果、误差分析、结论和局限，并附18组混淆矩阵计数及课程要求对应清单。个人姓名、学号请按课程要求补充。

完整交付说明见 [提交说明](docs/提交说明.md)。本地 `deliverables/室内占用检测课程项目提交包.zip` 包含报告、源码、数据、划分、预测明细、主要图表及逐文件SHA-256清单；压缩包不重复上传Git，解压后的文件均保留原有相对路径。

报告生成代码为 `build_course_report.py`。在独立文档环境中安装 `requirements-report.txt` 后可运行，不影响实验依赖。`package_submission.py` 生成提交包，要求当前报告哈希与已完成的逐页排版检查记录一致。更改报告后应重新渲染、检查并更新记录，再打包。Word排版检查使用LibreOffice与Poppler，本地工具及页面预览不入库。

## 数据来源与署名

数据来自 [UCI Occupancy Detection](https://archive.ics.uci.edu/dataset/357/occupancy+detection)。

Candanedo, L. (2016). Occupancy Detection. UCI. DOI: 10.24432/C5X01N。

数据采用 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 许可；具体署名见 `许可与署名.txt`。仓库中的原始TXT数据未修改；分析代码和生成结果为本课程项目新增内容。此处的数据许可不代表另行为项目代码指定许可。
