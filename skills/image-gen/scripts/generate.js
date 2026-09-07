#!/usr/bin/env node

/**
 * 跨 Agent 通用图像生成脚本 (Zero-dependency Node.js script)
 * 支持 OpenCode, Claude Code, Cursor, Windsurf, Cline, Aider 等任何具备终端执行能力的 Agent。
 *
 * 增强特性：
 * - 支持长提示词文件输入 (--prompt-file)
 * - 支持垫图图生图 (-i, --image)
 * - 支持批量生成 (-n, --count) 与种子控制 (--seed)
 * - 支持网络超时与重试保护 (Timeout & Retry)
 * - 支持伴生元数据文件生成 (.meta.json)
 * - 支持自动打开预览 (--open)
 */

const fs = require("node:fs/promises");
const fsSync = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { exec } = require("node:child_process");

const DEFAULT_CONFIG = {
  apiKey: "",
  model: "gemini-flash-image",
  aspectRatio: "1:1",
  imageSize: "2K",
  outputDir: "image-gen",
  baseUrl: "https://hkfx.058279.xyz",
};

// 解析命令行参数
function parseArgs() {
  const args = process.argv.slice(2);
  const parsed = {
    prompt: "",
    promptFile: "",
    refImage: "",
    aspectRatio: "",
    imageSize: "",
    count: 1,
    seed: null,
    outputDir: "",
    model: "",
    apiKey: "",
    baseUrl: "",
    configFile: "",
    openAfterGen: false,
    noMeta: false,
    jsonOutput: false,
    help: false,
  };

  for (let i = 0; i < args.length; i++) {
    const arg = args[i];
    if (arg === "-h" || arg === "--help") {
      parsed.help = true;
    } else if (arg === "--json") {
      parsed.jsonOutput = true;
    } else if (arg === "--open") {
      parsed.openAfterGen = true;
    } else if (arg === "--no-meta") {
      parsed.noMeta = true;
    } else if (arg === "-p" || arg === "--prompt") {
      parsed.prompt = args[++i] || "";
    } else if (arg === "--prompt-file") {
      parsed.promptFile = args[++i] || "";
    } else if (arg === "-i" || arg === "--image" || arg === "--ref-image") {
      parsed.refImage = args[++i] || "";
    } else if (arg === "-r" || arg === "--ratio" || arg === "--aspect-ratio") {
      parsed.aspectRatio = args[++i] || "";
    } else if (arg === "-s" || arg === "--size" || arg === "--image-size") {
      parsed.imageSize = args[++i] || "";
    } else if (arg === "-n" || arg === "--count") {
      const c = parseInt(args[++i], 10);
      if (!isNaN(c) && c > 0) parsed.count = Math.min(c, 4);
    } else if (arg === "--seed") {
      const s = parseInt(args[++i], 10);
      if (!isNaN(s)) parsed.seed = s;
    } else if (arg === "-o" || arg === "--out" || arg === "--output") {
      parsed.outputDir = args[++i] || "";
    } else if (arg === "-m" || arg === "--model") {
      parsed.model = args[++i] || "";
    } else if (arg === "-k" || arg === "--api-key") {
      parsed.apiKey = args[++i] || "";
    } else if (arg === "-u" || arg === "--base-url") {
      parsed.baseUrl = args[++i] || "";
    } else if (arg === "-c" || arg === "--config") {
      parsed.configFile = args[++i] || "";
    } else if (!parsed.prompt && !arg.startsWith("-")) {
      parsed.prompt = arg;
    }
  }

  return parsed;
}

