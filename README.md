# osk-skills

存放个人自定义 [Claude Code](https://claude.ai/code) 技能（Skills）的模块化仓库。你可以将这些技能引入你的 Claude Code 配置中，辅助开发与各类自动化处理任务。

## 🚀 技能速查矩阵 (Skill Matrix)

| 技能名称 (Skill) | 适用场景 | 亮点 / Token 优化策略 | 主要依赖 |
| :--- | :--- | :--- | :--- |
| **`pdf-to-gtp`** | 吉他/贝斯 PDF 乐谱转 Guitar Pro (`.gp5`) | 自动化向量几何解析、五线谱与 TAB 弦高音推导 | PyMuPDF, pyguitarpro, pdfminer.six |
| **`scanned-pdf-to-excel`** | 扫描件/大文件 PDF 账单转结构化 Excel | 多模态视觉/本地 RapidOCR 双引擎，图像 1280px 压缩 + CSV 输出 (**节省 70% Token**) | PyMuPDF, rapidocr_onnxruntime, openpyxl, pandas |

---

## 📂 项目目录结构

```text
osk-skills/
├── README.md               # 仓库使用说明
├── .gitignore              # Git 忽略文件（忽略编译缓存与测试临时产物）
└── skills/                 # 统一管理所有自定义技能的子目录
    ├── pdf-to-gtp/         # PDF 转换为 Guitar Pro (.gp5) 文件技能组
    │   ├── SKILL.md            # 技能描述与 prompt 指引
    │   ├── agents/
    │   │   └── openai.yaml     # 外部 Agent 配置
    │   ├── references/
    │   │   └── transcription-notes.md  # PDF 谱例识别提取的技术与算法笔记
    │   └── scripts/            # 工具脚本集合
    └── scanned-pdf-to-excel/   # 扫描版/图片版 PDF 转换为 Excel 技能组
        ├── SKILL.md            # 技能描述与 prompt 指引
        └── scripts/            # 拆图与 Excel 数据处理脚本
            ├── split_pdf.py       # PDF 页面压缩与图片拆分
            └── merge_to_excel.py  # 缺页自检与多页面 CSV 合并成 Excel
```

---

## ⚙️ 安装与配置说明

将需要的技能软链接或拷贝至本地 Claude Code 技能目录（默认路径为 `~/.claude/skills/`）：

```bash
# 复制全部技能到本地 Claude 技能目录
cp -r ./skills/* ~/.claude/skills/

# 或使用软链接引用特定技能（推荐，方便随仓库更新）
ln -s $(pwd)/skills/pdf-to-gtp ~/.claude/skills/pdf-to-gtp
ln -s $(pwd)/skills/scanned-pdf-to-excel ~/.claude/skills/scanned-pdf-to-excel
```

---

## 🛠️ 技能详细说明

### 1. `pdf-to-gtp` (PDF 转 Guitar Pro)
> 详细说明请参阅 [`skills/pdf-to-gtp/SKILL.md`](skills/pdf-to-gtp/SKILL.md)

- **环境依赖**：
  ```bash
  pip install PyMuPDF pyguitarpro pdfminer.six pdf2image
  ```
- **核心命令示例**：
  ```bash
  # 1. 渲染 pdf 的页面为调试用图片（检查剪裁与坐标）
  python ./skills/pdf-to-gtp/scripts/render_pdf_pages.py "./your_song.pdf" --out "./skills/pdf-to-gtp/scripts/images"

  # 2. 执行核心转换 (输出 your_song.gp5)
  python ./skills/pdf-to-gtp/scripts/convert_pdf_to_gp5.py "./your_song.pdf"
  ```

### 2. `scanned-pdf-to-excel` (扫描版 PDF 转 Excel)
> 详细说明请参阅 [`skills/scanned-pdf-to-excel/SKILL.md`](skills/scanned-pdf-to-excel/SKILL.md)

- **环境依赖**：
  ```bash
  pip install PyMuPDF openpyxl pandas rapidocr_onnxruntime
  ```
- **核心命令示例**：
  ```bash
  # 1. 拆分 PDF 并导出为高质量 1280px 压缩图片
  python ./skills/scanned-pdf-to-excel/scripts/split_pdf.py <pdf_path> <task_dir>/pdf_pages

  # 2. 缺页自检与数据合并导出成 Excel
  PYTHONIOENCODING=utf-8 python ./skills/scanned-pdf-to-excel/scripts/merge_to_excel.py <task_dir>/results <output_path.xlsx> [total_pages]
  ```

---

## 🤝 贡献与交流
如果你有其他实用的 Claude Code 技能，欢迎提交 PR 扩展本仓库！
