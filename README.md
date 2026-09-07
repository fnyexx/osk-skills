# osk-skills - 跨 Agent 实用技能库 (Agent Skills Collection)

<p align="left">
  <img src="https://img.shields.io/badge/Agent_Skills-Compatible-blue?style=flat-square" alt="Agent Skills">
  <img src="https://img.shields.io/badge/Claude_Code-Supported-purple?style=flat-square" alt="Claude Code">
  <img src="https://img.shields.io/badge/OpenCode-Supported-orange?style=flat-square" alt="OpenCode">
  <img src="https://img.shields.io/badge/Python-3.10+-brightgreen?style=flat-square" alt="Python 3.10+">
  <img src="https://img.shields.io/badge/Node.js-18+-green?style=flat-square" alt="Node.js 18+">
  <img src="https://img.shields.io/badge/License-MIT-blue.svg?style=flat-square" alt="License">
</p>

存放模块化、高性能自定义 AI 技能（Skills）的精选仓库。遵循跨平台 Agent Skills 标准，无缝兼容 [Claude Code](https://claude.ai/code)、[OpenCode](https://github.com/opencode)、Cursor、Windsurf 等现代智能编程助手与自动化 Agent。

每个技能均包含独立完整的运行环境声明、Prompt 指引规范 (`SKILL.md`) 以及开箱即用的核心处理脚本，助力复杂自动化工作流落地。

---

## 🚀 技能速查矩阵 (Skill Matrix)

| 技能名称 (Skill) | 核心场景 | 关键技术 / Token 优化策略 | 运行环境 | Agent 交互示例 |
| :--- | :--- | :--- | :--- | :--- |
| [**`pdf-to-gtp`**](#1-pdf-to-gtp-pdf-转-guitar-pro-乐谱) | 吉他/贝斯 PDF 乐谱转 Guitar Pro (`.gp5`) | 自动化向量几何解析、五线谱与 TAB 弦高音推导、节奏推理纠错 | Python 3.10+ | *"将这首曲子的吉他 PDF 谱转成 gp5 工程"* |
| [**`scanned-pdf-to-excel`**](#2-scanned-pdf-to-excel-扫描版-pdf-转-excel) | 扫描件/大文件 PDF 账单转结构化 Excel | 多模态视觉/本地 RapidOCR 双引擎，图像 1280px 压缩 + CSV 输出 (**节省 70% Token**) | Python 3.10+ | *"把发票/对账单扫描 PDF 整理导出为 Excel 表格"* |
| [**`image-gen`**](#3-image-gen-跨-agent-通用图像生成) | 跨 Agent 通用图像生成（文生图/垫图修改） | 零依赖独立运行，支持长提示词文件、种子控制、指数退避重试与元数据溯源 | Node.js 18+ | *"帮我生成一张 16:9 的赛博朋克雨夜街道 4K 壁纸"* |

---

## 📂 项目目录结构

```text
osk-skills/
├── README.md               # 仓库使用与配置说明
├── .gitignore              # Git 忽略配置（忽略本地缓存与临时产物）
└── skills/                 # 核心技能目录（每个技能为独立模块）
    ├── image-gen/              # 跨 Agent 通用图像生成技能
    │   ├── SKILL.md            # 技能定义与提示词规范
    │   ├── README.md           # 详细参数与特性说明
    │   ├── config.example.json # 配置文件示例
    │   └── scripts/
    │       └── generate.js     # 零外部依赖的独立生图脚本
    ├── pdf-to-gtp/         # PDF 转换为 Guitar Pro (.gp5) 技能
    │   ├── SKILL.md            # 技能描述与执行 SOP
    │   ├── agents/
    │   │   └── openai.yaml     # 外部 Agent 配置
    │   ├── references/
    │   │   └── transcription-notes.md  # 谱例解析算法与技术笔记
    │   └── scripts/            # 几何提取、音符映射与验证脚本集合
    └── scanned-pdf-to-excel/   # 扫描件/长文档 PDF 转 Excel 技能
        ├── SKILL.md            # 技能描述与处理流程规范
        └── scripts/            # 拆图与多页数据合并脚本
            ├── split_pdf.py       # PDF 页面缩放与高质量图片拆分
            └── merge_to_excel.py  # 缺页自动校验与 CSV 汇总合并
```

---

## ⚙️ 安装与配置说明

推荐使用**符号链接（软链接）**将技能引入各 Agent 的技能读取目录，后续仓库更新可实时同步生效。

### 1. Claude Code 接入

Claude Code 默认的技能根目录为 `~/.claude/skills/`（Windows 为 `%USERPROFILE%\.claude\skills`）。

#### macOS / Linux (Bash)
```bash
# 进入仓库根目录
cd /path/to/osk-skills

# 创建软链接引入全部技能
mkdir -p ~/.claude/skills
ln -s "$(pwd)/skills/image-gen" ~/.claude/skills/image-gen
ln -s "$(pwd)/skills/scanned-pdf-to-excel" ~/.claude/skills/scanned-pdf-to-excel
ln -s "$(pwd)/skills/pdf-to-gtp" ~/.claude/skills/pdf-to-gtp
```

#### Windows (PowerShell)
```powershell
# 确保目标目录存在
New-Item -ItemType Directory -Force -Path "$HOME\.claude\skills"

# 创建软链接（需管理员权限或开启开发者模式）
New-Item -ItemType SymbolicLink -Path "$HOME\.claude\skills\image-gen" -Target "$PWD\skills\image-gen"
New-Item -ItemType SymbolicLink -Path "$HOME\.claude\skills\scanned-pdf-to-excel" -Target "$PWD\skills\scanned-pdf-to-excel"
New-Item -ItemType SymbolicLink -Path "$HOME\.claude\skills\pdf-to-gtp" -Target "$PWD\skills\pdf-to-gtp"
```

> **提示**：若环境受限无法创建符号链接，直接使用 `cp -r ./skills/<skill-name> ~/.claude/skills/` 复制目录即可。

### 2. OpenCode 及其他 Agent 接入
可将技能目录放置在对应项目的 `.opencode/skills/` 或全局 Skills 路径下，具体以各 Agent 客户端配置为准。

---

## 🛠️ 技能详细说明与使用

### 1. `pdf-to-gtp` (PDF 转 Guitar Pro 乐谱)
> 完整规范请参阅 [`skills/pdf-to-gtp/SKILL.md`](skills/pdf-to-gtp/SKILL.md)

- **核心价值**：解析吉他/贝斯 PDF 谱中的矢量几何（小节线、符头、TAB 数字、连音线），自动推导节奏与时值，生成标准 Guitar Pro 5 (`.gp5`) 工程文件。
- **环境依赖**：
  ```bash
  pip install PyMuPDF pyguitarpro pdfminer.six pdf2image
  ```
- **Agent 对话调用示例**：
  > *"请帮我将 `jiuzui.pdf` 乐谱转换为 Guitar Pro 的 `.gp5` 文件，并检查小节节拍完整性。"*
- **底层命令行执行**：
  ```bash
  # 1. 提取并渲染页面几何定位（排查对齐）
  python ./skills/pdf-to-gtp/scripts/extract_geometry.py "./input.pdf"

  # 2. 端到端转制并生成 .gp5 文件
  python ./skills/pdf-to-gtp/scripts/convert_pdf_to_gp5.py "./input.pdf"
  ```

---

### 2. `scanned-pdf-to-excel` (扫描版 PDF 转 Excel)
> 完整规范请参阅 [`skills/scanned-pdf-to-excel/SKILL.md`](skills/scanned-pdf-to-excel/SKILL.md)

- **核心价值**：专为财务对账单、扫描票据、历史文档设计。通过高质量拆图分发、1280px 分辨率适配以及逐页转 CSV 汇总，实现**多页长文档处理不爆上下文、Token 消耗骤降 70%**。
- **环境依赖**：
  ```bash
  pip install PyMuPDF openpyxl pandas rapidocr_onnxruntime
  ```
- **Agent 对话调用示例**：
  > *"这里有一份扫描版银行对账单 PDF（共 20 页），请使用 scanned-pdf-to-excel 技能帮我转成结构化 Excel 文件。"*
- **底层命令行执行**：
  ```bash
  # 1. 拆分 PDF 页面为优化尺寸图片 (1280px 宽度)
  python ./skills/scanned-pdf-to-excel/scripts/split_pdf.py input.pdf ./task_dir/pages

  # 2. 汇总各页识别的 csv 结果并导出合并 Excel（带缺页自检）
  PYTHONIOENCODING=utf-8 python ./skills/scanned-pdf-to-excel/scripts/merge_to_excel.py ./task_dir/results ./output.xlsx 20
  ```

---

### 3. `image-gen` (跨 Agent 通用图像生成)
> 详细参数与高级功能参阅 [`skills/image-gen/README.md`](skills/image-gen/README.md) 与 [`skills/image-gen/SKILL.md`](skills/image-gen/SKILL.md)

- **核心价值**：纯原生 Node.js 实现的文生图/图生图模块。针对终端转义痛点提供长文件输入 (`--prompt-file`)，内置 API 重试、批量出图、随机种子控制及伴生元数据 (`.meta.json`)。
- **环境依赖**：
  Node.js (>= 18)，**零额外 npm 依赖**。首次使用请复制并配置 API Key：
  ```bash
  cp ./skills/image-gen/config.example.json ./skills/image-gen/config.json
  ```
- **Agent 对话调用示例**：
  > *"帮我设计一张科技感的主视觉封面图，比例 16:9，分辨率 4K，并自动打开预览。"*
- **底层命令行执行**：
  ```bash
  # 1. 基础文本生图 (默认 1:1, 2K)
  node ./skills/image-gen/scripts/generate.js -p "Cyberpunk neon city street, rainy night, highly detailed, 8k"

  # 2. 使用长提示词文件 + 垫图修改 + 指定尺寸与画幅
  node ./skills/image-gen/scripts/generate.js --prompt-file ./prompt.txt -i ./base.png -r 16:9 -s 4K --open
  ```

---

## 🧩 如何添加新技能 (Add a New Skill)

欢迎为本仓库贡献新技能！建议遵循以下标准目录规范：

```text
skills/my-new-skill/
├── SKILL.md              # [必选] 技能核心：包含技能简介、Trigger 触发词、SOP 流程
├── README.md             # [推荐] 详细使用说明、原理与高级参数
├── config.example.json   # [可选] 如涉及外部 API Key，请提供无敏感信息的示例配置
└── scripts/              # [推荐] 存放该技能依赖的可执行脚本 (Python/Node/Shell 等)
```

1. **新建技能文件夹**：在 `skills/` 目录下创建以 `kebab-case` 命名的子目录。
2. **编写 `SKILL.md`**：明确定义 Agent 的角色定位、何时触发、分步执行步骤以及异常处理策略。
3. **隔离敏感信息**：若需使用 API 密钥或凭证，请务必在技能根目录或仓库根目录的 `.gitignore` 中配置对应规则。
4. **更新根文档**：在根目录 `README.md` 的技能矩阵与使用说明中同步添加新技能条目。

---

## 🤝 贡献与交流

- **反馈与建议**：若在技能使用过程中遇到任何问题或优化思路，欢迎提交 [Issues](https://github.com/fnyexx/osk-skills/issues)。
- **提交贡献**：欢迎 Fork 本仓库并提交 Pull Request，共同建设实用的跨 Agent 技能生态！

## 📄 开源许可证

本项目基于 [MIT License](LICENSE) 开源。