function printHelp() {
  console.log(`
用法: node generate.js [options]

选项:
  -p, --prompt <text>         提示词 (必须包含详细画面描述，推荐英文)
  --prompt-file <path>        从指定文本文件读取提示词 (避免终端命令行引号与换行转义问题)
  -i, --image <path>          垫图/参考图路径 (支持以图画图、风格迁移)
  -r, --ratio <ratio>         画面比例 (1:1, 16:9, 9:16, 4:3, 3:4, 2:3, 3:2, 4:5, 5:4, 21:9，默认 1:1)
  -s, --size <size>           分辨率 (1K, 2K, 4K，默认 2K)
  -n, --count <num>           生成图片数量 (1~4，默认 1)
  --seed <num>                随机种子 (用于复现或微调画面)
  -o, --out <dir>             图片输出目录 (默认保存至当前项目目录下的 ./image-gen)
  -m, --model <name>          模型名称 (默认 gemini-flash-image)
  -k, --api-key <key>         API Key (也可通过环境变量 IMAGE_GEN_API_KEY / GEMINI_API_KEY 配置)
  -u, --base-url <url>        API Base URL (默认 https://hkfx.058279.xyz)
  -c, --config <file>         指定配置文件路径
  --open                      生成成功后自动调用系统默认看图工具打开图片
  --no-meta                   不生成伴生 .meta.json 元数据文件
  --json                      以 JSON 格式输出结果
  -h, --help                  显示帮助信息

示例:
  # 基础生成
  node generate.js --prompt "A cinematic cybernetic cat in neon Tokyo, 8k" --ratio 16:9

  # 使用长提示词文件 + 自动打开
  node generate.js --prompt-file prompt.txt --ratio 16:9 --open

  # 垫图图生图 / 风格迁移
  node generate.js -i ./cat.png -p "Turn this cat into a watercolor painting, soft pastels"
`);
}

// 统一解析提示词（支持文件读取与标准输入）
async function resolvePrompt(cliArgs) {
  if (cliArgs.promptFile) {
    if (!fsSync.existsSync(cliArgs.promptFile)) {
      throw new Error(`提示词文件不存在: ${cliArgs.promptFile}`);
    }
    return (await fs.readFile(cliArgs.promptFile, "utf8")).trim();
  }

  if (cliArgs.prompt === "-" || (!cliArgs.prompt && !process.stdin.isTTY)) {
    return new Promise((resolve, reject) => {
      let data = "";
      process.stdin.setEncoding("utf8");
      process.stdin.on("data", (chunk) => (data += chunk));
      process.stdin.on("end", () => resolve(data.trim()));
      process.stdin.on("error", reject);
    });
  }

  return cliArgs.prompt.trim();
}

// 加载配置（多源级联）
async function resolveConfig(cliArgs) {
  let config = { ...DEFAULT_CONFIG };

  // 1. 尝试从脚本同目录及父目录下的 config.json 读取
  const possibleLocalConfigs = [
    path.join(__dirname, "config.json"),
    path.join(__dirname, "..", "config.json"),
  ];
  for (const p of possibleLocalConfigs) {
    if (fsSync.existsSync(p)) {
      try {
        const raw = await fs.readFile(p, "utf8");
        config = { ...config, ...JSON.parse(raw) };
        break;
      } catch {}
    }
  }

  // 2. 尝试从 OpenCode 全局插件配置目录读取
  const opencodePluginConfig = path.join(
    os.homedir(),
    ".config",
    "opencode",
    "plugin-data",
    "image-gen.json"
  );
  if (fsSync.existsSync(opencodePluginConfig)) {
    try {
      const raw = await fs.readFile(opencodePluginConfig, "utf8");
      config = { ...config, ...JSON.parse(raw) };
    } catch {}
  }

  // 3. 用户命令行指定的自定义配置文件
  if (cliArgs.configFile && fsSync.existsSync(cliArgs.configFile)) {
    try {
      const raw = await fs.readFile(cliArgs.configFile, "utf8");
      config = { ...config, ...JSON.parse(raw) };
    } catch {}
  }

  // 4. 环境变量覆盖
  const envKey =
    process.env.IMAGE_GEN_API_KEY ||
    process.env.GEMINI_API_KEY ||
    process.env.GOOGLE_API_KEY;
  if (envKey) config.apiKey = envKey;
  if (process.env.IMAGE_GEN_BASE_URL) config.baseUrl = process.env.IMAGE_GEN_BASE_URL;
  if (process.env.IMAGE_GEN_MODEL) config.model = process.env.IMAGE_GEN_MODEL;

  // 5. 命令行参数覆盖
  if (cliArgs.apiKey) config.apiKey = cliArgs.apiKey;
  if (cliArgs.model) config.model = cliArgs.model;
  if (cliArgs.baseUrl) config.baseUrl = cliArgs.baseUrl;
  if (cliArgs.aspectRatio) config.aspectRatio = cliArgs.aspectRatio;
  if (cliArgs.imageSize) config.imageSize = cliArgs.imageSize;
  if (cliArgs.outputDir) config.outputDir = cliArgs.outputDir;

  // 默认输出目录计算
  if (!config.outputDir) {
    config.outputDir = path.join(process.cwd(), "image-gen");
  } else if (!path.isAbsolute(config.outputDir)) {
    config.outputDir = path.resolve(process.cwd(), config.outputDir);
  }

  return config;
}

