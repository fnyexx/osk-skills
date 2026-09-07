# image-gen Skill (跨 Agent 通用图像生成技能 - 增强版)

本技能遵循 Agent Skills 开放标准，可在多个 AI Agent 工具（OpenCode、Claude Code、Cursor、Windsurf、Cline、Aider 等）中直接使用。

## 新增增强特性 (v2.0)
- 📝 **长提示词文件输入 (`--prompt-file`)**：彻底避免终端命令行因特殊字符、换行与双引号导致的截断转义问题。
- 🖼️ **垫图/图生图支持 (`-i, --image`)**：支持传入本地底图进行以图画图、风格迁移与画面修改。
- 🎲 **多图批量与种子控制 (`-n, --count`, `--seed`)**：支持一次性生成 1~4 张图片抽卡，支持指定固定随机种子。
- 🛡️ **请求超时与自动重试**：内置 60s 超时与针对 429/5xx 故障的指数退避重试，防止进程无限挂起。
- 📑 **伴生元数据 (`.meta.json`)**：出图同时在同目录下保存完整参数记录，方便追溯复现。
- 👁️ **自动打开预览 (`--open`)**：生成后可选自动调用系统默认查看器打开大图。

## 目录结构

```
image-gen/
├── SKILL.md              # 技能定义文件（提示词扩写规范、风格预设、执行指令）
├── config.json           # 个人配置（包含 API Key，建议加入 .gitignore）
├── config.example.json   # 示例配置文件模板
├── .gitignore            # 忽略敏感配置与输出
├── README.md             # 说明文档
└── scripts/
    └── generate.js       # 零依赖跨平台独立生图脚本（Node.js 18+）
```

## 命令行参数一览

| 参数 | 简写 | 默认值 | 说明 |
| :--- | :--- | :--- | :--- |
| `--prompt <text>` | `-p` | - | 生图提示词（推荐详细英文） |
| `--prompt-file <path>` | - | - | 从文本文件读取提示词（解决复杂字符转义） |
| `--image <path>` | `-i` | - | 垫图/参考图路径（图生图/风格迁移） |
| `--ratio <ratio>` | `-r` | `1:1` | 画面比例 (1:1, 16:9, 9:16, 4:3, 3:4, 21:9 等) |
| `--size <size>` | `-s` | `2K` | 画面分辨率 (1K, 2K, 4K) |
| `--count <num>` | `-n` | `1` | 生成图片数量 (1~4) |
| `--seed <num>` | - | - | 随机种子 |
| `--out <dir>` | `-o` | `./image-gen` | 输出目录 |
| `--open` | - | `false` | 生成后自动用系统查看器打开 |
| `--no-meta` | - | `false` | 不生成同名 `.meta.json` 文件 |
| `--json` | - | `false` | 以 JSON 格式输出结果 |

## 环境变量支持
- `IMAGE_GEN_API_KEY` / `GEMINI_API_KEY`: API 密钥
- `IMAGE_GEN_BASE_URL`: 自定义中转或 API Base URL
- `IMAGE_GEN_MODEL`: 模型名称（默认 `gemini-flash-image`）
