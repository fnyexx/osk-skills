---
name: image-gen
description: Use when the user requests generating, drawing, creating, or editing images, illustrations, avatars, wallpapers, posters, UI mockups, or visual graphics. Guides prompt expansion, parameter selection, style presets, image-to-image workflows, and tool/script execution across agents.
---

# Image Generation Skill (增强版)

本技能为各种 Agent 工具（OpenCode、Claude Code、Cursor、Windsurf、Cline、Aider 等）提供统一的高质量图像生成指导、提示词扩写规范、风格预设库、图生图（垫图）以及跨平台脚本执行能力。

## 1. 触发场景 (When to Trigger)

当用户意图包含但不限于以下需求时自动激活本技能：
- **文本生图**：“画一张...”、“生成一张...图片”、“帮我绘制...”
- **视觉设计**：“做个电脑/手机壁纸”、“设计一个头像/海报/插画/Logo/Banner”
- **风格化创作**：“根据文本生成配图”、“做一张科幻概念图/水墨风画作”
- **图生图 / 垫图修改**：“参考这张图修改...”、“把这张照片转成水墨风/动漫风”、“基于现有图片二创”

## 2. 图像参数智能映射 (Parameter Mapping)

根据用户的描述或应用场景，自动匹配最适宜的画面比例（`aspect_ratio`）与分辨率（`image_size`）：

| 用户场景 / 意图 | 推荐比例 (`aspect_ratio`) | 说明 |
| :--- | :--- | :--- |
| 头像、图标、正方形图、社交贴图 | `1:1` (默认) | 均衡构图 |
| 电脑桌面壁纸、宽银幕插画、影视概念图 | `16:9` | 横幅宽屏 |
| 手机壁纸、手机锁屏、Story / 短视频封面 | `9:16` | 竖幅长屏 |
| 海报设计、宣传单、图书封面、立绘 | `3:4` 或 `2:3` | 传统竖版印刷构图 |
| 摄影横图、画册横页、博客文章横幅 | `4:3` 或 `3:2` | 传统摄影比例 |
| 超宽双屏壁纸、全景电影画面 | `21:9` | 超宽全景 |

> **分辨率（`image_size`）**：默认为 `2K`。对极高清晰度需求（如打印、精细壁纸），且模型支持时可指定 `4K`；普通草图或快速预览可使用 `1K`。
> **默认保存路径**：自动保存在当前项目根目录下的 `./image-gen/` 文件夹中。

---

## 3. 提示词工程规范 (Prompt Engineering Guidelines)

**核心原则**：底层生图模型在理解英文提示词时表现最佳。模型接收到用户的中文需求后，**必须将其扩写为高质量、具象化的英文 Prompt**。

### 扩写五要素公式
扩写后的 Prompt 建议包含以下层次结构：
1. **Subject & Details（主体与细节）**：核心主体是什么、外观特征、动作姿态、材质纹理。
2. **Art Medium & Style（艺术媒介与风格）**：摄影写实 (Photorealistic)、吉卜力手绘 (Ghibli anime style)、赛博朋克 (Cyberpunk)、3D C4D/Blender 渲染、水墨国风 (Traditional Chinese ink wash)、油画质感 (Oil painting) 等。
3. **Lighting & Atmosphere（光影与氛围）**：体积光 (Volumetric lighting)、赛博霓虹 (Neon glow)、柔和晨光 (Golden hour soft sunlight)、电影级高反差 (Cinematic moody lighting) 等。
4. **Composition & Viewpoint（构图与视角）**：广角特写 (Macro shot / Wide angle)、微距细节 (Close-up)、三分构图法 (Rule of thirds)、低角度仰拍 (Low-angle view) 等。
5. **Color Palette & Quality（色彩与质感标签）**：8k resolution, highly detailed, Unreal Engine 5 render, octane render, masterpiece, vivid colors 等。

### 常用风格预设库 (Style Presets)
Agent 可根据用户的风格意图直接吸收以下经典后缀词组：
- **摄影写实**：`photorealistic, 8k resolution, captured with 85mm f/1.4 lens, natural lighting, ultra-detailed skin/fur texture, depth of field, National Geographic award-winning photography`
- **吉卜力手绘**：`Studio Ghibli style, Hayao Miyazaki aesthetic, hand-drawn anime illustration, lush painted greenery, nostalgic warm lighting, vibrant watercolor sky, whimsical and peaceful atmosphere`
- **赛博朋克**：`cyberpunk style, futuristic cityscape, glowing neon lights in cyan and magenta, rain-slicked reflective streets, volumetric fog, high-tech cybernetic details, cinematic Unreal Engine 5 render`
- **传统国风水墨**：`traditional Chinese ink wash painting, ethereal mountain mist, minimalist zen composition, subtle watercolor gradients on rice paper, elegant brushstrokes, poetic atmosphere`
- **3D 粘土/等轴测 (Isometric)**：`isometric 3D render, cute claymation / Blender Cycles render, soft ambient occlusion, pastel color palette, miniature tilt-shift effect, clean studio lighting`

---

## 4. 跨平台执行方案 (Cross-Agent Execution)

Agent 根据当前运行时环境的能力，选择以下两种执行分支之一：

### 分支 A：当前 Agent 环境拥有 `generate_image` 原生工具（例如 OpenCode 已加载插件）
直接使用内置 Tool 调用：
```json
{
  "tool": "generate_image",
  "args": {
    "prompt": "<扩写后的高质量英文 Prompt>",
    "aspect_ratio": "16:9",
    "image_size": "2K"
  }
}
```

### 分支 B：通用终端/命令行执行（Claude Code, Cursor, Windsurf, Cline 等）
利用终端/Bash 工具执行独立 Node.js 脚本：

```bash
# 基础文生图
node <skill_dir>/scripts/generate.js --prompt "<扩写后的高质量英文 Prompt>" --ratio 16:9 --size 2K

# 【推荐】提示词过长或含有复杂标点时，先写文本文件再执行，彻底避免命令行引号转义截断：
node <skill_dir>/scripts/generate.js --prompt-file temp_prompt.txt --ratio 16:9

# 垫图图生图 / 风格迁移（指定本地参考图片）：
node <skill_dir>/scripts/generate.js -i ./reference.png --prompt "Transform into traditional Chinese ink wash style" --ratio 4:3

# 多图并发抽卡与固定种子：
node <skill_dir>/scripts/generate.js --prompt "..." --count 2 --seed 12345
```

---

## 5. 结果交付规范 (Delivery)

图片生成完成后，向用户回复时应包含：
1. **成功提示与图片路径**：以 Markdown 引用或图片语法展示（如 `![生成的图片](file:///path/to/image.png)`），给出文件的本地绝对路径与伴生元数据文件路径（`./image-gen/*.meta.json`）。
2. **生图参数说明**：列出最终采用的画面比例（如 `16:9`）、分辨率以及是否有垫图/种子。
3. **提示词透明化**：展示本次扩写使用的完整英文 Prompt，方便用户以此为基础进行二次调整或微调。