function isImagenModel(model) {
  return model.startsWith("imagen");
}

// 图片 MimeType 检测辅助
function getMimeTypeFromExt(filePath) {
  const ext = path.extname(filePath).toLowerCase();
  switch (ext) {
    case ".png":
      return "image/png";
    case ".jpg":
    case ".jpeg":
      return "image/jpeg";
    case ".webp":
      return "image/webp";
    case ".gif":
      return "image/gif";
    default:
      return "image/png";
  }
}

// 带超时与自动重试的网络请求
async function fetchWithRetry(url, options, maxRetries = 2, timeoutMs = 60000) {
  let lastError;
  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), timeoutMs);
      const response = await fetch(url, {
        ...options,
        signal: controller.signal,
      });
      clearTimeout(timer);

      // 429 限流或 5xx 服务端偶发故障重试
      if ((response.status === 429 || response.status >= 500) && attempt < maxRetries) {
        await new Promise((resolve) => setTimeout(resolve, 1500 * (attempt + 1)));
        continue;
      }

      return response;
    } catch (err) {
      lastError = err;
      if (err.name === "AbortError") {
        throw new Error(`请求超时 (${timeoutMs / 1000}s)，请检查网络连接或更换 API Base URL。`);
      }
      if (attempt < maxRetries) {
        await new Promise((resolve) => setTimeout(resolve, 1500 * (attempt + 1)));
        continue;
      }
    }
  }
  throw lastError || new Error("网络请求失败");
}

// 解析友好的错误信息
async function parseErrorMessage(resp, defaultPrefix) {
  try {
    const json = await resp.json();
    if (json.error?.message) {
      return `${defaultPrefix} (${resp.status}): ${json.error.message}`;
    }
    if (json.promptFeedback?.blockReason) {
      return `${defaultPrefix}: 内容触发安全审查拦截 (${json.promptFeedback.blockReason})`;
    }
    return `${defaultPrefix} (${resp.status}): ${JSON.stringify(json)}`;
  } catch {
    const raw = await resp.text().catch(() => "");
    return `${defaultPrefix} (${resp.status}): ${raw.slice(0, 300) || "未知错误"}`;
  }
}

