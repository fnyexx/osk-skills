---
name: scanned-pdf-to-excel
description: Use when converting scanned PDF documents or images into structured Excel spreadsheets via task subfolder isolation, PDF splitting, interactive engine selection (Default: Native Multimodal Vision; Optional: Local RapidOCR), missing page verification, Token optimization (CSV format + 1280px JPG image compression), and Excel assembly.
---

# Scanned PDF to Excel Conversion (扫描版大文件 PDF 转 Excel)

## Overview
扫描版/图片版 PDF 转换为结构化 Excel 的标准化高效处理管道。
核心要点：
1. **任务隔离**：开始任务前必须创建独立的任务子文件夹（如 `workspaces/<文件名>/`），所有中间过程文件（图片拆分、中间抽取结果、合并 Excel）都在该文件夹内集中管理，防止污染根目录。
2. **交互式模式选择（默认多模态视觉）**：在开始识别前询问用户选择识别引擎：
   - **默认推荐：原生多模态视觉识别（Native Multimodal Vision）** —— 使用大模型原生的 `Read` 工具/多 Agent 并发识别，准确度最高。
   - **可选：本地 Fast OCR 模式（Local RapidOCR）** —— 使用本地 CPU/GPU 运行轻量级 RapidOCR 脚本进行高速批量识别（0 API Token 消耗）。
3. **⚡ Token 极致优化策略**：
   - **文本层优先检测**：拆图前自动检测 PDF 是否含有电子文本层，若有则直接提取（0 Token 消耗）。
   - **图片切片压缩**：拆图时限制图片长边最大 1280px 并导出为 85% 质量 JPG，单个 Vision 页面 Tokens 消耗从 ~1500 降至 ~400（**节省 ~70% 输入 Token**）。
   - **CSV/TSV 结构化输出**：使用 CSV 紧凑文本代替带有重复 Key 的庞大 JSON 格式，规避冗余字段名重复（**节省 ~40% 输出 Token**）。

---

## ⚡ Workflow / 标准工作流

```
[原始扫描件 PDF]
       │
       ▼ (Step 1: 文本层检测 ➔ 图像压缩拆分 split_pdf.py ➔ 导出 1280px JPG)
[任务子文件夹: workspaces/<文件简称>/]
  ├── pdf_pages/ (存 1280px JPG 压缩图: page_001.jpg ...)
  ├── results/   (存提取的 CSV/JSON 数据: page_001.csv ...)
  └── <文件简称>.xlsx (最终导出的 Excel 表格)
       │
       ▼ (Step 2: 询问用户选择识别模式)
 ┌─────────────────────────────────────────────────────────────┐
 │ 1. 默认：原生多模态视觉识别 (Native Multimodal Vision Agent) │
 │ 2. 可选：本地 RapidOCR 批量识别 (Local RapidOCR Script)     │
 └─────────────────────────────────────────────────────────────┘
       │
       ▼ (Step 3 & 4: 缺页自检与数据组装)
[校验全量页码完整性 ➔ 运行 merge_to_excel.py 导出 Excel]
```

---

## 🛠️ Step 1: 任务子目录初始化与图片压缩拆分 (`scripts/split_pdf.py`)

运行拆图脚本，自动创建任务独立子文件夹，并将图片控制在长边 1280px 以内：
```bash
PYTHONIOENCODING=utf-8 python .claude/skills/scanned-pdf-to-excel/scripts/split_pdf.py <pdf_path> [task_dir] [max_long_edge]
```
- 若不传 `task_dir`，默认创建 `workspaces/<PDF文件名>/` 子文件夹。
- 自动检测电子文本层并提示。

---

## 🤖 Step 2: 交互选择识别模式 (AskUserQuestion)

在拆图完成后，**必须使用 `AskUserQuestion` 询问用户**：

### 选项定义：
1. **原生多模态视觉识别 (推荐/极高准确率)**: 默认选项。派发多 Agent 使用 Vision 视觉能力读取图片，以低 Token 的 CSV 格式转录。
2. **本地 RapidOCR 快速识别 (0 Token 消耗)**: 使用本地轻量 OCR 引擎批量扫描识别。

---

### 模式 1：默认原生多模态视觉识别 (Native Multimodal Vision)

按 **每组 8-10 页** 划分子任务，调用 `Agent` 并发处理。为了节省 Token，提示词要求输出结构化 **CSV 格式**（以英文逗号分隔）：

**并发 Agent Prompt 模板**：
```text
请依次使用 Read 工具读取 <task_dir>/pdf_pages/ 目录下的 page_001.jpg 至 page_010.jpg 图片。利用自身多模态视觉能力识别表格数据，并将每一页的识别结果保存为 CSV 文件存储至 <task_dir>/results/page_XXX.csv。

CSV 格式规范（第一行为统一表头）：
账户名称,对公账号,开户行,币种,明细序号,分录顺序号,交易日期,交易时间,记账方向,交易金额,交易后余额,交易行号,传票号,日志号,后台交易码,对方账号,对方名称,交易渠道,摘要
"优合集团有限公司","41000400040024624","410004","CNY","1","1","20150104","10:18:23","D","-660.00","437128.90","419999","0","112070540","DPOS0134","41999901941004383","","BTER","信息服务费"
```

---

### 模式 2：可选本地 RapidOCR 快速识别 (Local RapidOCR)

若用户选择 OCR 模式，运行 RapidOCR 批量脚本提取至 `results/`（无 API Token 消耗）：
```python
from rapidocr_onnxruntime import RapidOCR
# 遍历 pdf_pages 提取表格数据并保存至 results/page_XXX.csv
```

---

## 🔍 Step 3 & 4: 缺页自检与 Excel 数据合并 (`scripts/merge_to_excel.py`)

```bash
PYTHONIOENCODING=utf-8 python .claude/skills/scanned-pdf-to-excel/scripts/merge_to_excel.py <task_dir>/results <task_dir>/<文件名>.xlsx [total_pages]
```
- 自动对比 `total_pages` 进行缺页自检，确保 100% 提取后合并写入 Excel。
