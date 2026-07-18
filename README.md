# osk-skills

这是一个用于存放个人自定义 [Claude Code](https://claude.ai/code) 技能（Skills）的仓库。你可以将这些技能引入你的 Claude Code 配置中，辅助开发与各类自动化处理任务。

## 项目目录结构

```
osk-skills/
├── README.md               # 仓库使用说明
├── .gitignore              # Git 忽略文件（忽略编译缓存与测试 PDF 临时产物）
└── skills/                 # 统一管理所有自定义技能的子目录
    └── pdf-to-gtp/         # PDF 转换为 Guitar Pro (.gp5) 文件技能组
        ├── SKILL.md            # 技能描述与 prompt 指引
        ├── agents/
        │   └── openai.yaml     # 外部 Agent 配置（如有）
        ├── references/
        │   └── transcription-notes.md  # PDF 谱例识别提取的技术与算法笔记
        └── scripts/            # 工具脚本集合
            ├── render_pdf_pages.py     # PDF 页面渲染（DPI 调整等）
            ├── convert_pdf_to_gp5.py  # 核心转换调度入口
            ├── rhythm_inference.py    # 视觉/时值推导算法
            ├── map_notes_rests.py     # TAB 字符与六线谱物理弦映射
            ├── extract_geometry.py    # PDF 物理排版向量边界提取
            ├── analyze_pdf.py         # PDF 格式初步剖析
            ├── analyze_systems.py     # 谱行排版系统分析
            ├── verify_gp5.py          # 对生成的 gp5 进行解析与回读校验
            └── copy_correct_file.py   # 文件辅助整理工具
```

---

## 包含的技能列表

### 1. `pdf-to-gtp`
自动将 PDF 吉他谱（支持矢量的六线谱、扫描简谱、线谱、混合排版）转换成可在 Guitar Pro 软件中编辑与播放的 `.gp5` 文件。

#### 核心特征:
- **坐标解析**：基于 `pdfminer`/`fitz` (PyMuPDF) 的字符物理坐标提取，能够按像素/点的位置计算音符和弦，而不是直接展平文本，防止音轨和弦串行。
- **节奏推导**：基于下方符干/符尾的连接数量确定时值，退化情况下支持使用 DFS 贪心规划基于物理间距的最优时长划分。
- **技巧处理**：自动分析曲线与方向，转换得出 Legato（Hammer-on / Pull-off），Slide，Let ring 以及 Tie 延音。
- **拍弦/打板识别**：自动通过矢量小线段交叉判定 deadnote `X` 标记，而非单纯依赖 `X` 字符。
- **扫弦/琶音判定**：通过识别锯齿线与箭头方向物理坐标自动推导。
- **自动对齐段落与反复记号**：根据矢量画线附近的小双实点检测 Repeat Open/Close 并设置相应的 measure 标志，通过小标签文字自动识别一排与二排结尾（Alternative Endings）。
- **回读校验**：基于 `pyguitarpro` 将生成的 `.gp5` 序列化文件读回解析，并和 PDF 音符数、结构进行严格的一对一审计。

---

## 如何在你的 Claude Code 中使用本技能

根据 Claude Code 的官方说明，你可以在自定义技能/记忆路径引入本仓库的 `SKILL.md`。

通常做法是直接将对应技能的 `SKILL.md` 写入或软链接至你的本地 Claude 配置目录：
`~/.claude/skills/pdf-to-gtp/SKILL.md`

### 依赖环境配置（对于 python 工具类技能）
`pdf-to-gtp` 依赖以下 Python 库，如果需要本地运行或测试：
```bash
pip install PyMuPDF pyguitarpro pdfminer.six
```
渲染 PDF 成图片供模型二次检查（可选）：
```bash
pip install pdf2image
```
*注：`pdf2image` 依赖系统安装有 `poppler`。*

### 转换命令示例
```bash
# 1. 渲染 pdf 的页面为调试用图片（检查剪裁与坐标）
python ./skills/pdf-to-gtp/scripts/render_pdf_pages.py "./your_song.pdf" --out "./skills/pdf-to-gtp/scripts/images"

# 2. 执行核心转换 (输出 your_song.gp5)
python ./skills/pdf-to-gtp/scripts/convert_pdf_to_gp5.py "./your_song.pdf"
```

## 贡献与交流
如果你有其他实用的 Claude Code 技能，欢迎提交 PR 扩展本仓库！