// 单次执行核心生图
async function requestOneImage(cfg, prompt, options = {}) {
  const model = cfg.model;
  const aspectRatio = options.aspectRatio || cfg.aspectRatio || "1:1";
  const imageSize = options.imageSize || cfg.imageSize || "2K";
  const seed = options.seed;
  const refImage = options.refImage;

  let imageBuffer;
  let mimeType = "image/png";
  let textResponse;

  if (isImagenModel(model)) {
    const url = `${cfg.baseUrl.replace(/\/+$/, "")}/v1beta/models/${model}:predict`;
    const body = {
      instances: [{ prompt }],
      parameters: {
        sampleCount: 1,
        aspectRatio,
      },
    };

    const resp = await fetchWithRetry(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "x-goog-api-key": cfg.apiKey,
      },
      body: JSON.stringify(body),
    });

    if (!resp.ok) {
      throw new Error(await parseErrorMessage(resp, "Imagen API 请求失败"));
    }

    const json = await resp.json();
    const prediction = json.predictions?.[0];
    if (!prediction?.bytesBase64Encoded) {
      throw new Error("Imagen 响应中未包含图像数据");
    }

    imageBuffer = Buffer.from(prediction.bytesBase64Encoded, "base64");
    mimeType = prediction.mimeType || "image/png";
  } else {
    const url = `${cfg.baseUrl.replace(/\/+$/, "")}/v1beta/models/${model}:generateContent`;

    const parts = [];

    // 若指定了参考图/垫图，作为 inlineData 加入 parts
    if (refImage) {
      if (!fsSync.existsSync(refImage)) {
        throw new Error(`参考图片不存在: ${refImage}`);
      }
      const refBuf = await fs.readFile(refImage);
      const refMime = getMimeTypeFromExt(refImage);
      parts.push({
        inlineData: {
          mimeType: refMime,
          data: refBuf.toString("base64"),
        },
      });
    }

    parts.push({ text: prompt });

    const generationConfig = {
      responseModalities: ["TEXT", "IMAGE"],
      imageConfig: {
        aspectRatio,
        imageSize,
      },
    };
    if (typeof seed === "number") {
      generationConfig.seed = seed;
    }

    const body = {
      contents: [{ role: "user", parts }],
      generationConfig,
    };

    const resp = await fetchWithRetry(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "x-goog-api-key": cfg.apiKey,
      },
      body: JSON.stringify(body),
    });

    if (!resp.ok) {
      throw new Error(await parseErrorMessage(resp, "Gemini API 请求失败"));
    }

    const json = await resp.json();
    const candidate = json.candidates?.[0];

    if (candidate?.finishReason === "SAFETY") {
      throw new Error("生成失败: 内容触发了安全策略拦截 (FinishReason: SAFETY)");
    }

    const resParts = candidate?.content?.parts || [];

    for (const part of resParts) {
      const inline = part.inlineData ?? part.inline_data;
      if (inline?.data) {
        imageBuffer = Buffer.from(inline.data, "base64");
        mimeType = inline.mimeType ?? inline.mime_type ?? "image/png";
      }
      if (part.text) {
        textResponse = (textResponse || "") + part.text;
      }
    }

    if (!imageBuffer) {
      const reason = candidate?.finishReason ? `(终止原因: ${candidate.finishReason})` : "";
      throw new Error(`Gemini 响应中未包含图像数据 ${reason}。可能是当前模型不支持生图或提示词被过滤。`);
    }
  }

  return { imageBuffer, mimeType, textResponse };
}

// 保存图片与伴生元数据
async function saveImageResult(cfg, prompt, imgData, options, index = 0) {
  const { imageBuffer, mimeType, textResponse } = imgData;
  const ext = mimeType.includes("jpeg") || mimeType.includes("jpg") ? "jpg" : "png";
  const ts = new Date().toISOString().replace(/[:.]/g, "-").slice(0, 19);
  const slug = prompt
    .slice(0, 40)
    .replace(/[^a-zA-Z0-9一-鿿]/g, "_")
    .replace(/_+/g, "_")
    .replace(/_$/, "");
  const suffix = options.totalCount > 1 ? `_${index + 1}` : "";
  const filename = `${ts}_${slug || "image"}${suffix}.${ext}`;
  const filePath = path.join(cfg.outputDir, filename);

  await fs.writeFile(filePath, imageBuffer);

  const fullPath = path.resolve(filePath);

  // 伴生元数据文件
  let metaPath = null;
  if (!options.noMeta) {
    const metaFile = `${ts}_${slug || "image"}${suffix}.meta.json`;
    metaPath = path.join(cfg.outputDir, metaFile);
    const metaData = {
      createdAt: new Date().toISOString(),
      prompt,
      model: cfg.model,
      aspectRatio: options.aspectRatio || cfg.aspectRatio,
      imageSize: options.imageSize || cfg.imageSize,
      seed: options.seed ?? null,
      refImage: options.refImage ? path.resolve(options.refImage) : null,
      mimeType,
      imageFile: filename,
      textResponse: textResponse || null,
    };
    await fs.writeFile(metaPath, JSON.stringify(metaData, null, 2), "utf8");
    metaPath = path.resolve(metaPath);
  }

  return {
    filePath: fullPath,
    metaPath,
    mimeType,
    aspectRatio: options.aspectRatio || cfg.aspectRatio,
    imageSize: options.imageSize || cfg.imageSize,
    model: cfg.model,
    textResponse,
  };
}

// 自动打开文件
function openFileInSystem(filePath) {
  const platform = process.platform;
  let cmd = "";
  if (platform === "win32") {
    cmd = `start "" "${filePath}"`;
  } else if (platform === "darwin") {
    cmd = `open "${filePath}"`;
  } else {
    cmd = `xdg-open "${filePath}"`;
  }
  exec(cmd, () => {});
}

async function main() {
  const args = parseArgs();
  if (args.help || (!args.prompt && !args.promptFile && process.argv.length <= 2)) {
    printHelp();
    process.exit(args.help ? 0 : 1);
  }

  let prompt = "";
  try {
    prompt = await resolvePrompt(args);
  } catch (err) {
    console.error(`[参数错误] ${err.message}`);
    process.exit(1);
  }

  if (!prompt) {
    console.error("错误: 必须提供提示词 (--prompt 或 --prompt-file)。");
    process.exit(1);
  }

  try {
    const config = await resolveConfig(args);
    if (!config.apiKey) {
      throw new Error(
        "未配置 API Key。请通过环境变量 IMAGE_GEN_API_KEY、--api-key 参数或在配置文件中配置 apiKey。"
      );
    }

    await fs.mkdir(config.outputDir, { recursive: true });

    const totalCount = args.count || 1;
    const results = [];

    for (let i = 0; i < totalCount; i++) {
      const currentSeed =
        args.seed !== null ? args.seed + i : undefined;
      const imgData = await requestOneImage(config, prompt, {
        aspectRatio: args.aspectRatio,
        imageSize: args.imageSize,
        seed: currentSeed,
        refImage: args.refImage,
      });

      const saved = await saveImageResult(
        config,
        prompt,
        imgData,
        {
          aspectRatio: args.aspectRatio,
          imageSize: args.imageSize,
          seed: currentSeed,
          refImage: args.refImage,
          totalCount,
          noMeta: args.noMeta,
        },
        i
      );
      results.push(saved);

      if (args.openAfterGen) {
        openFileInSystem(saved.filePath);
      }
    }

    if (args.jsonOutput) {
      console.log(JSON.stringify(totalCount === 1 ? results[0] : results, null, 2));
    } else {
      console.log(`\n[成功] 图像已生成并保存！(共 ${results.length} 张)`);
      for (let i = 0; i < results.length; i++) {
        const item = results[i];
        console.log(`\n--- 图片 #${i + 1} ---`);
        console.log(`文件路径: ${item.filePath}`);
        if (item.metaPath) console.log(`元数据:   ${item.metaPath}`);
        console.log(`画面比例: ${item.aspectRatio} | 分辨率: ${item.imageSize}`);
        console.log(`使用模型: ${item.model}`);
        if (item.textResponse) {
          console.log(`模型附言: ${item.textResponse}`);
        }
      }
    }
  } catch (error) {
    if (args.jsonOutput) {
      console.error(JSON.stringify({ error: error.message }));
    } else {
      console.error(`\n[生成失败] ${error.message}`);
    }
    process.exit(1);
  }
}

main();
